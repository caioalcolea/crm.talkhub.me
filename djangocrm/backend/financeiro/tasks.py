import datetime
import logging

from celery import shared_task

from common.tasks import set_rls_context

logger = logging.getLogger(__name__)


@shared_task(name="financeiro.tasks.check_overdue_parcelas")
def check_overdue_parcelas():
    """
    Daily task: logs overdue parcelas count per org.
    Iterates over all active orgs and sets RLS context per org,
    since financeiro_parcela is RLS-protected.
    """
    from common.models import Org
    from financeiro.models import Parcela

    today = datetime.date.today()
    total_overdue = 0

    for org in Org.objects.filter(is_active=True):
        set_rls_context(str(org.id))
        overdue_count = Parcela.objects.filter(
            status="ABERTO", data_vencimento__lt=today
        ).count()

        if overdue_count > 0:
            logger.info(
                "Financeiro [%s]: %d parcelas vencidas.", org.name, overdue_count
            )
            total_overdue += overdue_count

    if total_overdue > 0:
        logger.info("Financeiro: %d parcelas vencidas no total.", total_overdue)

    return {"overdue_count": total_overdue, "checked_at": str(today)}


@shared_task(name="financeiro.tasks.process_pix_confirmation")
def process_pix_confirmation(transaction_id, org_id):
    """
    Post-confirmation task: when a PIX PaymentTransaction is confirmed,
    create Payment on linked invoice and/or update linked Parcela.

    Called asynchronously after webhook confirms a transaction.
    """
    set_rls_context(org_id)

    from financeiro.models import PaymentTransaction

    transaction = PaymentTransaction.objects.filter(
        id=transaction_id, org_id=org_id
    ).select_related("invoice", "lancamento").first()

    if not transaction or transaction.status != "confirmed":
        logger.warning(
            "PIX confirmation task: transaction %s not found or not confirmed",
            transaction_id,
        )
        return

    # 1. If linked to an invoice, create a Payment record
    if transaction.invoice:
        _create_invoice_payment(transaction)

    # 2. If linked to a lancamento, update the first open Parcela
    if transaction.lancamento:
        _update_lancamento_parcela(transaction)


def _create_invoice_payment(transaction):
    """Create a Payment record on the linked invoice."""
    from invoices.models import Payment

    # Check if payment already exists for this transaction (idempotency)
    existing = Payment.objects.filter(
        invoice=transaction.invoice,
        reference_number=f"PIX:{transaction.pix_txid}",
    ).exists()
    if existing:
        logger.info(
            "Payment already exists for PIX txid %s on invoice %s",
            transaction.pix_txid,
            transaction.invoice_id,
        )
        return

    Payment.objects.create(
        invoice=transaction.invoice,
        amount=transaction.amount,
        payment_date=transaction.paid_at.date() if transaction.paid_at else datetime.date.today(),
        payment_method="PIX",
        reference_number=f"PIX:{transaction.pix_txid}",
        notes=f"Pagamento PIX confirmado automaticamente. E2E: {transaction.pix_e2e_id or 'N/A'}",
        org=transaction.org,
    )
    logger.info(
        "Created Payment for invoice %s from PIX %s",
        transaction.invoice_id,
        transaction.pix_txid,
    )


def _update_lancamento_parcela(transaction):
    """Update the first open Parcela of the linked Lancamento to PAGO."""
    lancamento = transaction.lancamento
    parcela = lancamento.parcelas.filter(status="ABERTO").order_by("numero").first()

    if not parcela:
        logger.info(
            "No open parcela found for lancamento %s (PIX %s)",
            lancamento.id,
            transaction.pix_txid,
        )
        return

    parcela.data_pagamento = (
        transaction.paid_at.date() if transaction.paid_at else datetime.date.today()
    )
    parcela.observacoes = (
        f"{parcela.observacoes}\nPIX confirmado: {transaction.pix_txid}".strip()
    )
    parcela.save()

    # Update parent lancamento status
    lancamento.update_status()

    logger.info(
        "Updated parcela %s/%s for lancamento %s from PIX %s",
        parcela.numero,
        lancamento.numero_parcelas,
        lancamento.id,
        transaction.pix_txid,
    )


@shared_task(name="financeiro.tasks.generate_recurring_parcelas")
def generate_recurring_parcelas():
    """
    Periodic: generate next parcelas for active recurring lancamentos.
    Generates up to 12 months ahead so users always see upcoming installments.
    Runs on the 1st and 15th of each month.
    """
    from common.models import Org
    from financeiro.models import Lancamento

    total_generated = 0

    for org in Org.objects.filter(is_active=True):
        set_rls_context(str(org.id))

        lancamentos = Lancamento.objects.filter(
            is_recorrente=True,
            recorrencia_ativa=True,
            status="ABERTO",
        )

        for lanc in lancamentos:
            # Check data_fim_recorrencia
            if lanc.data_fim_recorrencia and lanc.data_fim_recorrencia < datetime.date.today():
                lanc.recorrencia_ativa = False
                lanc.save(update_fields=["recorrencia_ativa", "updated_at"])
                continue

            before = lanc.parcelas.count()
            lanc.generate_recurring_parcelas(months_ahead=12)
            after = lanc.parcelas.count()
            generated = after - before
            if generated > 0:
                total_generated += generated
                logger.info(
                    "Recorrente [%s]: %d novas parcelas para '%s'",
                    org.name, generated, lanc.descricao,
                )

    return {"generated": total_generated, "date": str(datetime.date.today())}


@shared_task(name="financeiro.tasks.update_variable_exchange_rates")
def update_variable_exchange_rates():
    """
    Daily: update exchange rates for pending parcelas of VARIAVEL lancamentos
    whose due date has arrived.
    """
    from decimal import Decimal, ROUND_HALF_UP

    from common.models import Org
    from financeiro.exchange_rates import ExchangeRateError, get_exchange_rate
    from financeiro.models import Lancamento, Parcela

    today = datetime.date.today()
    total_updated = 0

    for org in Org.objects.filter(is_active=True):
        set_rls_context(str(org.id))

        # Find VARIAVEL lancamentos with open parcelas due today or earlier
        lancamentos = Lancamento.objects.filter(
            exchange_rate_type="VARIAVEL",
            status="ABERTO",
        ).exclude(currency=org.default_currency)

        for lanc in lancamentos:
            parcelas = lanc.parcelas.filter(
                status="ABERTO",
                data_vencimento__lte=today,
            )

            for parcela in parcelas:
                try:
                    rate = get_exchange_rate(
                        lanc.currency, org.default_currency, parcela.data_vencimento
                    )
                    if rate != parcela.exchange_rate_to_base:
                        parcela.exchange_rate_to_base = rate
                        parcela.valor_parcela_convertido = (
                            parcela.valor_parcela * rate
                        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        parcela.save(update_fields=[
                            "exchange_rate_to_base",
                            "valor_parcela_convertido",
                            "updated_at",
                        ])
                        total_updated += 1
                except ExchangeRateError:
                    logger.warning(
                        "Failed to update rate for parcela %s of lancamento %s",
                        parcela.id, lanc.id,
                    )

    return {"updated": total_updated, "date": str(today)}


@shared_task(name="financeiro.tasks.reconcile_pix_transactions")
def reconcile_pix_transactions():
    """
    Every 15 min: expire pending PIX transactions whose expires_at has passed.
    """
    from django.utils import timezone

    from common.models import Org
    from financeiro.models import PaymentTransaction

    now = timezone.now()
    total_expired = 0

    for org in Org.objects.filter(is_active=True):
        set_rls_context(str(org.id))

        expired_count = PaymentTransaction.objects.filter(
            org=org,
            status="pending",
            expires_at__isnull=False,
            expires_at__lt=now,
        ).update(status="expired")

        if expired_count:
            logger.info(
                "PIX reconciliation [%s]: %d transactions expired.",
                org.name,
                expired_count,
            )
            total_expired += expired_count

    return {"expired_count": total_expired}


@shared_task(name="financeiro.tasks.pix_reconciliation_report")
def pix_reconciliation_report():
    """
    Daily: generate a reconciliation report per org.
    Checks for divergences between confirmed PaymentTransactions
    and their linked Payments/Parcelas.
    """
    from common.models import Org, Profile
    from financeiro.models import PaymentTransaction
    from integrations.models import IntegrationLog
    from invoices.models import Payment

    today = datetime.date.today()
    total_divergences = 0

    for org in Org.objects.filter(is_active=True):
        set_rls_context(str(org.id))

        # Get today's confirmed transactions
        confirmed_txs = PaymentTransaction.objects.filter(
            org=org,
            status="confirmed",
            paid_at__date=today,
        ).select_related("invoice", "lancamento")

        divergences = []

        for tx in confirmed_txs:
            # Check invoice linkage
            if tx.invoice:
                payment_exists = Payment.objects.filter(
                    invoice=tx.invoice,
                    reference_number=f"PIX:{tx.pix_txid}",
                ).exists()
                if not payment_exists:
                    divergences.append({
                        "transaction_id": str(tx.id),
                        "pix_txid": tx.pix_txid,
                        "type": "missing_invoice_payment",
                        "detail": f"Invoice {tx.invoice_id} sem Payment correspondente",
                    })

            # Check lancamento/parcela linkage
            if tx.lancamento:
                has_paid_parcela = tx.lancamento.parcelas.filter(
                    status="PAGO",
                    observacoes__contains=tx.pix_txid,
                ).exists()
                if not has_paid_parcela:
                    divergences.append({
                        "transaction_id": str(tx.id),
                        "pix_txid": tx.pix_txid,
                        "type": "missing_parcela_update",
                        "detail": f"Lancamento {tx.lancamento_id} sem Parcela atualizada",
                    })

        if divergences:
            total_divergences += len(divergences)

            # Log divergences
            for div in divergences:
                IntegrationLog.objects.create(
                    org=org,
                    connector_slug="pix_gateway",
                    operation="reconciliation_divergence",
                    direction="in",
                    entity_type="payment_transaction",
                    entity_id=div["transaction_id"],
                    status="error",
                    error_detail=div["detail"],
                    metadata_json=div,
                )

            # Notify org admins
            admins = Profile.objects.filter(
                org=org, role="ADMIN", is_active=True
            )
            for admin in admins:
                _send_pix_divergence_alert(admin, org, divergences, today)

        logger.info(
            "PIX reconciliation report [%s]: %d confirmed, %d divergences.",
            org.name,
            confirmed_txs.count(),
            len(divergences),
        )

    return {"divergences": total_divergences, "date": str(today)}


def _send_pix_divergence_alert(profile, org, divergences, report_date):
    """Send email alert about PIX reconciliation divergences."""
    from django.conf import settings
    from django.core.mail import EmailMessage

    subject = f"[TalkHub CRM] Alerta: {len(divergences)} divergência{'s' if len(divergences) != 1 else ''} PIX em {report_date.strftime('%d/%m/%Y')}"
    lines = [
        f"Olá {profile.user.get_username()},\n",
        f"Foram encontradas {len(divergences)} divergências na reconciliação PIX de hoje ({report_date.strftime('%d/%m/%Y')}):\n",
    ]
    for i, div in enumerate(divergences, 1):
        lines.append(f"{i}. TXID: {div['pix_txid']} — {div['detail']}")

    lines.append(f"\nVerifique em: {settings.DOMAIN_NAME}/financeiro/pix")
    body = "\n".join(lines)

    msg = EmailMessage(
        subject,
        body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[profile.user.email],
    )
    try:
        msg.send()
    except Exception:
        logger.exception(
            "Failed to send PIX divergence alert to %s", profile.user.email
        )
