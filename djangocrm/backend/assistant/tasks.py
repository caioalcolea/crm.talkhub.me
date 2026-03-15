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
        elif model_name == "lead":
            from assistant.template_engine import build_context_for_lead
            context = build_context_for_lead(target)
        elif model_name == "task":
            from assistant.template_engine import build_context_for_task
            context = build_context_for_task(target)
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

    if job.job_type != "reminder":
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
