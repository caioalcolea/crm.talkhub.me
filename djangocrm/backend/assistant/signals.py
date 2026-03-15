"""
Signals for the assistant app.

Listens to model changes that should trigger job recalculation
(e.g., Parcela date changes, policy activation/deactivation).
"""

import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="financeiro.Parcela")
def parcela_changed_recalculate_reminders(sender, instance, **kwargs):
    """
    When data_vencimento or status changes on a Parcela, recalculate
    associated reminder jobs for the parent Lancamento.
    """
    from assistant.models import ReminderPolicy
    from assistant.tasks import recalculate_policy_schedules

    try:
        lancamento = instance.lancamento
        ct = ContentType.objects.get_for_model(lancamento)
        policy_ids = list(
            ReminderPolicy.objects.filter(
                target_content_type=ct,
                target_object_id=lancamento.id,
                is_active=True,
            ).values_list("id", flat=True)
        )

        for policy_id in policy_ids:
            recalculate_policy_schedules.delay(str(policy_id))

        if policy_ids:
            logger.info(
                "Triggered recalculation for %d policies after Parcela %s change",
                len(policy_ids), instance.id,
            )
    except Exception as e:
        logger.error("Error recalculating reminders for parcela %s: %s", instance.id, e)


@receiver(post_save, sender="assistant.ReminderPolicy")
def policy_saved_generate_jobs(sender, instance, created, **kwargs):
    """
    When a ReminderPolicy is created or reactivated, generate initial jobs.
    When deactivated, cancel pending jobs.
    """
    from assistant.engine import cancel_stale_jobs, generate_jobs_for_policy

    if not instance.is_active:
        cancel_stale_jobs(instance)
        return

    if created:
        generate_jobs_for_policy(instance)
