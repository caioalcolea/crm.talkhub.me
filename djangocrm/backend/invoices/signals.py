"""
Invoice signals — auto-create Contas a Receber/Pagar in Financeiro,
process stock movements, and sync Payment↔Parcela.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from financeiro.exchange_rates import ExchangeRateError, get_exchange_rate
from invoices.models import Invoice, Payment

logger = logging.getLogger(__name__)

# Statuses that should trigger a Lancamento creation
_ACTIVE_STATUSES = {"Sent", "Viewed", "Paid", "Partially_Paid", "Overdue", "Pending"}


@receiver(post_save, sender=Invoice)
def create_lancamento_from_invoice(sender, instance, created, **kwargs):
    """
    When an Invoice is saved with an active (non-Draft, non-Cancelled) status,
    auto-create:
    1. Lancamento RECEBER (revenue) with product's plano de contas
    2. StockMovements for physical products (inventory deduction)
    3. Lancamento PAGAR (COGS) for cost of products sold
    """
    from financeiro.models import Lancamento
    from invoices.models import StockMovement

    if instance.status not in _ACTIVE_STATUSES:
        return

    # Skip if a RECEBER Lancamento already exists for this invoice
    if Lancamento.objects.filter(invoice=instance, tipo="RECEBER").exists():
        return

    due_date = instance.due_date or instance.issue_date
    if not due_date:
        logger.warning(
            "Invoice %s has no due_date or issue_date — skipping Lancamento creation",
            instance.pk,
        )
        return

    with transaction.atomic():
        # Determine plano de contas from first product line item
        plano_receita = None
        plano_custo = None
        line_items = instance.line_items.select_related("product").all()

        for item in line_items:
            if item.product:
                if not plano_receita and item.product.default_plano_receita_id:
                    plano_receita = item.product.default_plano_receita
                if not plano_custo and item.product.default_plano_custo_id:
                    plano_custo = item.product.default_plano_custo
                if plano_receita and plano_custo:
                    break

        # Resolve exchange rate for multi-currency invoices
        currency = instance.currency or "BRL"
        exchange_rate = Decimal("1")
        if currency != instance.org.default_currency:
            try:
                exchange_rate = get_exchange_rate(
                    currency, instance.org.default_currency, due_date,
                )
            except ExchangeRateError:
                logger.warning(
                    "Could not fetch exchange rate for Invoice %s (%s→%s)",
                    instance.pk, currency, instance.org.default_currency,
                )

        # 1. Create RECEBER Lancamento (revenue)
        lancamento_receber = Lancamento(
            org=instance.org,
            tipo="RECEBER",
            descricao=f"Fatura {instance.invoice_number or 'S/N'} — {instance.invoice_title or ''}",
            currency=currency,
            valor_total=instance.total_amount,
            exchange_rate_to_base=exchange_rate,
            data_primeiro_vencimento=due_date,
            numero_parcelas=1,
            invoice=instance,
            account=instance.account,
            contact=instance.contact,
            opportunity=instance.opportunity,
            plano_de_contas=plano_receita,
        )
        lancamento_receber.save()
        lancamento_receber.generate_parcelas()

        logger.info(
            "Auto-created Lancamento RECEBER id=%s for Invoice %s (total=%s %s)",
            lancamento_receber.pk,
            instance.invoice_number,
            instance.total_amount,
            instance.currency,
        )

        # 2. Process stock movements for physical products
        total_cogs = Decimal("0")
        for item in line_items:
            if not item.product:
                continue

            product = item.product

            # Calculate COGS for this line item
            item_cost = item.quantity * product.cost_price
            total_cogs += item_cost

            # Create stock movement for tracked inventory products
            if product.track_inventory and product.product_type == "product":
                StockMovement.objects.create(
                    product=product,
                    movement_type="out",
                    quantity=item.quantity,
                    unit_cost=product.cost_price,
                    reference_type="invoice",
                    reference_id=instance.pk,
                    notes=f"Fatura {instance.invoice_number} — {item.name or product.name}",
                    org=instance.org,
                )
                # Update stock quantity
                product.stock_quantity -= item.quantity
                product.save(update_fields=["stock_quantity"])

                logger.info(
                    "Stock deducted: %s x%s for Invoice %s (new stock: %s)",
                    product.name,
                    item.quantity,
                    instance.invoice_number,
                    product.stock_quantity,
                )

        # 3. Create PAGAR Lancamento (COGS) if there's cost
        if total_cogs > 0 and not Lancamento.objects.filter(
            invoice=instance, tipo="PAGAR"
        ).exists():
            lancamento_cogs = Lancamento(
                org=instance.org,
                tipo="PAGAR",
                descricao=f"CMV — Fatura {instance.invoice_number}",
                currency=currency,
                valor_total=total_cogs,
                exchange_rate_to_base=exchange_rate,
                data_primeiro_vencimento=due_date,
                numero_parcelas=1,
                invoice=instance,
                account=instance.account,
                plano_de_contas=plano_custo,
            )
            lancamento_cogs.save()
            lancamento_cogs.generate_parcelas()

            logger.info(
                "Auto-created Lancamento PAGAR (COGS) id=%s for Invoice %s (cost=%s)",
                lancamento_cogs.pk,
                instance.invoice_number,
                total_cogs,
            )


@receiver(post_save, sender=Payment)
def sync_payment_to_parcela(sender, instance, created, **kwargs):
    """
    When a Payment is created on an Invoice, find the linked Lancamento RECEBER
    and mark the corresponding Parcela(s) as PAGO.
    """
    if not created:
        return

    from financeiro.models import Lancamento

    invoice = instance.invoice
    if not invoice:
        return

    lancamento = Lancamento.objects.filter(
        invoice=invoice, tipo="RECEBER"
    ).first()

    if not lancamento:
        return

    from django.utils import timezone

    with transaction.atomic():
        # Lock unpaid parcelas to prevent concurrent payment race conditions
        parcelas = list(
            lancamento.parcelas.filter(status="ABERTO")
            .order_by("data_vencimento")
            .select_for_update()
        )
        remaining = instance.amount

        for parcela in parcelas:
            if remaining <= 0:
                break

            if remaining >= parcela.valor_parcela:
                parcela.status = "PAGO"
                parcela.data_pagamento = instance.payment_date or timezone.now().date()
                parcela.save(update_fields=["status", "data_pagamento"])
                remaining -= parcela.valor_parcela
            # Partial payment: leave as ABERTO (the parcela has a fixed value)

        # Recalculate lancamento status atomically
        lancamento.update_status()

    logger.info(
        "Synced Payment to Parcela: Invoice %s, Lancamento %s",
        invoice.invoice_number,
        lancamento.pk,
    )
