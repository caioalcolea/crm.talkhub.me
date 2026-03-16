"""
Celery tasks for the assistant scheduler.

process_scheduled_jobs: Runs every minute, picks up due jobs and executes them.
execute_job: Executes a single ScheduledJob (dispatch + task creation).
recalculate_policy_schedules: Recalculates next_run_at after policy/target changes.
"""

import logging

from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from common.tasks import set_rls_context

logger = logging.getLogger(__name__)


@shared_task(name="assistant.tasks.process_scheduled_jobs")
def process_scheduled_jobs():
    """
    Process due scheduled jobs. Runs every minute via Celery Beat.

    Uses SELECT FOR UPDATE SKIP LOCKED to prevent duplicate execution
    across multiple workers.
    """
    from assistant.models import ScheduledJob

    now = timezone.now()

    # Find due jobs that are pending and not requiring approval
    due_jobs = (
        ScheduledJob.objects.filter(
            status="pending",
            due_at__lte=now,
            approval_required=False,
        )
        .select_for_update(skip_locked=True)
        .values_list("id", "org_id")[:50]  # Process in batches
    )

    with transaction.atomic():
        job_list = list(due_jobs)

    for job_id, org_id in job_list:
        execute_job.delay(str(job_id), str(org_id))

    if job_list:
        logger.info("Dispatched %d due jobs for execution", len(job_list))


@shared_task(name="assistant.tasks.execute_job", bind=True, max_retries=2)
def execute_job(self, job_id, org_id):
    """
    Execute a single ScheduledJob.

    Steps:
    1. Lock the job (status -> locked)
    2. Dispatch message via configured channel
    3. Create task if task_config.enabled
    4. Update policy run counters and schedule next run
    5. Mark job as completed or failed
    """
    from assistant.models import ChannelDispatch, ScheduledJob, TaskLink
    from assistant.dispatch import dispatch_message
    from assistant.engine import generate_jobs_for_policy
    from assistant.template_engine import render_template

    set_rls_context(org_id)

    try:
        job = ScheduledJob.objects.select_for_update().get(id=job_id)
    except ScheduledJob.DoesNotExist:
        logger.error("Job %s not found", job_id)
        return

    if job.status != "pending":
        logger.info("Job %s already in status %s, skipping", job_id, job.status)
        return

    # Lock the job
    job.status = "locked"
    job.attempt_count = F("attempt_count") + 1
    job.save(update_fields=["status", "attempt_count", "updated_at"])
    job.refresh_from_db()

    # Route campaign_step jobs to dedicated handler
    if job.job_type == "campaign_step":
        _execute_campaign_step_job(job, org_id)
        return

    payload = job.payload or {}
    channel_config = payload.get("channel_config", {})
    task_config = payload.get("task_config", {})
    message_template = payload.get("message_template", "")
    module_key = payload.get("module_key", "")

    try:
        # Build context for template rendering
        context = _build_context_for_job(job)

        # Render message
        rendered_message = render_template(message_template, context, module_key)

        # Dispatch via channel
        channel_type = channel_config.get("channel_type", "internal")
        destination = _resolve_destination(job, channel_config)

        if destination:
            message_data = {
                "subject": rendered_message[:100] if rendered_message else "",
                "body": rendered_message,
            }

            result = dispatch_message(
                str(org_id), channel_type, destination, message_data
            )

            # Record dispatch
            ChannelDispatch.objects.create(
                org=job.org,
                scheduled_job=job,
                channel_type=channel_type,
                destination=destination,
                message_payload=message_data,
                status="sent" if result.get("success") else "failed",
                provider_message_id=result.get("message_id", ""),
                error_message=result.get("error", ""),
                sent_at=timezone.now() if result.get("success") else None,
            )

        # Create task if configured
        if task_config.get("enabled"):
            _create_task_for_job(job, task_config, context, module_key)

        # Mark completed
        job.status = "completed"
        job.save(update_fields=["status", "updated_at"])

        # Update source policy
        _update_policy_after_run(job, success=True)

    except Exception as exc:
        logger.exception("Job %s execution failed: %s", job_id, exc)
        job.status = "failed"
        job.last_error = str(exc)[:1000]
        job.save(update_fields=["status", "last_error", "updated_at"])

        _update_policy_after_run(job, success=False)

        # Retry if under max attempts
        job.refresh_from_db()
        if job.attempt_count < job.max_attempts:
            raise self.retry(exc=exc, countdown=60 * job.attempt_count)


@shared_task(name="assistant.tasks.recalculate_policy_schedules")
def recalculate_policy_schedules(policy_id=None):
    """
    Recalculate next_run_at for active policies.

    If policy_id is given, only recalculate that policy.
    Otherwise, recalculate all active policies.
    """
    from assistant.models import ReminderPolicy
    from assistant.engine import cancel_stale_jobs, generate_jobs_for_policy

    if policy_id:
        policies = ReminderPolicy.objects.filter(id=policy_id, is_active=True)
    else:
        policies = ReminderPolicy.objects.filter(is_active=True)

    for policy in policies:
        set_rls_context(str(policy.org_id))
        # Cancel existing pending jobs — they'll be regenerated
        cancel_stale_jobs(policy)
        # Generate new jobs based on current state
        generate_jobs_for_policy(policy)

    logger.info("Recalculated schedules for %d policies", policies.count())


def _execute_campaign_step_job(job, org_id):
    """
    Execute a campaign step job for a single recipient.

    1. Load Campaign + CampaignRecipient from payload
    2. Verify campaign is running and recipient is valid
    3. Render template with contact data
    4. Send via channel (email with tracking/unsub, or whatsapp)
    5. Create ChannelDispatch record
    6. Update CampaignRecipient status and Campaign counters
    7. For nurture: generate job for next step
    """
    from django.conf import settings
    from django.core.mail import EmailMessage
    from django.db.models import F

    from assistant.models import ChannelDispatch
    from campaigns.models import Campaign, CampaignRecipient

    payload = job.payload or {}
    campaign_id = payload.get("campaign_id")
    recipient_id = payload.get("recipient_id")
    channel = payload.get("channel", "email")
    step_order = payload.get("step_order", 0)
    subject = payload.get("subject", "")
    body_template = payload.get("body_template", "")

    try:
        campaign = Campaign.objects.get(id=campaign_id)
        recipient = CampaignRecipient.objects.select_related("contact").get(
            id=recipient_id
        )
    except (Campaign.DoesNotExist, CampaignRecipient.DoesNotExist):
        job.status = "failed"
        job.last_error = "Campaign or recipient not found"
        job.save(update_fields=["status", "last_error", "updated_at"])
        return

    # Verify campaign is still running
    if campaign.status not in ("running",):
        job.status = "skipped"
        job.save(update_fields=["status", "updated_at"])
        return

    # Skip unsubscribed recipients
    if recipient.status == "unsubscribed":
        job.status = "skipped"
        job.save(update_fields=["status", "updated_at"])
        return

    contact = recipient.contact
    body = _render_campaign_template(body_template, contact)
    success = False
    error_msg = ""
    provider_message_id = ""

    if channel == "email":
        success, error_msg = _send_campaign_email(
            campaign, recipient, contact, subject, body, org_id
        )
    elif channel == "whatsapp":
        success, error_msg, provider_message_id = _send_campaign_whatsapp(
            contact, body, org_id
        )

    # Create ChannelDispatch audit record
    destination = contact.email if channel == "email" else (contact.phone or "")
    ChannelDispatch.objects.create(
        org=job.org,
        scheduled_job=job,
        channel_type=f"campaign_{channel}",
        destination=destination,
        message_payload={"subject": subject, "body": body[:500]},
        status="sent" if success else "failed",
        provider_message_id=provider_message_id,
        error_message=error_msg,
        sent_at=timezone.now() if success else None,
    )

    # Update recipient and campaign counters
    _update_campaign_after_send(campaign, recipient, success, error_msg, step_order)

    if success:
        job.status = "completed"
        job.save(update_fields=["status", "updated_at"])

        # For nurture: generate next step job
        if campaign.campaign_type == "nurture_sequence" and step_order > 0:
            from campaigns.job_generator import generate_nurture_next_step_job
            next_job = generate_nurture_next_step_job(
                campaign, recipient, step_order
            )
            if not next_job:
                # Last step completed for this recipient
                recipient.status = "sent"
                recipient.sent_at = timezone.now()
                recipient.save(update_fields=["status", "sent_at", "updated_at"])
                Campaign.objects.filter(id=campaign.id).update(
                    sent_count=F("sent_count") + 1
                )

        # Check campaign completion
        _check_campaign_completion(campaign)
    else:
        job.status = "failed"
        job.last_error = error_msg[:1000]
        job.save(update_fields=["status", "last_error", "updated_at"])

        # Retry via Celery retry mechanism (handled by execute_job's except block)
        # For campaign jobs we don't retry automatically — mark as failed
        job.refresh_from_db()


def _render_campaign_template(body_template, contact):
    """Render campaign template with contact variables."""
    text = body_template
    text = text.replace("{{contact.first_name}}", contact.first_name or "")
    text = text.replace("{{contact.last_name}}", contact.last_name or "")
    text = text.replace("{{contact.email}}", contact.email or "")
    text = text.replace("{{contact.organization}}", contact.organization or "")
    text = text.replace("{{contact.phone}}", contact.phone or "")
    return text


def _send_campaign_email(campaign, recipient, contact, subject, body, org_id):
    """Send campaign email with tracking pixel and unsubscribe link."""
    from django.conf import settings
    from django.core.mail import EmailMessage

    if not contact.email:
        return False, "Contato sem email"

    try:
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
            subject=subject or "Sem assunto",
            body=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[contact.email],
        )
        msg.content_subtype = "html"
        msg.send()
        return True, ""
    except Exception as exc:
        logger.exception(
            "Campaign email failed for %s campaign %s",
            contact.email, campaign.id,
        )
        return False, str(exc)[:500]


def _send_campaign_whatsapp(contact, body, org_id):
    """Send campaign WhatsApp message via TalkHub."""
    from django.conf import settings

    if not contact.phone:
        return False, "Contato sem telefone", ""

    user_ns = getattr(contact, "omni_user_ns", None) or getattr(
        contact, "talkhub_subscriber_id", None
    )
    if not user_ns:
        return False, "Contato sem ID TalkHub Omni", ""

    try:
        from talkhub_omni.models import TalkHubConnection
        from talkhub_omni.client import TalkHubClient

        conn = TalkHubConnection.objects.filter(
            org_id=org_id, is_active=True
        ).first()
        if not conn:
            return False, "Sem conexão TalkHub ativa", ""

        from cryptography.fernet import Fernet

        try:
            fernet_key = settings.SECRET_KEY[:32].ljust(32, "=")
            f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
            api_key = f.decrypt(conn.api_key.encode()).decode()
        except Exception:
            api_key = conn.api_key

        client = TalkHubClient(api_key=api_key, base_url=conn.base_url)
        result = client.send_text(user_ns, body)
        msg_id = str(result) if result else ""
        return True, "", msg_id
    except Exception as exc:
        logger.exception(
            "Campaign WhatsApp failed for %s", contact.phone,
        )
        return False, str(exc)[:500], ""


def _update_campaign_after_send(campaign, recipient, success, error_msg, step_order):
    """Update recipient status and campaign counters after a send attempt."""
    from django.db.models import F
    from campaigns.models import Campaign, CampaignStep

    if success:
        if campaign.campaign_type == "nurture_sequence":
            # For nurture, update current_step; final "sent" is set when all steps done
            recipient.current_step = step_order
            recipient.save(update_fields=["current_step", "updated_at"])

            # Update step sent_count
            CampaignStep.objects.filter(
                campaign=campaign, step_order=step_order
            ).update(sent_count=F("sent_count") + 1)
        else:
            # For blast/broadcast, mark as sent immediately
            recipient.status = "sent"
            recipient.sent_at = timezone.now()
            recipient.save(update_fields=["status", "sent_at", "updated_at"])
            Campaign.objects.filter(id=campaign.id).update(
                sent_count=F("sent_count") + 1
            )
    else:
        recipient.status = "failed"
        recipient.error_detail = error_msg[:500]
        recipient.save(update_fields=["status", "error_detail", "updated_at"])
        Campaign.objects.filter(id=campaign.id).update(
            failed_count=F("failed_count") + 1
        )


def _check_campaign_completion(campaign):
    """Check if all recipients have been processed and mark campaign completed.

    Uses select_for_update to prevent race conditions when multiple workers
    finish their last jobs concurrently.
    """
    from assistant.models import ScheduledJob
    from campaigns.models import Campaign, CampaignRecipient

    from django.contrib.contenttypes.models import ContentType

    pending_recipients = CampaignRecipient.objects.filter(
        campaign=campaign, status="pending"
    ).count()

    campaign_ct = ContentType.objects.get_for_model(campaign)
    active_jobs = ScheduledJob.objects.filter(
        source_content_type=campaign_ct,
        source_object_id=campaign.id,
        status__in=["pending", "locked"],
    ).count()

    # active_jobs <= 1 because the current job is still "locked"
    if pending_recipients == 0 and active_jobs <= 1:
        with transaction.atomic():
            locked = Campaign.objects.select_for_update().get(id=campaign.id)
            if locked.status != "running":
                return
            locked.status = "completed"
            locked.completed_at = timezone.now()
            locked.save(update_fields=["status", "completed_at", "updated_at"])
            logger.info("Campaign %s completed", locked.id)


def _build_context_for_job(job):
    """Build template context by resolving the job's target."""
    context = {}
    if not job.target_content_type_id or not job.target_object_id:
        return context

    try:
        model_class = job.target_content_type.model_class()
        if model_class is None:
            return context

        target = model_class.objects.filter(pk=job.target_object_id).first()
        if not target:
            return context

        # Determine which context builder to use based on model
        model_name = model_class.__name__.lower()

        if model_name == "lancamento":
            # For lancamentos, build context from parcelas
            from assistant.template_engine import build_context_for_parcela
            parcelas = target.parcelas.filter(status="ABERTO").order_by("data_vencimento")
            if parcelas.exists():
                context = build_context_for_parcela(parcelas.first())
        elif model_name == "parcela":
            from assistant.template_engine import build_context_for_parcela
            context = build_context_for_parcela(target)
        elif model_name == "contact":
            context = {
                "contact_first_name": getattr(target, "first_name", "") or "",
                "contact_last_name": getattr(target, "last_name", "") or "",
                "contact_email": getattr(target, "email", "") or "",
                "contact_phone": getattr(target, "phone", "") or "",
                "contact_organization": getattr(target, "organization", "") or "",
            }
        elif model_name == "lead":
            from assistant.template_engine import build_context_for_lead
            context = build_context_for_lead(target)
        elif model_name == "task":
            from assistant.template_engine import build_context_for_task
            context = build_context_for_task(target)
        elif model_name == "opportunity":
            from assistant.template_engine import build_context_for_opportunity
            context = build_context_for_opportunity(target)
        elif model_name == "case":
            from assistant.template_engine import build_context_for_case
            context = build_context_for_case(target)
        elif model_name == "invoice":
            from assistant.template_engine import build_context_for_invoice
            context = build_context_for_invoice(target)
        else:
            # Generic context
            context = {
                "org_name": getattr(target.org, "name", "") if hasattr(target, "org") else "",
            }
    except Exception as e:
        logger.error("Failed to build context for job %s: %s", job.id, e)

    return context


def _resolve_destination(job, channel_config):
    """Resolve the destination address for a dispatch."""
    dest_type = channel_config.get("destination_type", "")
    dest_value = channel_config.get("destination_value", "")

    if dest_value:
        return dest_value

    if not job.target_content_type_id or not job.target_object_id:
        return None

    try:
        model_class = job.target_content_type.model_class()
        target = model_class.objects.filter(pk=job.target_object_id).first()
        if not target:
            return None

        if dest_type == "contact_email":
            contact = getattr(target, "contact", None)
            if contact:
                return getattr(contact, "email", None)
        elif dest_type == "owner_email":
            owner = getattr(target, "owner_user", None) or getattr(target, "created_by", None)
            if owner:
                return getattr(owner, "email", None)
        elif dest_type == "assigned_email":
            if job.assigned_user:
                return getattr(job.assigned_user, "email", None)
    except Exception as e:
        logger.error("Failed to resolve destination for job %s: %s", job.id, e)

    return None


def _create_task_for_job(job, task_config, context, module_key):
    """Create a Task and TaskLink for a job."""
    from assistant.template_engine import render_template
    from tasks.models import Task

    title_template = task_config.get("title_template", "Tarefa automática")
    desc_template = task_config.get("description_template", "")
    priority = task_config.get("priority", "Medium")

    title = render_template(title_template, context, module_key)
    description = render_template(desc_template, context, module_key) if desc_template else ""

    task = Task.objects.create(
        org=job.org,
        title=title[:255],
        description=description,
        priority=priority,
        status="New",
        created_by=job.assigned_user.user if job.assigned_user else None,
    )

    # Assign user if configured
    assign_to_id = task_config.get("assign_to_user_id")
    if assign_to_id:
        task.assigned_to.add(assign_to_id)
    elif job.assigned_user:
        task.assigned_to.add(job.assigned_user)

    # Create TaskLink
    source_ct = job.source_content_type
    TaskLink = job.org.tasklink_set.model  # noqa: N806
    from assistant.models import TaskLink

    TaskLink.objects.create(
        org=job.org,
        source_content_type=source_ct,
        source_object_id=job.source_object_id,
        task=task,
        sync_mode=task_config.get("mode", "per_run"),
        status="active",
    )

    logger.info("Created task %s linked to job %s", task.id, job.id)
    return task


def _update_policy_after_run(job, success):
    """Update the source ReminderPolicy after a job run."""
    from assistant.engine import generate_jobs_for_policy
    from assistant.models import ReminderPolicy

    if job.job_type not in ("reminder",):
        # campaign_step jobs update via _check_campaign_completion instead
        return

    policy_id = (job.payload or {}).get("policy_id")
    if not policy_id:
        return

    try:
        policy = ReminderPolicy.objects.get(id=policy_id)
        policy.last_run_at = timezone.now()
        update_fields = ["last_run_at", "updated_at"]

        if success:
            policy.run_count = F("run_count") + 1
            update_fields.append("run_count")
        else:
            policy.error_count = F("error_count") + 1
            update_fields.append("error_count")

        policy.save(update_fields=update_fields)
        policy.refresh_from_db()

        # Schedule next run
        generate_jobs_for_policy(policy)

    except ReminderPolicy.DoesNotExist:
        logger.warning("Policy %s not found when updating after job %s", policy_id, job.id)
