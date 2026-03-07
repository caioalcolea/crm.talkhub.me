"""
Celery tasks do app campaigns.

- check_scheduled_campaigns: Beat task que verifica campanhas agendadas.
- execute_email_blast: Envia email blast em lotes.
- execute_whatsapp_broadcast: Envia WhatsApp broadcast em lotes.
- execute_nurture_step: Executa um step de nurture sequence para um recipient.
"""

import logging
import time

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template import Template, Context
from django.utils import timezone

from common.tasks import set_rls_context

logger = logging.getLogger(__name__)


def _render_template(body_template, contact):
    """Render body_template substituindo variáveis de contato."""
    context = {
        "contact": {
            "first_name": contact.first_name or "",
            "last_name": contact.last_name or "",
            "email": contact.email or "",
            "organization": contact.organization or "",
            "phone": contact.phone or "",
        }
    }
    try:
        # Support both {{var}} and Django template syntax
        text = body_template
        text = text.replace("{{contact.first_name}}", contact.first_name or "")
        text = text.replace("{{contact.last_name}}", contact.last_name or "")
        text = text.replace("{{contact.email}}", contact.email or "")
        text = text.replace("{{contact.organization}}", contact.organization or "")
        text = text.replace("{{contact.phone}}", contact.phone or "")
        return text
    except Exception:
        return body_template


@shared_task(name="campaigns.tasks.check_scheduled_campaigns")
def check_scheduled_campaigns():
    """
    Beat task (a cada minuto): verifica campanhas agendadas cujo
    scheduled_at já passou e dispara a task de execução apropriada.
    """
    from campaigns.models import Campaign
    from common.models import Org

    now = timezone.now()
    campaigns = Campaign.objects.filter(
        status="scheduled",
        scheduled_at__lte=now,
    ).select_related("org")

    for campaign in campaigns:
        set_rls_context(campaign.org_id)
        campaign.status = "running"
        campaign.started_at = now
        campaign.save(update_fields=["status", "started_at", "updated_at"])

        if campaign.campaign_type == "email_blast":
            execute_email_blast.delay(str(campaign.id), str(campaign.org_id))
        elif campaign.campaign_type == "whatsapp_broadcast":
            execute_whatsapp_broadcast.delay(str(campaign.id), str(campaign.org_id))
        elif campaign.campaign_type == "nurture_sequence":
            execute_nurture_first_step.delay(str(campaign.id), str(campaign.org_id))


@shared_task(name="campaigns.tasks.execute_email_blast")
def execute_email_blast(campaign_id, org_id):
    """
    Envia email blast em lotes de 50 com throttle de 1s entre lotes.
    Inclui tracking pixel e link de unsubscribe.
    """
    from campaigns.models import Campaign, CampaignRecipient

    set_rls_context(org_id)

    try:
        campaign = Campaign.objects.get(id=campaign_id, org_id=org_id)
    except Campaign.DoesNotExist:
        logger.error("Campaign %s not found for org %s", campaign_id, org_id)
        return

    if campaign.status not in ("running",):
        logger.info("Campaign %s status is %s, skipping", campaign_id, campaign.status)
        return

    recipients = CampaignRecipient.objects.filter(
        campaign=campaign, org_id=org_id, status="pending"
    ).select_related("contact").order_by("created_at")

    batch_size = 50
    batch = []

    for recipient in recipients.iterator():
        # Check if campaign was paused
        campaign.refresh_from_db(fields=["status"])
        if campaign.status == "paused":
            logger.info("Campaign %s paused, stopping", campaign_id)
            return

        batch.append(recipient)
        if len(batch) >= batch_size:
            _send_email_batch(campaign, batch, org_id)
            batch = []
            time.sleep(1)  # Throttle between batches

    # Send remaining
    if batch:
        _send_email_batch(campaign, batch, org_id)

    # Mark completed
    campaign.refresh_from_db()
    if campaign.status == "running":
        campaign.status = "completed"
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=["status", "completed_at", "updated_at"])
        logger.info("Campaign %s completed", campaign_id)


def _send_email_batch(campaign, recipients, org_id):
    """Send a batch of emails for a campaign."""
    from campaigns.models import CampaignRecipient

    for recipient in recipients:
        contact = recipient.contact
        if not contact.email:
            recipient.status = "failed"
            recipient.error_detail = "Contato sem email"
            recipient.save(update_fields=["status", "error_detail", "updated_at"])
            campaign.failed_count += 1
            campaign.save(update_fields=["failed_count"])
            continue

        try:
            body = _render_template(campaign.body_template, contact)

            # Add tracking pixel
            tracking_url = f"{settings.DOMAIN_NAME}/track/open/{recipient.id}/"
            tracking_pixel = f'<img src="{tracking_url}" width="1" height="1" alt="" />'

            # Add unsubscribe link
            unsubscribe_url = f"{settings.DOMAIN_NAME}/track/unsubscribe/{recipient.id}/"
            unsubscribe_link = (
                f'<br/><p style="font-size:11px;color:#999;">'
                f'<a href="{unsubscribe_url}">Descadastrar-se</a></p>'
            )

            html_body = body + tracking_pixel + unsubscribe_link

            msg = EmailMessage(
                subject=campaign.subject or "Sem assunto",
                body=html_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[contact.email],
            )
            msg.content_subtype = "html"
            msg.send()

            recipient.status = "sent"
            recipient.sent_at = timezone.now()
            recipient.save(update_fields=["status", "sent_at", "updated_at"])
            campaign.sent_count += 1
            campaign.save(update_fields=["sent_count"])

        except Exception as exc:
            logger.exception(
                "Failed to send email to %s for campaign %s",
                contact.email, campaign.id,
            )
            recipient.status = "failed"
            recipient.error_detail = str(exc)[:500]
            recipient.save(update_fields=["status", "error_detail", "updated_at"])
            campaign.failed_count += 1
            campaign.save(update_fields=["failed_count"])


@shared_task(name="campaigns.tasks.execute_whatsapp_broadcast")
def execute_whatsapp_broadcast(campaign_id, org_id):
    """
    Envia WhatsApp broadcast em lotes de 20 com throttle de 2s.
    Valida canal WhatsApp ativo na org antes de enviar.
    """
    from campaigns.models import Campaign, CampaignRecipient
    from talkhub_omni.models import TalkHubConnection

    set_rls_context(org_id)

    try:
        campaign = Campaign.objects.get(id=campaign_id, org_id=org_id)
    except Campaign.DoesNotExist:
        logger.error("Campaign %s not found for org %s", campaign_id, org_id)
        return

    if campaign.status not in ("running",):
        return

    # Validate active WhatsApp channel
    connection = TalkHubConnection.objects.filter(
        org_id=org_id, is_active=True
    ).first()

    if not connection:
        campaign.status = "cancelled"
        campaign.save(update_fields=["status", "updated_at"])
        logger.error(
            "Campaign %s cancelled: no active TalkHub connection for org %s",
            campaign_id, org_id,
        )
        return

    from talkhub_omni.client import TalkHubClient
    from cryptography.fernet import Fernet

    # Decrypt API key
    try:
        fernet_key = settings.SECRET_KEY[:32].ljust(32, "=")
        f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
        api_key = f.decrypt(connection.api_key.encode()).decode()
    except Exception:
        api_key = connection.api_key

    client = TalkHubClient(api_key=api_key, base_url=connection.base_url)

    recipients = CampaignRecipient.objects.filter(
        campaign=campaign, org_id=org_id, status="pending"
    ).select_related("contact").order_by("created_at")

    batch_size = 20
    batch = []

    for recipient in recipients.iterator():
        campaign.refresh_from_db(fields=["status"])
        if campaign.status == "paused":
            return

        batch.append(recipient)
        if len(batch) >= batch_size:
            _send_whatsapp_batch(campaign, batch, client)
            batch = []
            time.sleep(2)

    if batch:
        _send_whatsapp_batch(campaign, batch, client)

    campaign.refresh_from_db()
    if campaign.status == "running":
        campaign.status = "completed"
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=["status", "completed_at", "updated_at"])


def _send_whatsapp_batch(campaign, recipients, client):
    """Send a batch of WhatsApp messages."""
    for recipient in recipients:
        contact = recipient.contact

        if not contact.phone:
            recipient.status = "failed"
            recipient.error_detail = "Contato sem telefone"
            recipient.save(update_fields=["status", "error_detail", "updated_at"])
            campaign.failed_count += 1
            campaign.save(update_fields=["failed_count"])
            continue

        # Need omni_user_ns or talkhub_subscriber_id to send
        user_ns = contact.omni_user_ns or contact.talkhub_subscriber_id
        if not user_ns:
            recipient.status = "failed"
            recipient.error_detail = "Contato sem ID TalkHub Omni"
            recipient.save(update_fields=["status", "error_detail", "updated_at"])
            campaign.failed_count += 1
            campaign.save(update_fields=["failed_count"])
            continue

        try:
            body = _render_template(campaign.body_template, contact)
            client.send_text(user_ns, body)

            recipient.status = "sent"
            recipient.sent_at = timezone.now()
            recipient.save(update_fields=["status", "sent_at", "updated_at"])
            campaign.sent_count += 1
            campaign.save(update_fields=["sent_count"])

        except Exception as exc:
            logger.exception(
                "Failed to send WhatsApp to %s for campaign %s",
                contact.phone, campaign.id,
            )
            recipient.status = "failed"
            recipient.error_detail = str(exc)[:500]
            recipient.save(update_fields=["status", "error_detail", "updated_at"])
            campaign.failed_count += 1
            campaign.save(update_fields=["failed_count"])


@shared_task(name="campaigns.tasks.execute_nurture_first_step")
def execute_nurture_first_step(campaign_id, org_id):
    """
    Inicia nurture sequence: processa step_order=1 para todos os recipients.
    Agenda próximo step via ETA após delay_hours.
    """
    from campaigns.models import Campaign, CampaignRecipient, CampaignStep

    set_rls_context(org_id)

    try:
        campaign = Campaign.objects.get(id=campaign_id, org_id=org_id)
    except Campaign.DoesNotExist:
        return

    if campaign.status not in ("running",):
        return

    first_step = CampaignStep.objects.filter(
        campaign=campaign, org_id=org_id, step_order=1
    ).first()

    if not first_step:
        campaign.status = "cancelled"
        campaign.save(update_fields=["status", "updated_at"])
        logger.error("Campaign %s has no steps", campaign_id)
        return

    recipients = CampaignRecipient.objects.filter(
        campaign=campaign, org_id=org_id, status="pending"
    ).select_related("contact")

    for recipient in recipients:
        execute_nurture_step.delay(
            str(campaign.id), str(recipient.id), str(org_id), 1
        )


@shared_task(name="campaigns.tasks.execute_nurture_step")
def execute_nurture_step(campaign_id, recipient_id, org_id, step_order):
    """
    Executa um step de nurture sequence para um recipient.
    Ao concluir, agenda o próximo step com delay.
    """
    from campaigns.models import Campaign, CampaignRecipient, CampaignStep

    set_rls_context(org_id)

    try:
        campaign = Campaign.objects.get(id=campaign_id, org_id=org_id)
        recipient = CampaignRecipient.objects.select_related("contact").get(
            id=recipient_id, org_id=org_id
        )
    except (Campaign.DoesNotExist, CampaignRecipient.DoesNotExist):
        return

    if campaign.status not in ("running",):
        return

    if recipient.status == "unsubscribed":
        return

    step = CampaignStep.objects.filter(
        campaign=campaign, org_id=org_id, step_order=step_order
    ).first()

    if not step:
        # No more steps — mark recipient as sent (sequence complete)
        recipient.status = "sent"
        recipient.sent_at = timezone.now()
        recipient.save(update_fields=["status", "sent_at", "updated_at"])
        campaign.sent_count += 1
        campaign.save(update_fields=["sent_count"])
        _check_nurture_completion(campaign)
        return

    contact = recipient.contact
    body = _render_template(step.body_template, contact)
    success = False

    if step.channel == "email":
        if not contact.email:
            recipient.error_detail = f"Step {step_order}: sem email"
            recipient.save(update_fields=["error_detail", "updated_at"])
        else:
            try:
                tracking_url = f"{settings.DOMAIN_NAME}/track/open/{recipient.id}/"
                pixel = f'<img src="{tracking_url}" width="1" height="1" alt="" />'
                unsub_url = f"{settings.DOMAIN_NAME}/track/unsubscribe/{recipient.id}/"
                unsub = f'<br/><p style="font-size:11px;color:#999;"><a href="{unsub_url}">Descadastrar-se</a></p>'

                msg = EmailMessage(
                    subject=step.subject or campaign.subject or "Sem assunto",
                    body=body + pixel + unsub,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[contact.email],
                )
                msg.content_subtype = "html"
                msg.send()
                success = True
            except Exception as exc:
                logger.exception("Nurture email failed step %d recipient %s", step_order, recipient_id)
                recipient.error_detail = f"Step {step_order}: {str(exc)[:200]}"
                recipient.save(update_fields=["error_detail", "updated_at"])

    elif step.channel == "whatsapp":
        user_ns = contact.omni_user_ns or contact.talkhub_subscriber_id
        if not user_ns or not contact.phone:
            recipient.error_detail = f"Step {step_order}: sem telefone/ID TalkHub"
            recipient.save(update_fields=["error_detail", "updated_at"])
        else:
            try:
                from talkhub_omni.models import TalkHubConnection
                from talkhub_omni.client import TalkHubClient

                conn = TalkHubConnection.objects.filter(
                    org_id=org_id, is_active=True
                ).first()
                if conn:
                    from cryptography.fernet import Fernet
                    try:
                        fernet_key = settings.SECRET_KEY[:32].ljust(32, "=")
                        f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
                        api_key = f.decrypt(conn.api_key.encode()).decode()
                    except Exception:
                        api_key = conn.api_key
                    client = TalkHubClient(api_key=api_key, base_url=conn.base_url)
                    client.send_text(user_ns, body)
                    success = True
                else:
                    recipient.error_detail = f"Step {step_order}: sem conexão TalkHub ativa"
                    recipient.save(update_fields=["error_detail", "updated_at"])
            except Exception as exc:
                logger.exception("Nurture WhatsApp failed step %d recipient %s", step_order, recipient_id)
                recipient.error_detail = f"Step {step_order}: {str(exc)[:200]}"
                recipient.save(update_fields=["error_detail", "updated_at"])

    if success:
        step.sent_count += 1
        step.save(update_fields=["sent_count"])
        recipient.current_step = step_order
        recipient.save(update_fields=["current_step", "updated_at"])

        # Schedule next step
        next_step = CampaignStep.objects.filter(
            campaign=campaign, org_id=org_id, step_order=step_order + 1
        ).first()

        if next_step:
            eta = timezone.now() + timezone.timedelta(hours=next_step.delay_hours)
            execute_nurture_step.apply_async(
                args=[str(campaign_id), str(recipient_id), str(org_id), step_order + 1],
                eta=eta,
            )
        else:
            # Last step completed
            recipient.status = "sent"
            recipient.sent_at = timezone.now()
            recipient.save(update_fields=["status", "sent_at", "updated_at"])
            campaign.sent_count += 1
            campaign.save(update_fields=["sent_count"])
            _check_nurture_completion(campaign)


def _check_nurture_completion(campaign):
    """Check if all recipients have completed the nurture sequence."""
    from campaigns.models import CampaignRecipient

    pending = CampaignRecipient.objects.filter(
        campaign=campaign, status="pending"
    ).exists()

    if not pending and campaign.status == "running":
        campaign.status = "completed"
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=["status", "completed_at", "updated_at"])
