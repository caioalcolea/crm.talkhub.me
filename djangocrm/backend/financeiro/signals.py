"""
Financeiro signals — sync Parcela payment status back to Invoice.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from financeiro.models import Parcela

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Parcela)
def sync_parcela_to_invoice(sender, instance, **kwargs):
    """
    When a Parcela is marked as PAGO, check if its parent Lancamento
    is linked to an Invoice and update the Invoice status accordingly.
    """
    lancamento = instance.lancamento

    # Only care about RECEBER lancamentos linked to invoices
    if not lancamento.invoice_id or lancamento.tipo != "RECEBER":
        return

    invoice = lancamento.invoice

    # Check all parcelas of this lancamento
    all_parcelas = lancamento.parcelas.all()
    total_count = all_parcelas.count()
    paid_count = all_parcelas.filter(status="PAGO").count()

    # Determine new invoice status
    if paid_count == total_count and total_count > 0:
        new_status = "Paid"
    elif paid_count > 0:
        new_status = "Partially_Paid"
    else:
        return  # No change needed

    # Only update if status actually changed and invoice is in an active state
    if invoice.status in ("Sent", "Viewed", "Overdue", "Pending", "Partially_Paid"):
        if invoice.status != new_status:
            update_fields = ["status"]
            invoice.status = new_status

            if new_status == "Paid" and not invoice.paid_at:
                invoice.paid_at = timezone.now()
                update_fields.append("paid_at")

            # Calculate amount_paid from parcela payments
            from decimal import Decimal
            total_paid = sum(
                p.valor_parcela for p in all_parcelas if p.status == "PAGO"
            )
            invoice.amount_paid = total_paid
            invoice.amount_due = invoice.total_amount - total_paid
            update_fields.extend(["amount_paid", "amount_due"])

            invoice.save(update_fields=update_fields)

            logger.info(
                "Synced Parcela payment to Invoice %s: status=%s (%d/%d parcelas paid)",
                invoice.invoice_number,
                new_status,
                paid_count,
                total_count,
            )
