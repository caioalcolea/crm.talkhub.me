import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from cases.models import Case
from common.models import Profile
from common.tasks import set_rls_context

logger = logging.getLogger(__name__)


@shared_task
def send_email_to_assigned_user(recipients, case_id, org_id):
    """Send Mail To Users When they are assigned to a case"""
    set_rls_context(org_id)
    case = Case.objects.get(id=case_id)
    created_by = case.created_by
    for profile_id in recipients:
        recipients_list = []
        profile = Profile.objects.filter(id=profile_id, is_active=True).first()
        if profile:
            recipients_list.append(profile.user.email)
            context = {}
            context["url"] = settings.DOMAIN_NAME
            context["user"] = profile.user
            context["case"] = case
            context["created_by"] = created_by
            subject = "Um chamado foi atribuído a você."
            html_content = render_to_string(
                "assigned_to/cases_assigned.html", context=context
            )

            msg = EmailMessage(subject, html_content, to=recipients_list)
            msg.content_subtype = "html"
            msg.send()


@shared_task
def check_sla_breaches():
    """
    Verificar todos os cases abertos com SLA configurado.
    Se SLA de first_response ou resolution foi violado, escalar automaticamente.
    Executado a cada 15 minutos via Celery Beat.
    Itera por org para respeitar isolamento multi-tenant.
    """
    from django.utils import timezone as tz

    from common.models import Org

    # Iterar por org para manter isolamento multi-tenant
    orgs_with_cases = Org.objects.filter(
        cases__status__in=["New", "In Progress", "Pending", "Assigned"],
    ).distinct()

    total_escalated = 0

    for org in orgs_with_cases:
        set_rls_context(str(org.id))

        open_cases = Case.objects.filter(
            org=org,
            status__in=["New", "In Progress", "Pending", "Assigned"],
        ).select_related("stage__pipeline")

        now = tz.now()

        for case in open_cases:
            if not case.stage or not case.stage.pipeline:
                continue

            pipeline = case.stage.pipeline
            if not getattr(pipeline, "auto_escalate", False):
                continue

            breached = False

            if case.is_sla_first_response_breached and not case.first_response_at:
                breached = True

            if case.is_sla_resolution_breached and not case.resolved_at:
                breached = True

            if breached and case.escalation_level < 3:
                case.escalation_level += 1
                case.escalated_at = now
                case.save(update_fields=[
                    "escalation_level", "escalated_at", "updated_at",
                ])
                total_escalated += 1
                logger.info(
                    "Case %s (org=%s) escalated to level %d (SLA breach)",
                    case.id, org.id, case.escalation_level,
                )

    if total_escalated:
        logger.info("SLA check complete: %d cases escalated across all orgs", total_escalated)
