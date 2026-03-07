"""
Signals do app automations — integração com LogicRules.

Conecta post_save/pre_save nos models Lead, Opportunity, Case, Task e Contact
para disparar avaliação de LogicRules ativas.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _safe_process_event(event_name, instance, extra_data=None):
    """Wrapper seguro para process_event — nunca bloqueia o save."""
    try:
        org_id = getattr(instance, "org_id", None)
        if not org_id:
            return
        from automations.engine import process_event

        process_event(event_name, instance, org_id, extra_data=extra_data)
    except Exception:
        logger.exception("Error processing automation event %s", event_name)


# --- Lead signals ---

@receiver(pre_save, sender="leads.Lead")
def lead_pre_save_track_status(sender, instance, **kwargs):
    """Rastrear mudança de status do Lead para disparar lead.status_changed."""
    if not instance.pk:
        instance._automation_prev_status = None
        return
    try:
        from leads.models import Lead
        old = Lead.objects.get(pk=instance.pk)
        instance._automation_prev_status = old.status
    except sender.DoesNotExist:
        instance._automation_prev_status = None


@receiver(post_save, sender="leads.Lead")
def lead_post_save_automation(sender, instance, created, **kwargs):
    """Disparar eventos lead.created e lead.status_changed."""
    if created:
        _safe_process_event("lead.created", instance)
    else:
        prev_status = getattr(instance, "_automation_prev_status", None)
        current_status = getattr(instance, "status", None)
        if prev_status and current_status and prev_status != current_status:
            _safe_process_event(
                "lead.status_changed",
                instance,
                extra_data={"previous_status": prev_status},
            )


# --- Opportunity signals ---

@receiver(pre_save, sender="opportunity.Opportunity")
def opportunity_pre_save_track_stage(sender, instance, **kwargs):
    """Rastrear mudança de stage da Opportunity."""
    if not instance.pk:
        instance._automation_prev_stage = None
        return
    try:
        from opportunity.models import Opportunity
        old = Opportunity.objects.get(pk=instance.pk)
        instance._automation_prev_stage = old.stage
    except sender.DoesNotExist:
        instance._automation_prev_stage = None


@receiver(post_save, sender="opportunity.Opportunity")
def opportunity_post_save_automation(sender, instance, created, **kwargs):
    """Disparar eventos opportunity.created e opportunity.stage_changed."""
    if created:
        _safe_process_event("opportunity.created", instance)
    else:
        prev_stage = getattr(instance, "_automation_prev_stage", None)
        current_stage = getattr(instance, "stage", None)
        if prev_stage and current_stage and prev_stage != current_stage:
            _safe_process_event(
                "opportunity.stage_changed",
                instance,
                extra_data={"previous_stage": prev_stage},
            )


# --- Case signals ---

@receiver(post_save, sender="cases.Case")
def case_post_save_automation(sender, instance, created, **kwargs):
    """Disparar evento case.created."""
    if created:
        _safe_process_event("case.created", instance)


# --- Task signals ---

@receiver(post_save, sender="tasks.Task")
def task_post_save_automation(sender, instance, created, **kwargs):
    """Disparar evento task.completed quando status muda para Completed."""
    if not created:
        status = getattr(instance, "status", "")
        if status and status.lower() in ("completed", "done"):
            _safe_process_event("task.completed", instance)


# --- Contact signals ---

@receiver(post_save, sender="contacts.Contact")
def contact_post_save_automation(sender, instance, created, **kwargs):
    """Disparar evento contact.created."""
    if created:
        _safe_process_event("contact.created", instance)
