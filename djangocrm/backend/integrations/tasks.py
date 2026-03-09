"""
Celery tasks do app integrations.

- process_webhook: Processar webhook recebido (retry com backoff).
- run_connector_sync: Executar sync de conector específico.
- cleanup_old_logs: Remover logs antigos (>90 dias).
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from common.tasks import set_rls_context

logger = logging.getLogger(__name__)

# Backoff delays para retry de webhook: 30s, 2min, 10min
WEBHOOK_RETRY_DELAYS = [30, 120, 600]


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_webhook(self, connector_slug: str, org_id: str, payload: dict, headers: dict):
    """
    Processar webhook recebido. Retry com backoff: 30s, 2min, 10min.

    Delega o processamento para o handle_webhook do conector.
    """
    from common.models import Org
    from integrations.models import IntegrationLog, WebhookLog
    from integrations.registry import ConnectorRegistry

    set_rls_context(org_id)

    connector_cls = ConnectorRegistry.get(connector_slug)
    if not connector_cls:
        logger.error("Connector not found for webhook: %s", connector_slug)
        return

    connector = connector_cls()
    org = Org.objects.get(id=org_id)

    try:
        result = connector.handle_webhook(org, payload, headers)

        # Atualizar status do webhook log mais recente
        webhook_log = (
            WebhookLog.objects.filter(org_id=org_id, connector_slug=connector_slug)
            .order_by("-created_at")
            .first()
        )
        if webhook_log and webhook_log.status == "queued":
            webhook_log.status = "processed"
            webhook_log.save(update_fields=["status", "updated_at"])

        return result

    except Exception as exc:
        delay = WEBHOOK_RETRY_DELAYS[min(self.request.retries, len(WEBHOOK_RETRY_DELAYS) - 1)]

        IntegrationLog.objects.create(
            org_id=org_id,
            connector_slug=connector_slug,
            operation="webhook",
            direction="in",
            entity_type="webhook",
            status="error",
            error_detail=str(exc),
        )

        logger.warning(
            "Webhook processing failed (attempt %d/%d): %s - %s",
            self.request.retries + 1,
            self.max_retries + 1,
            connector_slug,
            exc,
        )
        raise self.retry(exc=exc, countdown=delay)


@shared_task(name="integrations.tasks.run_connector_sync")
def run_connector_sync(connector_slug: str, org_id: str, sync_type: str, job_id: str):
    """
    Executar sync de um conector específico.

    Atualiza o SyncJob com contadores e status final.
    """
    from common.models import Org
    from integrations.models import SyncJob
    from integrations.registry import ConnectorRegistry

    set_rls_context(org_id)

    connector_cls = ConnectorRegistry.get(connector_slug)
    if not connector_cls:
        logger.error("Connector not found for sync: %s", connector_slug)
        return

    connector = connector_cls()
    org = Org.objects.get(id=org_id)
    job = SyncJob.objects.get(id=job_id)

    job.status = "IN_PROGRESS"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "updated_at"])

    try:
        result = connector.sync(org, sync_type, str(job_id))

        job.status = "COMPLETED"
        job.total_records = result.get("total", 0)
        job.imported_count = result.get("imported", 0)
        job.updated_count = result.get("updated", 0)
        job.skipped_count = result.get("skipped", 0)
        job.error_count = result.get("errors", 0)
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "total_records",
                "imported_count",
                "updated_count",
                "skipped_count",
                "error_count",
                "completed_at",
                "updated_at",
            ]
        )

        logger.info(
            "Sync completed: %s/%s - imported=%d, updated=%d, errors=%d",
            connector_slug,
            sync_type,
            job.imported_count,
            job.updated_count,
            job.error_count,
        )
        return result

    except Exception as exc:
        job.status = "FAILED"
        job.error_log = [{"error": str(exc), "timestamp": timezone.now().isoformat()}]
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_log", "completed_at", "updated_at"])

        logger.error("Sync failed: %s/%s - %s", connector_slug, sync_type, exc)
        raise


@shared_task(name="integrations.tasks.sync_conversation_status_to_chatwoot", max_retries=2, default_retry_delay=5)
def sync_conversation_status_to_chatwoot(org_id: str, chatwoot_conversation_id: int, new_status: str):
    """
    Sync a CRM status change to Chatwoot (fire-and-forget).

    Called when user changes conversation status in the CRM UI.
    Maps CRM status → Chatwoot status and calls the Chatwoot API.
    """
    set_rls_context(org_id)

    from integrations.models import IntegrationConnection

    conn = IntegrationConnection.objects.filter(
        org_id=org_id, connector_slug="chatwoot", is_active=True, is_connected=True,
    ).first()
    if not conn:
        return

    from chatwoot.connector import _api_request, _decrypt_config
    config = _decrypt_config(conn.config_json or {})

    # Map CRM status → Chatwoot status
    crm_to_chatwoot = {"open": "open", "pending": "pending", "resolved": "resolved"}
    cw_status = crm_to_chatwoot.get(new_status)
    if not cw_status:
        return

    try:
        resp = _api_request(config, "POST", f"/conversations/{chatwoot_conversation_id}/toggle_status", json={
            "status": cw_status,
        })
        if resp.status_code in (200, 201):
            logger.info("Synced status '%s' to Chatwoot conversation %s", cw_status, chatwoot_conversation_id)
        else:
            logger.warning("Failed to sync status to Chatwoot: %s %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Error syncing status to Chatwoot: %s", exc)


@shared_task(name="integrations.tasks.cleanup_old_logs")
def cleanup_old_logs():
    """
    Remover IntegrationLog e WebhookLog com mais de 90 dias.

    Executar diariamente via Celery Beat.
    """
    from integrations.models import IntegrationLog, WebhookLog

    cutoff = timezone.now() - timedelta(days=90)

    deleted_logs, _ = IntegrationLog.objects.filter(created_at__lt=cutoff).delete()
    deleted_webhooks, _ = WebhookLog.objects.filter(created_at__lt=cutoff).delete()

    logger.info(
        "Cleanup completed: deleted %d integration logs, %d webhook logs",
        deleted_logs,
        deleted_webhooks,
    )
    return {"deleted_logs": deleted_logs, "deleted_webhooks": deleted_webhooks}


@shared_task(name="integrations.tasks.check_pending_syncs")
def check_pending_syncs():
    """
    Verificar integrações com sync pendente baseado no intervalo configurado.

    Roda a cada 5 minutos via Celery Beat. Para cada connection ativa com
    sync_interval_minutes configurado, verifica se o tempo desde o último
    sync excede o intervalo e dispara run_connector_sync.
    """
    from django.db import connection as db_conn

    from integrations.models import IntegrationConnection, SyncJob

    now = timezone.now()

    # Get all org IDs (organization table has no RLS)
    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM organization")
        org_ids = [row[0] for row in cursor.fetchall()]

    queued = 0
    for org_id in org_ids:
        set_rls_context(str(org_id))

        connections = IntegrationConnection.objects.filter(
            is_active=True, is_connected=True
        )
        for conn in connections:
            interval = conn.sync_interval_minutes or 60
            if interval < 5:
                interval = 5

            # Verificar se o último sync foi há mais tempo que o intervalo
            if conn.last_sync_at:
                elapsed = (now - conn.last_sync_at).total_seconds() / 60
                if elapsed < interval:
                    continue

            # Verificar se já existe um sync em andamento
            running = SyncJob.objects.filter(
                org_id=conn.org_id,
                connector_slug=conn.connector_slug,
                status__in=["PENDING", "IN_PROGRESS"],
            ).exists()
            if running:
                continue

            # Criar SyncJob e disparar task
            job = SyncJob.objects.create(
                org_id=conn.org_id,
                connector_slug=conn.connector_slug,
                sync_type="all",
                status="PENDING",
            )
            run_connector_sync.delay(
                conn.connector_slug, str(conn.org_id), "all", str(job.id)
            )
            queued += 1

            logger.info(
                "Queued scheduled sync: %s (org=%s, interval=%dmin)",
                conn.connector_slug,
                conn.org_id,
                interval,
            )

    logger.info("check_pending_syncs: queued %d syncs", queued)


@shared_task(name="integrations.tasks.check_integration_health")
def check_integration_health():
    """
    Verificar saúde de todas as integrações ativas.

    Lógica de degradação:
    - error_count > 5  → "degraded"
    - error_count > 15 → "down"
    - senão             → "healthy"

    Envia email ao admin quando status muda para "down".
    Roda a cada 10 minutos via Celery Beat.
    """
    from django.conf import settings
    from django.core.mail import send_mail
    from django.db import connection as db_conn

    from integrations.models import IntegrationConnection

    # Get all org IDs (organization table has no RLS)
    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM organization")
        org_ids = [row[0] for row in cursor.fetchall()]

    checked = 0
    for org_id in org_ids:
        set_rls_context(str(org_id))

        connections = IntegrationConnection.objects.filter(is_active=True)
        for conn in connections:
            checked += 1
            old_status = conn.health_status

            if conn.error_count > 15:
                new_status = "down"
            elif conn.error_count > 5:
                new_status = "degraded"
            else:
                new_status = "healthy"

            if new_status != old_status:
                conn.health_status = new_status
                conn.save(update_fields=["health_status", "updated_at"])

                logger.info(
                    "Health status changed: %s (%s) %s → %s",
                    conn.connector_slug,
                    conn.org_id,
                    old_status,
                    new_status,
                )

                # Enviar email ao admin quando status muda para "down"
                if new_status == "down":
                    try:
                        admin_email = getattr(settings, "DEFAULT_FROM_EMAIL", "adm@talkhub.me")
                        send_mail(
                            subject=f"[TalkHub CRM] Integração {conn.display_name} fora do ar",
                            message=(
                                f"A integração {conn.display_name} ({conn.connector_slug}) "
                                f"está fora do ar.\n\n"
                                f"Erros consecutivos: {conn.error_count}\n"
                                f"Último erro: {conn.last_error or 'N/A'}\n"
                                f"Último sync: {conn.last_sync_at or 'Nunca'}\n\n"
                                f"Verifique o painel de integrações para mais detalhes."
                            ),
                            from_email=admin_email,
                            recipient_list=[admin_email],
                            fail_silently=True,
                        )
                    except Exception as exc:
                        logger.error("Failed to send health alert email: %s", exc)

    logger.info("Health check completed for %d active connections", checked)


@shared_task(name="integrations.tasks.run_integration_review")
def run_integration_review(org_id: str, auto_fix: bool = False):
    """
    Executar revisão de integridade para uma org.

    Pode ser agendado via Celery Beat (diário) ou disparado manualmente.
    """
    from common.models import Org
    from integrations.review_agent import IntegrationReviewAgent

    set_rls_context(org_id)

    org = Org.objects.get(id=org_id)
    agent = IntegrationReviewAgent(org, auto_fix=auto_fix)
    report = agent.run_full_review()

    logger.info(
        "Integration review for org %s: %d issues (%d critical, %d fixed)",
        org_id,
        len(report.issues),
        report.critical_count,
        len(report.fixes_applied),
    )

    return report.to_dict()

@shared_task(name="integrations.tasks.periodic_review_integrations")
def periodic_review_integrations():
    """
    Executar revisão de integridade para todas as orgs com integrações ativas.

    Roda diariamente via Celery Beat. Auto-fix habilitado para correções seguras.
    """
    from integrations.models import IntegrationConnection

    active_orgs = (
        IntegrationConnection.objects.filter(is_active=True)
        .values_list("org_id", flat=True)
        .distinct()
    )

    for org_id in active_orgs:
        try:
            run_integration_review.delay(str(org_id), auto_fix=True)
        except Exception as exc:
            logger.error("Failed to queue review for org %s: %s", org_id, exc)

    logger.info("Queued integration reviews for %d orgs", len(active_orgs))
