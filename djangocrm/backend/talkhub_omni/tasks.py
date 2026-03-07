"""
Celery tasks refatoradas para TalkHub Omni.

Tasks:
- push_contact_to_omni: propagar Contact → Omni (bind, max_retries=3, backoff)
- push_case_to_omni_task / push_lead_to_omni_task: propagar tickets
- sync_omni_contacts/tickets/tags/team_members/statistics: full sync
- sync_tag_to_omni / delete_tag_from_omni: tag sync bidirecional
- periodic_sync_*: wrappers para Celery Beat
"""

import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from common.models import Org
from common.tasks import set_rls_context

from .models import TalkHubConnection, TalkHubSyncJob

logger = logging.getLogger(__name__)

SYNC_LOCK_TTL = 5


# ═══════════════════════════════════════════════════════════════════════
# Push tasks (bidirecional CRM → Omni)
# ═══════════════════════════════════════════════════════════════════════


@shared_task(bind=True, max_retries=3)
def push_contact_to_omni(self, org_id: str, contact_id: str):
    """Propagar alteração de Contact para TalkHub Omni. Backoff exponencial."""
    set_rls_context(org_id)
    from contacts.models import Contact

    org = Org.objects.get(id=org_id)
    contact = Contact.objects.get(id=contact_id)

    if contact.talkhub_subscriber_id:
        cache_key = f"sync_lock:contact:{contact.talkhub_subscriber_id}:{org_id}"
        cache.set(cache_key, True, timeout=SYNC_LOCK_TTL)

    try:
        from .sync_engine import push_contact_to_talkhub
        push_contact_to_talkhub(org, contact)
    except Exception as exc:
        _log_error(org, "update", "contact", contact_id, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


@shared_task(bind=True, max_retries=3)
def push_case_to_omni_task(self, org_id: str, case_id: str):
    """Propagar alteração de Case para TalkHub Omni ticket."""
    set_rls_context(org_id)
    from cases.models import Case

    org = Org.objects.get(id=org_id)
    case = Case.objects.get(id=case_id)

    try:
        from .sync_engine import push_case_to_omni
        push_case_to_omni(org, case)
    except Exception as exc:
        _log_error(org, "update", "case", case_id, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


@shared_task(bind=True, max_retries=3)
def push_lead_to_omni_task(self, org_id: str, lead_id: str):
    """Propagar alteração de Lead para TalkHub Omni ticket."""
    set_rls_context(org_id)
    from leads.models import Lead

    org = Org.objects.get(id=org_id)
    lead = Lead.objects.get(id=lead_id)

    try:
        from .sync_engine import push_lead_to_omni
        push_lead_to_omni(org, lead)
    except Exception as exc:
        _log_error(org, "update", "lead", lead_id, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


# ═══════════════════════════════════════════════════════════════════════
# Tag sync tasks
# ═══════════════════════════════════════════════════════════════════════


@shared_task
def sync_tag_to_omni(org_id: str, tag_name: str):
    """Criar tag no TalkHub Omni."""
    set_rls_context(org_id)
    from .client import TalkHubAPIError, TalkHubClient
    from .models import TalkHubConnection

    conn = TalkHubConnection.objects.filter(
        org_id=org_id, is_connected=True
    ).first()
    if not conn:
        return

    client = TalkHubClient(api_key=conn.api_key, base_url=conn.workspace_url)
    try:
        client.create_tag(tag_name)
    except TalkHubAPIError as exc:
        logger.warning("Failed to create tag '%s' in Omni: %s", tag_name, exc)


@shared_task
def delete_tag_from_omni(org_id: str, tag_ns: str):
    """Excluir tag no TalkHub Omni."""
    set_rls_context(org_id)
    from .client import TalkHubAPIError, TalkHubClient
    from .models import TalkHubConnection

    conn = TalkHubConnection.objects.filter(
        org_id=org_id, is_connected=True
    ).first()
    if not conn:
        return

    client = TalkHubClient(api_key=conn.api_key, base_url=conn.workspace_url)
    try:
        client.delete_tag(tag_ns)
    except TalkHubAPIError as exc:
        logger.warning("Failed to delete tag ns=%s from Omni: %s", tag_ns, exc)


# ═══════════════════════════════════════════════════════════════════════
# Full sync tasks (one-shot, dispatched by views)
# ═══════════════════════════════════════════════════════════════════════


@shared_task
def sync_omni_contacts(org_id: str, job_id: str):
    """Full sync de contatos TalkHub Omni → CRM."""
    set_rls_context(org_id)
    from .sync_engine import sync_contacts

    org = Org.objects.get(id=org_id)
    job = TalkHubSyncJob.objects.get(id=job_id)
    try:
        sync_contacts(org, job)
    except Exception as exc:
        _fail_job(job, exc)

    TalkHubConnection.objects.filter(org=org, is_connected=True).update(
        last_sync_at=timezone.now()
    )


@shared_task
def sync_omni_tickets(org_id: str, job_id: str):
    """Sync de tickets TalkHub Omni ↔ Cases/Leads."""
    set_rls_context(org_id)
    from .sync_engine import sync_tickets

    org = Org.objects.get(id=org_id)
    job = TalkHubSyncJob.objects.get(id=job_id)
    try:
        sync_tickets(org, job)
    except Exception as exc:
        _fail_job(job, exc)


@shared_task
def sync_omni_ticket_list_structure(org_id: str):
    """Sync estrutura de ticket lists → Pipelines. 1x/dia."""
    set_rls_context(org_id)
    from .sync_engine import sync_ticket_list_structure

    org = Org.objects.get(id=org_id)
    sync_ticket_list_structure(org)


@shared_task
def sync_omni_tags(org_id: str):
    """Sync tags. 1x/dia."""
    set_rls_context(org_id)
    from .sync_engine import sync_tags

    org = Org.objects.get(id=org_id)
    sync_tags(org)


@shared_task
def sync_omni_team_members(org_id: str):
    """Sync membros da equipe. 1x/dia."""
    set_rls_context(org_id)
    from .sync_engine import sync_team_members

    org = Org.objects.get(id=org_id)
    sync_team_members(org)


@shared_task
def sync_omni_statistics(org_id: str):
    """Sync estatísticas. A cada 1 hora."""
    set_rls_context(org_id)
    from .sync_engine import sync_statistics

    org = Org.objects.get(id=org_id)
    sync_statistics(org)


# ═══════════════════════════════════════════════════════════════════════
# Periodic tasks (Celery Beat wrappers)
# ═══════════════════════════════════════════════════════════════════════


@shared_task
def periodic_sync_contacts():
    """Sync contacts para todas as orgs conectadas (a cada 5 min)."""
    for conn in _connected_orgs():
        org = conn.org
        set_rls_context(str(org.id))
        job = TalkHubSyncJob.objects.create(org=org, sync_type="contacts")
        sync_omni_contacts.delay(str(org.id), str(job.id))


@shared_task
def periodic_sync_tickets():
    """Sync tickets para todas as orgs conectadas."""
    for conn in _connected_orgs():
        org = conn.org
        set_rls_context(str(org.id))
        job = TalkHubSyncJob.objects.create(org=org, sync_type="tickets")
        sync_omni_tickets.delay(str(org.id), str(job.id))


@shared_task
def periodic_sync_tags():
    """Sync tags para todas as orgs conectadas (1x/dia)."""
    for conn in _connected_orgs():
        sync_omni_tags.delay(str(conn.org_id))


@shared_task
def periodic_sync_team_members():
    """Sync membros para todas as orgs conectadas (1x/dia)."""
    for conn in _connected_orgs():
        sync_omni_team_members.delay(str(conn.org_id))


@shared_task
def periodic_sync_ticket_structure():
    """Sync estrutura de ticket lists (1x/dia)."""
    for conn in _connected_orgs():
        sync_omni_ticket_list_structure.delay(str(conn.org_id))


@shared_task
def periodic_sync_statistics():
    """Sync estatísticas para todas as orgs conectadas (1x/hora)."""
    for conn in _connected_orgs():
        sync_omni_statistics.delay(str(conn.org_id))


@shared_task
def periodic_cleanup_old_logs():
    """Limpar logs antigos (>30 dias). 1x/dia."""
    from django.utils import timezone as tz
    from datetime import timedelta

    cutoff = tz.now() - timedelta(days=30)
    deleted, _ = TalkHubSyncJob.objects.filter(created_at__lt=cutoff).delete()
    logger.info("Cleaned up %d old sync jobs", deleted)


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


def _connected_orgs():
    """Retornar todas as conexões TalkHub ativas."""
    return TalkHubConnection.objects.filter(
        is_connected=True
    ).select_related("org")


def _fail_job(job, exc):
    """Marcar job como falho."""
    logger.exception("Sync job %s failed: %s", job.id, exc)
    job.status = "FAILED"
    job.error_log = [{"error": str(exc)}]
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "error_log", "completed_at", "updated_at"])


def _log_error(org, operation, entity_type, entity_id, exc):
    """Registrar erro de integração."""
    try:
        from integrations.models import IntegrationLog

        IntegrationLog.objects.create(
            org=org,
            connector_slug="talkhub-omni",
            operation=operation,
            direction="out",
            entity_type=entity_type,
            entity_id=str(entity_id),
            status="error",
            error_detail=str(exc),
        )
    except Exception:
        pass
