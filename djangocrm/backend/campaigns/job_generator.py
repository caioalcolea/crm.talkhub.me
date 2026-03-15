"""
Job generator for campaigns.

Creates ScheduledJob records per recipient so campaign execution flows through
the unified autopilot runtime (process_scheduled_jobs → execute_job).
"""

import hashlib
import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

logger = logging.getLogger(__name__)


def generate_idempotency_key(campaign_id, recipient_id, step_order=0):
    """Generate deterministic idempotency key for a campaign job."""
    raw = f"campaign-{campaign_id}-recipient-{recipient_id}-step-{step_order}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def generate_campaign_jobs(campaign):
    """
    Generate ScheduledJobs for all pending recipients of a campaign.

    - email_blast / whatsapp_broadcast: 1 job per recipient, due_at staggered
      for batching (email: 50/batch, 1s interval; whatsapp: 20/batch, 2s interval).
    - nurture_sequence: 1 job per recipient for step 1, due_at = now.
      Subsequent steps are generated after each step completes.

    Returns the number of jobs created.
    """
    from assistant.models import ScheduledJob
    from campaigns.models import CampaignRecipient, CampaignStep

    campaign_ct = ContentType.objects.get_for_model(campaign)
    contact_ct = ContentType.objects.get_for_model(campaign.recipients.model)

    now = timezone.now()
    created_count = 0

    if campaign.campaign_type == "nurture_sequence":
        first_step = CampaignStep.objects.filter(
            campaign=campaign, step_order=1
        ).first()
        if not first_step:
            logger.error("Campaign %s has no steps", campaign.id)
            return 0

        recipients = CampaignRecipient.objects.filter(
            campaign=campaign, status="pending"
        ).select_related("contact")

        for recipient in recipients:
            created = _create_job_for_recipient(
                campaign, recipient, campaign_ct, now,
                step_order=1,
                step=first_step,
            )
            if created:
                created_count += 1

    else:
        # email_blast or whatsapp_broadcast
        if campaign.campaign_type == "whatsapp_broadcast":
            batch_size = 20
            interval_seconds = 2
        else:
            batch_size = 50
            interval_seconds = 1

        recipients = CampaignRecipient.objects.filter(
            campaign=campaign, status="pending"
        ).select_related("contact").order_by("created_at")

        for idx, recipient in enumerate(recipients):
            # Stagger due_at for batching
            batch_number = idx // batch_size
            due_at = now + timedelta(seconds=batch_number * interval_seconds)

            created = _create_job_for_recipient(
                campaign, recipient, campaign_ct, due_at,
                step_order=0,
                step=None,
            )
            if created:
                created_count += 1

    logger.info(
        "Generated %d jobs for campaign %s (%s)",
        created_count, campaign.id, campaign.campaign_type,
    )
    return created_count


def generate_nurture_next_step_job(campaign, recipient, completed_step_order):
    """
    After completing a step, generate a job for the next step.
    due_at = now + next_step.delay_hours.

    Returns the created ScheduledJob or None.
    """
    from campaigns.models import CampaignStep

    next_step = CampaignStep.objects.filter(
        campaign=campaign, step_order=completed_step_order + 1
    ).first()

    if not next_step:
        return None

    campaign_ct = ContentType.objects.get_for_model(campaign)
    due_at = timezone.now() + timedelta(hours=next_step.delay_hours)

    return _create_job_for_recipient(
        campaign, recipient, campaign_ct, due_at,
        step_order=next_step.step_order,
        step=next_step,
    )


def cancel_campaign_jobs(campaign):
    """Cancel all pending jobs for a campaign (for pause/cancel)."""
    from assistant.models import ScheduledJob

    campaign_ct = ContentType.objects.get_for_model(campaign)
    updated = ScheduledJob.objects.filter(
        source_content_type=campaign_ct,
        source_object_id=campaign.id,
        status="pending",
    ).update(status="cancelled")

    if updated:
        logger.info("Cancelled %d pending jobs for campaign %s", updated, campaign.id)
    return updated


def recreate_campaign_jobs(campaign):
    """Recreate jobs for pending recipients (for resume)."""
    return generate_campaign_jobs(campaign)


def _create_job_for_recipient(campaign, recipient, campaign_ct, due_at, step_order, step):
    """Create a single ScheduledJob for a campaign recipient."""
    from assistant.models import ScheduledJob

    idem_key = generate_idempotency_key(campaign.id, recipient.id, step_order)

    if ScheduledJob.objects.filter(idempotency_key=idem_key).exists():
        return None

    contact_ct = ContentType.objects.get_for_model(recipient.contact)

    # Determine channel and template
    if step:
        channel = step.channel
        subject = step.subject or campaign.subject or ""
        body_template = step.body_template
    else:
        channel = "whatsapp" if campaign.campaign_type == "whatsapp_broadcast" else "email"
        subject = campaign.subject or ""
        body_template = campaign.body_template

    job = ScheduledJob.objects.create(
        org=campaign.org,
        job_type="campaign_step",
        source_content_type=campaign_ct,
        source_object_id=campaign.id,
        target_content_type=contact_ct,
        target_object_id=recipient.contact_id,
        due_at=due_at,
        status="pending",
        payload={
            "campaign_id": str(campaign.id),
            "recipient_id": str(recipient.id),
            "step_order": step_order,
            "channel": channel,
            "subject": subject,
            "body_template": body_template,
            "module_key": "campaigns",
        },
        idempotency_key=idem_key,
        approval_required=False,
    )

    # Link recipient to job
    recipient.scheduled_job = job
    recipient.save(update_fields=["scheduled_job", "updated_at"])

    return job
