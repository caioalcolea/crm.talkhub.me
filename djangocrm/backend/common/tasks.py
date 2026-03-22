import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import connection
from django.template.loader import render_to_string
from django.utils import timezone

from common.models import Comment, ContactFormSubmission, MagicLinkToken, Profile, Teams, User

logger = logging.getLogger(__name__)


def set_rls_context(org_id):
    """
    Set RLS context for Celery tasks that query org-scoped tables.

    Celery workers don't go through Django middleware, so RLS context
    must be set explicitly before querying org-scoped data.

    Args:
        org_id: Organization UUID (string or UUID object)
    """
    if org_id:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_org', %s, false)", [str(org_id)]
            )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    retry_jitter=True,
)
def send_welcome_email(self, user_id):
    """Send welcome email to newly created users."""
    user_obj = User.objects.filter(id=user_id).first()
    if not user_obj:
        return

    email = user_obj.email.strip()
    try:
        validate_email(email)
    except ValidationError:
        logger.warning("Welcome email skipped: invalid email for user %s", user_id)
        return

    context = {"url": settings.FRONTEND_URL}
    subject = "Bem-vindo ao TalkHub CRM"
    html_content = render_to_string("welcome_email.html", context=context)
    text_content = f"Bem-vindo ao TalkHub CRM!\n\nAcesse: {settings.FRONTEND_URL}"

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    logger.info("Welcome email sent to %s", email)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    retry_jitter=True,
)
def send_magic_link_email(self, token_id):
    """Send magic link email for passwordless authentication."""
    magic_token = MagicLinkToken.objects.filter(id=token_id).first()
    if not magic_token:
        return

    # Skip if token already expired (no point sending)
    if magic_token.expires_at < timezone.now():
        logger.info("Magic link token %s already expired, skipping email", token_id)
        return

    email = magic_token.email.strip()
    try:
        validate_email(email)
    except ValidationError:
        logger.warning("Magic link skipped: invalid email format for token %s", token_id)
        return

    magic_link_url = f"{settings.FRONTEND_URL}/login/verify?token={magic_token.token}"

    html_content = render_to_string(
        "magic_link_email.html",
        {"magic_link_url": magic_link_url},
    )

    text_content = (
        "Entrar no TalkHub CRM\n\n"
        "Clique no link abaixo para entrar na sua conta. "
        "Este link expira em 10 minutos.\n\n"
        f"{magic_link_url}\n\n"
        "Se você não solicitou este link, ignore este e-mail."
    )

    msg = EmailMultiAlternatives(
        subject="TalkHub CRM - Seu link de acesso",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.extra_headers["X-Mailer"] = "TalkHub CRM"
    msg.extra_headers["X-Auto-Response-Suppress"] = "All"
    msg.send()
    logger.info("Magic link email sent to %s (token %s)", email, token_id)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    retry_jitter=True,
)
def send_email_user_mentions(
    self,
    comment_id,
    called_from,
    org_id=None,
):
    """Send Mail To Mentioned Users In The Comment"""
    # Set RLS context for org-scoped queries
    set_rls_context(org_id)

    comment = Comment.objects.filter(id=comment_id).first()
    if not comment:
        return

    comment_text = comment.comment
    comment_text_list = comment_text.split()
    recipients = []
    for word in comment_text_list:
        if word.startswith("@"):
            username = word.strip("@").strip(",")
            if username not in recipients:
                user = User.objects.filter(username=username, is_active=True).first()
                if user:
                    recipients.append(user.email)

    SUBJECT_MAP = {
        "accounts": "Novo comentário em Conta",
        "contacts": "Novo comentário em Contato",
        "leads": "Novo comentário em Lead",
        "opportunity": "Novo comentário em Oportunidade",
        "cases": "Novo comentário em Chamado",
        "tasks": "Novo comentário em Tarefa",
        "invoices": "Novo comentário em Fatura",
    }
    subject = SUBJECT_MAP.get(called_from)
    if not subject or not recipients:
        return

    context = {
        "commented_by": comment.commented_by,
        "comment_description": comment.comment,
        "url": settings.DOMAIN_NAME,
    }

    for recipient in recipients:
        context["mentioned_user"] = recipient
        html_content = render_to_string("comment_email.html", context=context)
        text_content = f"{subject}\n\n{comment.comment}\n\nPor: {comment.commented_by}"
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    retry_jitter=True,
)
def send_email_user_status(
    self,
    user_id,
    status_changed_user="",
):
    """Send Mail To Users Regarding their status i.e active or inactive"""
    user = User.objects.filter(id=user_id).first()
    if not user:
        return

    context = {
        "email": user.email,
        "url": settings.DOMAIN_NAME,
        "status_changed_user": status_changed_user,
    }
    if user.has_marketing_access:
        context["url"] = context["url"] + "/marketing"

    if user.is_active:
        context["message"] = "activated"
        subject = "Conta Ativada"
        html_content = render_to_string("user_status_activate.html", context=context)
        text_content = f"Sua conta foi ativada por {status_changed_user}."
    else:
        context["message"] = "deactivated"
        subject = "Conta Desativada"
        html_content = render_to_string("user_status_deactivate.html", context=context)
        text_content = f"Sua conta foi desativada por {status_changed_user}."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    retry_jitter=True,
)
def send_email_user_delete(
    self,
    user_email,
    deleted_by="",
):
    """Send Mail To Users When their account is deleted"""
    if not user_email:
        return

    context = {
        "message": "deleted",
        "deleted_by": deleted_by,
        "email": user_email,
    }
    subject = "TalkHub CRM: Sua conta foi excluída."
    html_content = render_to_string("user_delete_email.html", context=context)
    text_content = f"Sua conta no TalkHub CRM foi excluída por {deleted_by}."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@shared_task
def remove_users(removed_users_list, team_id, org_id=None):
    # Set RLS context for org-scoped queries
    set_rls_context(org_id)

    removed_users_list = [i for i in removed_users_list if i.isdigit()]
    users_list = Profile.objects.filter(id__in=removed_users_list)
    if users_list.exists():
        team = Teams.objects.filter(id=team_id).first()
        if team:
            accounts = team.account_teams.all()
            for account in accounts:
                for user in users_list:
                    account.assigned_to.remove(user)

            contacts = team.contact_teams.all()
            for contact in contacts:
                for user in users_list:
                    contact.assigned_to.remove(user)

            leads = team.lead_teams.all()
            for lead in leads:
                for user in users_list:
                    lead.assigned_to.remove(user)

            opportunities = team.oppurtunity_teams.all()
            for opportunity in opportunities:
                for user in users_list:
                    opportunity.assigned_to.remove(user)

            cases = team.cases_teams.all()
            for case in cases:
                for user in users_list:
                    case.assigned_to.remove(user)

            docs = team.document_teams.all()
            for doc in docs:
                for user in users_list:
                    doc.shared_to.remove(user)

            tasks = team.tasks_teams.all()
            for task in tasks:
                for user in users_list:
                    task.assigned_to.remove(user)

            invoices = team.invoices_teams.all()
            for invoice in invoices:
                for user in users_list:
                    invoice.assigned_to.remove(user)


@shared_task
def update_team_users(team_id, org_id=None):
    """this function updates assigned_to field on all models when a team is updated"""
    # Set RLS context for org-scoped queries
    set_rls_context(org_id)

    team = Teams.objects.filter(id=team_id).first()
    if team:
        teams_members = team.users.all()

        accounts = team.account_teams.all()
        for account in accounts:
            account_assigned_to_users = account.assigned_to.all()
            for team_member in teams_members:
                if team_member not in account_assigned_to_users:
                    account.assigned_to.add(team_member)

        contacts = team.contact_teams.all()
        for contact in contacts:
            contact_assigned_to_users = contact.assigned_to.all()
            for team_member in teams_members:
                if team_member not in contact_assigned_to_users:
                    contact.assigned_to.add(team_member)

        leads = team.lead_teams.all()
        for lead in leads:
            lead_assigned_to_users = lead.assigned_to.all()
            for team_member in teams_members:
                if team_member not in lead_assigned_to_users:
                    lead.assigned_to.add(team_member)

        opportunities = team.oppurtunity_teams.all()
        for opportunity in opportunities:
            opportunity_assigned_to_users = opportunity.assigned_to.all()
            for team_member in teams_members:
                if team_member not in opportunity_assigned_to_users:
                    opportunity.assigned_to.add(team_member)

        cases = team.cases_teams.all()
        for case in cases:
            case_assigned_to_users = case.assigned_to.all()
            for team_member in teams_members:
                if team_member not in case_assigned_to_users:
                    case.assigned_to.add(team_member)

        docs = team.document_teams.all()
        for doc in docs:
            doc_assigned_to_users = doc.shared_to.all()
            for team_member in teams_members:
                if team_member not in doc_assigned_to_users:
                    doc.shared_to.add(team_member)

        tasks = team.tasks_teams.all()
        for task in tasks:
            task_assigned_to_users = task.assigned_to.all()
            for team_member in teams_members:
                if team_member not in task_assigned_to_users:
                    task.assigned_to.add(team_member)

        invoices = team.invoices_teams.all()
        for invoice in invoices:
            invoice_assigned_to_users = invoice.assigned_to.all()
            for team_member in teams_members:
                if team_member not in invoice_assigned_to_users:
                    invoice.assigned_to.add(team_member)


REASON_LABELS = {
    "support": "Suporte Prioritário",
    "feature": "Solicitação de Recurso",
    "bug": "Relatório de Bug",
    "security": "Vulnerabilidade de Segurança",
    "general": "Consulta Geral",
}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    retry_jitter=True,
)
def send_contact_form_email(self, submission_id):
    """Send contact form submission to adm@talkhub.me."""
    submission = ContactFormSubmission.objects.filter(id=submission_id).first()
    if not submission:
        logger.warning("ContactFormSubmission not found: %s", submission_id)
        return

    reason_label = REASON_LABELS.get(submission.reason, submission.reason)
    subject = f"[TalkHub CRM] {reason_label}: {submission.subject or submission.name}"

    html_content = render_to_string(
        "contact_form_email.html",
        {
            "submission": submission,
            "reason_label": reason_label,
        },
    )
    text_content = (
        f"{reason_label}\n\n"
        f"De: {submission.name} ({submission.email})\n"
        f"Assunto: {submission.subject or 'N/A'}\n\n"
        f"{submission.message or ''}"
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=["adm@talkhub.me"],
        reply_to=[submission.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    logger.info("Contact form email sent for submission %s", submission_id)

ROLE_LABELS_INVITE = {
    "ADMIN": "Administrador",
    "USER": "Usuário",
}


@shared_task(
    name="common.tasks.send_invitation_email",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    retry_jitter=True,
)
def send_invitation_email(self, invitation_id):
    """Envia email de convite para novo usuário."""
    from common.models import PendingInvitation

    invitation = PendingInvitation.objects.select_related("org", "invited_by").filter(
        id=invitation_id
    ).first()
    if not invitation:
        logger.warning("PendingInvitation not found: %s", invitation_id)
        return

    email = invitation.email.strip()
    try:
        validate_email(email)
    except ValidationError:
        logger.warning("Invitation email skipped: invalid email %s", email)
        return

    accept_url = (
        f"{settings.DOMAIN_NAME}/invite/accept/{invitation.token}/"
    )
    invited_by_name = invitation.invited_by.email.split("@")[0] if invitation.invited_by else "Alguém"
    role_label = ROLE_LABELS_INVITE.get(invitation.role, invitation.role)

    html_content = render_to_string(
        "invitations/invite_email.html",
        {
            "accept_url": accept_url,
            "org_name": invitation.org.name,
            "invited_by_name": invited_by_name,
            "role_label": role_label,
        },
    )

    text_content = (
        f"Convite para {invitation.org.name}\n\n"
        f"{invited_by_name} convidou você como {role_label}.\n\n"
        f"Aceite o convite: {accept_url}"
    )

    subject = f"Convite para {invitation.org.name} — TalkHub CRM"
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    logger.info("Invitation email sent to %s for org %s", email, invitation.org.name)


@shared_task(name="common.tasks.expire_pending_invitations")
def expire_pending_invitations():
    """Marca convites expirados. Roda diariamente via Celery Beat."""
    from common.models import Org, PendingInvitation

    now = timezone.now()

    # Process per-org to respect RLS
    org_ids = (
        PendingInvitation.objects.filter(status="pending", expires_at__lt=now)
        .values_list("org_id", flat=True)
        .distinct()
    )

    total_expired = 0
    for org_id in org_ids:
        set_rls_context(org_id)
        count = PendingInvitation.objects.filter(
            org_id=org_id,
            status="pending",
            expires_at__lt=now,
        ).update(status="expired")
        total_expired += count

    if total_expired:
        logger.info("Expired %d pending invitations", total_expired)

