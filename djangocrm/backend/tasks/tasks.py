"""Celery tasks for the Tasks module."""

import logging
from datetime import date

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="auto_escalate_overdue_tasks")
def auto_escalate_overdue_tasks():
    """
    Run hourly via Beat. Escalates priority of overdue tasks to High.
    Only affects tasks with Low or Medium priority that are past due_date
    and not yet Completed.
    """
    from common.models import Org
    from common.tasks import set_rls_context
    from tasks.models import Task

    today = date.today()
    total_escalated = 0

    for org_id in Org.objects.values_list("id", flat=True):
        set_rls_context(org_id)
        updated = Task.objects.filter(
            org_id=org_id,
            due_date__lt=today,
            status__in=["New", "In Progress"],
            priority__in=["Low", "Medium"],
        ).update(priority="High")
        total_escalated += updated

    if total_escalated:
        logger.info("Auto-escalated %d overdue tasks to High priority", total_escalated)

    return total_escalated
