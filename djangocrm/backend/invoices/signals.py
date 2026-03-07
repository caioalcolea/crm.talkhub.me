"""
Invoice signals — auto-create Contas a Receber in Financeiro
when an Invoice transitions out of Draft status.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from invoices.models import Invoice

logger = logging.getLogger(__name__)

# Statuses that should trigger a Lancamento creation
_ACTIVE_STATUSES = {"Sent", "Viewed", "Paid", "Partially_Paid", "Overdue", "Pending"}


@receiver(post_save, sender=Invoice)
def create_lancamento_from_invoice(sender, instance, created, **kwargs):
    """
    When an Invoice is saved with an active (non-Draft, non-Cancelled) status,
    auto-create a Lancamento (Conta a Receber) in the Financeiro module
    if one doesn't already exist for this invoice.
    """
    from financeiro.models import Lancamento

    if instance.status not in _ACTIVE_STATUSES:
        return

    # Skip if a Lancamento already exists for this invoice
    if Lancamento.objects.filter(invoice=instance).exists():
        return

    due_date = instance.due_date or instance.issue_date
    if not due_date:
        logger.warning(
            "Invoice %s has no due_date or issue_date — skipping Lancamento creation",
            instance.pk,
        )
        return

    lancamento = Lancamento(
        org=instance.org,
        tipo="RECEBER",
        descricao=f"Fatura {instance.invoice_number} — {instance.invoice_title}",
        currency=instance.currency or "BRL",
        valor_total=instance.total_amount,
        data_primeiro_vencimento=due_date,
        numero_parcelas=1,
        invoice=instance,
        account=instance.account,
        contact=instance.contact,
        opportunity=instance.opportunity,
    )
    lancamento.save()
    lancamento.generate_parcelas()

    logger.info(
        "Auto-created Lancamento (RECEBER) id=%s for Invoice %s (total=%s %s)",
        lancamento.pk,
        instance.invoice_number,
        instance.total_amount,
        instance.currency,
    )
