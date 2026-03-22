"""
Django signals para o módulo de Leads.

Signals:
- Lead pre_save → auto-criar Opportunity quando lead atinge stage "won"
  e pipeline tem auto_create_opportunity=True.
"""

import logging
from datetime import date

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
    from opportunity.models import Opportunity, OpportunityPipeline

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

        # Determine target opportunity pipeline & stage
        target_pipeline_stage = None
        target_legacy_stage = "PROSPECTING"

        if getattr(pipeline, "target_opp_stage_id", None):
            target_pipeline_stage = pipeline.target_opp_stage
            target_legacy_stage = (
                getattr(target_pipeline_stage, "maps_to_stage", "") or "PROSPECTING"
            )
        elif getattr(pipeline, "target_opp_pipeline_id", None):
            first_stage = pipeline.target_opp_pipeline.stages.order_by("order").first()
            if first_stage:
                target_pipeline_stage = first_stage
                target_legacy_stage = (
                    getattr(first_stage, "maps_to_stage", "") or "PROSPECTING"
                )

        # Fallback: use first active opportunity pipeline & its first stage
        if target_pipeline_stage is None:
            first_opp_pipeline = OpportunityPipeline.objects.filter(
                org=lead.org, is_active=True
            ).order_by("-is_default", "created_at").first()
            if first_opp_pipeline:
                first_stage = first_opp_pipeline.stages.order_by("order").first()
                if first_stage:
                    target_pipeline_stage = first_stage
                    target_legacy_stage = (
                        getattr(first_stage, "maps_to_stage", "") or "PROSPECTING"
                    )

        # Who moved the card (set by LeadMoveView)
        moved_by = getattr(lead, "_moved_by_profile", None)

        opp = Opportunity.objects.create(
            org=lead.org,
            name=opp_name,
            lead=lead,
            stage=target_legacy_stage,
            pipeline_stage=target_pipeline_stage,
            probability=lead.probability or 50,
            amount=lead.opportunity_amount or 0,
            closed_on=date.today(),
            description=f"Auto-created from lead: {lead.title}",
            created_by=moved_by.user if moved_by else lead.created_by,
        )
        # Copiar contacts do lead
        opp.contacts.set(contacts)
        # Copiar assigned_to do lead + quem moveu o card
        if lead.assigned_to.exists():
            opp.assigned_to.set(lead.assigned_to.all())
        if moved_by:
            opp.assigned_to.add(moved_by)
        # Copiar account se existir
        if hasattr(lead, "account") and lead.account:
            opp.account = lead.account
            opp.save(update_fields=["account"])

        logger.info(
            "Auto-created Opportunity %s from Lead %s (pipeline=%s, stage=%s, moved_by=%s)",
            opp.id, lead.id, pipeline.name,
            target_pipeline_stage.name if target_pipeline_stage else "none",
            moved_by or "signal",
        )
    except Exception as exc:
        logger.error("Failed to auto-create opportunity from lead %s: %s", lead.id, exc)
