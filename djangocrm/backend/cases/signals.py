"""
Django signals para o módulo de Cases.

Signals:
- Case pre_save → auto-preencher closed_on e resolved_at quando stage_type="closed"
- Case pre_save → auto-preencher first_response_at na primeira interação de agente
"""

import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(pre_save, sender="cases.Case")
def auto_fill_close_fields(sender, instance, **kwargs):
    """
    Quando Case muda para CaseStage com stage_type="closed",
    preencher closed_on e resolved_at automaticamente.
    """
    if not instance.pk:
        return

    if not instance.stage:
        return

    stage_type = getattr(instance.stage, "stage_type", "")
    if stage_type != "closed":
        return

    # Verificar se mudou de stage
    try:
        old = sender.objects.get(pk=instance.pk)
        if old.stage_id == instance.stage_id:
            return
    except sender.DoesNotExist:
        return

    now = timezone.now()

    if not instance.closed_on:
        instance.closed_on = now.date()
        logger.info("Case %s: auto-set closed_on to %s", instance.id, instance.closed_on)

    if not instance.resolved_at:
        instance.resolved_at = now
        logger.info("Case %s: auto-set resolved_at to %s", instance.id, instance.resolved_at)
