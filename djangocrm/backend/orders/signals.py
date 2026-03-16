"""
Order signals — auto-create Lancamento PAGAR and stock entries
when a Purchase Order is activated.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from orders.models import Order

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def process_order_activation(sender, instance, **kwargs):
    """
    When a Purchase Order is activated:
    1. Create Lancamento PAGAR (accounts payable)
    2. Create StockMovements for physical products (inventory increase)
    3. Update product stock quantities
    """
    # Only process when status is ACTIVATED
    if instance.status != "ACTIVATED":
        return

    # Only process purchase orders
    if instance.order_type != "purchase":
        return

    from financeiro.models import Lancamento
    from invoices.models import StockMovement

    # Skip if already processed (Lancamento exists)
    if Lancamento.objects.filter(
        org=instance.org,
        descricao__startswith=f"Compra {instance.order_number or instance.name}",
        tipo="PAGAR",
    ).exists():
        return

    due_date = instance.order_date
    if not due_date:
        import datetime
        due_date = datetime.date.today()

    with transaction.atomic():
        line_items = instance.line_items.select_related("product").all()

        # Determine plano de contas from first product
        plano_custo = None
        for item in line_items:
            if item.product and item.product.default_plano_custo_id:
                plano_custo = item.product.default_plano_custo
                break

        # 1. Create Lancamento PAGAR
        if instance.total_amount > 0:
            lancamento = Lancamento(
                org=instance.org,
                tipo="PAGAR",
                descricao=f"Compra {instance.order_number or instance.name}",
                currency=instance.currency or "BRL",
                valor_total=instance.total_amount,
                data_primeiro_vencimento=due_date,
                numero_parcelas=1,
                account=instance.account,
                contact=instance.contact,
                plano_de_contas=plano_custo,
            )
            lancamento.save()
            lancamento.generate_parcelas()

            logger.info(
                "Auto-created Lancamento PAGAR id=%s for Purchase Order %s (total=%s)",
                lancamento.pk,
                instance.name,
                instance.total_amount,
            )

        # 2. Process stock movements for physical products
        for item in line_items:
            if not item.product:
                continue

            product = item.product
            if product.track_inventory and product.product_type == "product":
                StockMovement.objects.create(
                    product=product,
                    movement_type="in",
                    quantity=item.quantity,
                    unit_cost=item.unit_price,
                    reference_type="purchase",
                    reference_id=instance.pk,
                    notes=f"Pedido de compra {instance.order_number or instance.name}",
                    org=instance.org,
                )

                # Update stock quantity
                product.stock_quantity += item.quantity
                # Update cost price with weighted average
                if product.stock_quantity > 0:
                    old_total = (product.stock_quantity - item.quantity) * product.cost_price
                    new_total = item.quantity * item.unit_price
                    product.cost_price = (
                        (old_total + new_total) / product.stock_quantity
                    ).quantize(Decimal("0.01"))

                product.save(update_fields=["stock_quantity", "cost_price"])

                logger.info(
                    "Stock added: %s +%s for Purchase Order %s (new stock: %s, new cost: %s)",
                    product.name,
                    item.quantity,
                    instance.name,
                    product.stock_quantity,
                    product.cost_price,
                )
