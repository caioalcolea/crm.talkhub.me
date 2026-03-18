"""
Scheduler engine — generates and recalculates ScheduledJobs from ReminderPolicies.

Responsible for:
- Calculating next_run_at for a policy based on trigger_type
- Generating ScheduledJob records for pending executions
- Cancelling stale jobs when a policy is deactivated or target changes
"""

import hashlib
import logging
from datetime import date, datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

logger = logging.getLogger(__name__)


def calculate_next_run(policy):
    """
    Calculate the next execution datetime for a ReminderPolicy.

    Args:
        policy: ReminderPolicy instance

    Returns:
        datetime or None if no more runs are scheduled
    """
    trigger_type = policy.trigger_type
    config = policy.trigger_config or {}

    if trigger_type == "due_date":
        return _evaluate_due_date_trigger(policy, config)
    elif trigger_type == "recurring":
        return _evaluate_recurring_trigger(policy, config)
    elif trigger_type == "cron":
        return _evaluate_cron_trigger(policy, config)
    elif trigger_type == "event_plus_offset":
        # Event-based triggers are calculated on event, not scheduled
        return None
    elif trigger_type == "relative_date":
        return _evaluate_relative_date_trigger(policy, config)

    logger.warning("Unknown trigger_type %s for policy %s", trigger_type, policy.id)
    return None


def _evaluate_due_date_trigger(policy, config):
    """
    For trigger_type=due_date: find the target's date field and apply offsets.

    config example: {"date_field": "data_vencimento", "offset_days": -3}
    or with multiple offsets: {"date_field": "data_vencimento", "offsets": [-7, -3, 0, 1, 3]}
    """
    date_field = config.get("date_field", "data_vencimento")
    target = _resolve_target(policy)
    if not target:
        return None

    target_date = getattr(target, date_field, None)
    if not target_date:
        return None

    # Convert date to datetime if needed
    if isinstance(target_date, date) and not isinstance(target_date, datetime):
        import pytz
        from datetime import time as time_type
        tz = pytz.timezone(policy.timezone)
        # Use target's due_time if available, else config time_of_day_hour, else 9 AM
        target_time = getattr(target, 'due_time', None)
        if not target_time:
            hour = config.get('time_of_day_hour') or 9
            target_time = time_type(hour=hour)
        target_date = tz.localize(datetime.combine(target_date, target_time))

    now = timezone.now()

    # Single offset
    if "offset_days" in config:
        run_at = target_date + timedelta(days=config["offset_days"])
        return run_at if run_at > now else None

    # Multiple offsets — find next upcoming one
    offsets = config.get("offsets", [0])
    upcoming = []
    for offset in sorted(offsets):
        run_at = target_date + timedelta(days=offset)
        if run_at > now:
            upcoming.append(run_at)

    return upcoming[0] if upcoming else None


def _evaluate_recurring_trigger(policy, config):
    """
    For trigger_type=recurring: calculate next run based on interval.

    config example: {"interval_days": 3, "max_runs": 10, "start_after": "data_vencimento"}
    """
    interval_days = config.get("interval_days", 1)
    max_runs = config.get("max_runs")

    if max_runs and policy.run_count >= max_runs:
        return None

    if policy.last_run_at:
        return policy.last_run_at + timedelta(days=interval_days)

    # First run: use start_after field from target if specified
    start_after_field = config.get("start_after")
    if start_after_field:
        target = _resolve_target(policy)
        if target:
            start_date = getattr(target, start_after_field, None)
            if start_date:
                if isinstance(start_date, date) and not isinstance(start_date, datetime):
                    import pytz
                    tz = pytz.timezone(policy.timezone)
                    start_date = tz.localize(
                        datetime.combine(start_date, datetime.min.replace(hour=9).time())
                    )
                return start_date

    return timezone.now()


def _evaluate_cron_trigger(policy, config):
    """
    For trigger_type=cron: calculate next run from cron expression.

    config example: {"cron_expression": "0 9 * * 1-5"}
    """
    cron_expr = config.get("cron_expression")
    if not cron_expr:
        return None

    try:
        from croniter import croniter
        now = timezone.now()
        cron = croniter(cron_expr, now)
        return cron.get_next(datetime)
    except (ImportError, ValueError) as e:
        logger.error("Cron evaluation failed for policy %s: %s", policy.id, e)
        return None


def _evaluate_relative_date_trigger(policy, config):
    """
    For trigger_type=relative_date: offset from a field on target.

    config example: {"date_field": "created_at", "offset_days": 7}
    """
    date_field = config.get("date_field")
    offset_days = config.get("offset_days", 0)

    if not date_field:
        return None

    target = _resolve_target(policy)
    if not target:
        return None

    target_date = getattr(target, date_field, None)
    if not target_date:
        return None

    if isinstance(target_date, date) and not isinstance(target_date, datetime):
        import pytz
        tz = pytz.timezone(policy.timezone)
        target_date = tz.localize(datetime.combine(target_date, datetime.min.replace(hour=9).time()))

    run_at = target_date + timedelta(days=offset_days)
    now = timezone.now()
    return run_at if run_at > now else None


def _resolve_target(policy):
    """Resolve the GenericForeignKey target of a policy."""
    try:
        ct = policy.target_content_type
        model_class = ct.model_class()
        if model_class is None:
            return None
        return model_class.objects.filter(pk=policy.target_object_id).first()
    except Exception as e:
        logger.error("Failed to resolve target for policy %s: %s", policy.id, e)
        return None


def generate_idempotency_key(policy_id, due_at, suffix=""):
    """Generate a deterministic idempotency key for a job."""
    raw = f"policy-{policy_id}-{due_at.isoformat()}"
    if suffix:
        raw += f"-{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def generate_jobs_for_policy(policy):
    """
    Generate pending ScheduledJobs for an active ReminderPolicy.

    Returns list of created ScheduledJob instances.
    """
    from assistant.models import ScheduledJob

    if not policy.is_active:
        return []

    next_run = calculate_next_run(policy)
    if not next_run:
        return []

    # Update policy's next_run_at
    policy.next_run_at = next_run
    policy.save(update_fields=["next_run_at", "updated_at"])

    # Generate idempotency key
    idem_key = generate_idempotency_key(policy.id, next_run)

    # Check if job already exists
    if ScheduledJob.objects.filter(idempotency_key=idem_key).exists():
        return []

    source_ct = ContentType.objects.get_for_model(policy)

    job = ScheduledJob.objects.create(
        org=policy.org,
        job_type="reminder",
        source_content_type=source_ct,
        source_object_id=policy.id,
        target_content_type=policy.target_content_type,
        target_object_id=policy.target_object_id,
        assigned_user=policy.owner_user,
        due_at=next_run,
        status="pending",
        payload={
            "policy_id": str(policy.id),
            "module_key": policy.module_key,
            "channel_config": policy.channel_config,
            "task_config": policy.task_config,
            "message_template": policy.message_template,
        },
        idempotency_key=idem_key,
        approval_required=(policy.approval_policy == "manual"),
    )

    logger.info(
        "Generated job %s for policy %s, due at %s",
        job.id, policy.id, next_run,
    )
    return [job]


def cancel_stale_jobs(policy):
    """Cancel all pending jobs for a policy (e.g., when deactivated or target changed)."""
    from assistant.models import ScheduledJob

    source_ct = ContentType.objects.get_for_model(policy)
    updated = ScheduledJob.objects.filter(
        source_content_type=source_ct,
        source_object_id=policy.id,
        status="pending",
    ).update(status="cancelled")

    if updated:
        logger.info("Cancelled %d stale jobs for policy %s", updated, policy.id)
    return updated
