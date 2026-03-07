"""
Django signals para o módulo de Leads.

Signals:
- Lead pre_save → auto-criar Opportunity quando lead atinge stage "won"
  e pipeline tem auto_create_opportunity=True.
"""

import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender="leads.Lead")
def auto_create_opportunity(sender, instance, **kwargs):
    """
    Quando um Lead muda para um stage do tipo "won" e o pipeline
    tem auto_create_opportunity=True, criar Opportunity automaticamente.
    Deduplicação: verifica se já existe Opportunity para mesmo Contact + Pipeline.
    """
    if not instance.pk:
        return

    # Lead → stage (FK) → pipeline (FK) — Lead não tem campo pipeline direto
    if not instance.stage or not instance.stage.pipeline:
        return

    if not getattr(instance.stage.pipeline, "auto_create_opportunity", False):
        return

    if getattr(instance.stage, "stage_type", "") != "won":
        return

    # Verificar se mudou de stage (evitar duplicatas)
    try:
        from leads.models import Lead
        old = Lead.objects.get(pk=instance.pk)
        if old.stage_id == instance.stage_id:
            return
    except sender.DoesNotExist:
        return

    # Criar opportunity após save (precisa dos M2M)
    from django.db.models.signals import post_save

    def _create_opportunity_after_save(sender, instance, **kw):
        post_save.disconnect(_create_opportunity_after_save, sender=sender)
        _do_create_opportunity(instance)

    post_save.connect(_create_opportunity_after_save, sender=sender, weak=False)


def _do_create_opportunity(lead):
    """Create Opportunity from Lead with Contact+Pipeline deduplication."""
    from opportunity.models import Opportunity

    contacts = lead.contacts.all()
    if not contacts.exists():
        logger.info(
            "Lead %s won but has no contacts — skipping auto-opportunity", lead.id
        )
        return

    pipeline = lead.stage.pipeline if lead.stage else None
    if not pipeline:
        logger.info(
            "Lead %s won but has no pipeline — skipping auto-opportunity", lead.id
        )
        return

    # Deduplicação por Contact + Pipeline
    for contact in contacts:
        existing = Opportunity.objects.filter(
            org=lead.org,
            contacts=contact,
        ).filter(
            lead__stage__pipeline=pipeline,
        ).exists()
        if existing:
            logger.info(
                "Opportunity already exists for contact %s in pipeline %s — skipping",
                contact.id, pipeline.name,
            )
            return

    # Criar Opportunity
    try:
        first_contact = contacts.first()
        opp_name = f"{first_contact.first_name} - {pipeline.name}"

        opp = Opportunity.objects.create(
            org=lead.org,
            name=opp_name,
            lead=lead,
            stage="PROSPECTING",
            probability=lead.probability or 50,
            amount=lead.opportunity_amount or 0,
            description=f"Auto-created from lead: {lead.title}",
            created_by=lead.created_by,
        )
        # Copiar contacts do lead
        opp.contacts.set(contacts)
        # Copiar assigned_to do lead
        if lead.assigned_to.exists():
            opp.assigned_to.set(lead.assigned_to.all())
        # Copiar account se existir
        if hasattr(lead, "account") and lead.account:
            opp.account = lead.account
            opp.save(update_fields=["account"])

        logger.info(
            "Auto-created Opportunity %s from Lead %s (pipeline=%s)",
            opp.id, lead.id, pipeline.name,
        )
    except Exception as exc:
        logger.error("Failed to auto-create opportunity from lead %s: %s", lead.id, exc)
