"""
Opportunity signals — auto-create Conta a Receber in Financeiro
when an Opportunity is moved to CLOSED_WON stage.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from opportunity.models import Opportunity

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Opportunity)
def create_lancamento_on_closed_won(sender, instance, **kwargs):
    """
    When an Opportunity reaches CLOSED_WON (via legacy stage field or
    pipeline_stage.maps_to_stage), auto-create a Lancamento RECEBER if one
    doesn't already exist for this opportunity.
    """
    from financeiro.models import Lancamento

    # Determine if opportunity is in "CLOSED_WON" state
    is_won = False

    # Check pipeline stage mapping first (new kanban system)
    if instance.pipeline_stage_id:
        try:
            if instance.pipeline_stage.maps_to_stage == "CLOSED_WON":
                is_won = True
        except Exception:
            pass

    # Fall back to legacy stage field
    if not is_won and instance.stage == "CLOSED_WON":
        is_won = True

    if not is_won:
        return

    # Skip if amount is missing or zero
    if not instance.amount:
        logger.info(
            "Opportunity %s is CLOSED_WON but has no amount — skipping Lancamento",
            instance.pk,
        )
        return

    # Skip if a Lancamento already exists for this opportunity
    if Lancamento.objects.filter(opportunity=instance, tipo="RECEBER").exists():
        return

    due_date = instance.closed_on
    if not due_date:
        from django.utils import timezone
        due_date = timezone.now().date()

    with transaction.atomic():
        contact = instance.contacts.first()

        currency = instance.currency or "BRL"
        exchange_rate = Decimal("1")
        if currency != instance.org.default_currency:
            from financeiro.exchange_rates import ExchangeRateError, get_exchange_rate
            try:
                exchange_rate = get_exchange_rate(
                    currency, instance.org.default_currency, due_date,
                )
            except ExchangeRateError:
                logger.warning(
                    "Could not fetch exchange rate for Opportunity %s (%s→%s)",
                    instance.pk, currency, instance.org.default_currency,
                )

        lancamento = Lancamento(
            org=instance.org,
            tipo="RECEBER",
            descricao=f"Oportunidade ganha: {instance.name}",
            currency=currency,
            valor_total=instance.amount,
            exchange_rate_to_base=exchange_rate,
            data_primeiro_vencimento=due_date,
            numero_parcelas=1,
            opportunity=instance,
            account=instance.account,
            contact=contact,
        )
        lancamento.save()
        lancamento.generate_parcelas()

        logger.info(
            "Auto-created Lancamento RECEBER id=%s for Opportunity %s (amount=%s %s)",
            lancamento.pk,
            instance.name,
            instance.amount,
            instance.currency,
        )
