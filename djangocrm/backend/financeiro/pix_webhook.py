"""
Public PIX webhook endpoint — receives payment confirmations from PIX gateway.

Endpoint: POST /webhooks/pix/<org_slug>/
- No JWT required (public webhook)
- Validates HMAC-SHA256 signature from X-Webhook-Signature header
- Updates PaymentTransaction status to "confirmed"
- Triggers post-confirmation tasks (invoice payment, parcela update)
"""

import json
import logging
import time

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class PixWebhookView(View):
    """
    POST /webhooks/pix/<org_slug>/

    Expected payload:
    {
        "pix_txid": "...",
        "pix_e2e_id": "...",
        "status": "confirmed",
        "paid_at": "2025-01-15T10:30:00Z",
        "payer_name": "...",
        "payer_document": "...",
        "amount": 150.00
    }

    Headers:
        X-Webhook-Signature: HMAC-SHA256 hex digest
    """

    def post(self, request, org_slug):
        from django.utils import timezone

        from common.models import Org
        from common.tasks import set_rls_context
        from financeiro.models import PaymentTransaction
        from financeiro.pix_gateway import get_pix_connection, verify_webhook_signature
        from integrations.models import WebhookLog

        start_time = time.time()

        # Resolve org by slug
        org = Org.objects.filter(slug=org_slug, is_active=True).first()
        if not org:
            return JsonResponse({"status": "ok"}, status=200)

        # Set RLS context
        set_rls_context(str(org.id))

        # Get PIX connection for webhook_secret
        connection = get_pix_connection(org)
        if not connection:
            self._log_webhook(
                org, "pix_confirmation", "rejected",
                {"reason": "no_pix_connection"}, start_time,
            )
            return JsonResponse({"status": "ok"}, status=200)

        # Parse payload
        try:
            payload_bytes = request.body
            payload = json.loads(payload_bytes)
        except (json.JSONDecodeError, ValueError):
            self._log_webhook(
                org, "pix_confirmation", "rejected",
                {"reason": "invalid_json"}, start_time,
            )
            return JsonResponse(
                {"error": "Invalid JSON"}, status=400
            )

        # Validate signature
        signature = request.headers.get("X-Webhook-Signature", "")
        webhook_secret = connection.webhook_secret

        if webhook_secret:
            if not verify_webhook_signature(payload_bytes, signature, webhook_secret):
                self._log_webhook(
                    org, "pix_confirmation", "rejected",
                    {"reason": "invalid_signature", "pix_txid": payload.get("pix_txid")},
                    start_time,
                )
                return JsonResponse(
                    {"error": "Invalid signature"}, status=401
                )

        pix_txid = payload.get("pix_txid")
        if not pix_txid:
            self._log_webhook(
                org, "pix_confirmation", "rejected",
                {"reason": "missing_pix_txid"}, start_time,
            )
            return JsonResponse({"status": "ok"}, status=200)

        # Find transaction
        transaction = PaymentTransaction.objects.filter(
            org=org, pix_txid=pix_txid
        ).first()

        if not transaction:
            self._log_webhook(
                org, "pix_confirmation", "rejected",
                {"reason": "txid_not_found", "pix_txid": pix_txid},
                start_time,
            )
            return JsonResponse({"status": "ok"}, status=200)

        # Idempotency: already confirmed
        if transaction.status == "confirmed":
            self._log_webhook(
                org, "pix_confirmation", "processed",
                {"pix_txid": pix_txid, "note": "already_confirmed"},
                start_time,
            )
            return JsonResponse({"status": "ok"}, status=200)

        # Update transaction
        transaction.status = "confirmed"
        transaction.pix_e2e_id = payload.get("pix_e2e_id", "")
        transaction.payer_name = payload.get("payer_name", "")
        if payload.get("payer_document"):
            transaction.payer_document = payload["payer_document"]

        paid_at_str = payload.get("paid_at")
        if paid_at_str:
            from django.utils.dateparse import parse_datetime
            transaction.paid_at = parse_datetime(paid_at_str) or timezone.now()
        else:
            transaction.paid_at = timezone.now()

        transaction.save()

        # Trigger post-confirmation tasks
        from financeiro.tasks import process_pix_confirmation

        process_pix_confirmation.delay(str(transaction.id), str(org.id))

        self._log_webhook(
            org, "pix_confirmation", "processed",
            {"pix_txid": pix_txid, "transaction_id": str(transaction.id)},
            start_time,
        )

        return JsonResponse({"status": "ok"}, status=200)

    def _log_webhook(self, org, event_type, status, payload_json, start_time):
        """Log webhook to WebhookLog."""
        try:
            from integrations.models import WebhookLog

            processing_time = int((time.time() - start_time) * 1000)
            WebhookLog.objects.create(
                org=org,
                connector_slug="pix_gateway",
                event_type=event_type,
                status=status,
                processing_time_ms=processing_time,
                payload_json=payload_json,
            )
        except Exception:
            logger.exception("Failed to log PIX webhook")
