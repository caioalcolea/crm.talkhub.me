"""
Public tracking endpoints for campaigns (no JWT required).

- TrackingPixelView: GET /track/open/<recipient_id>/ — 1x1 transparent PNG
- UnsubscribeView: GET /track/unsubscribe/<recipient_id>/ — opt-out

These endpoints are public (no JWT) so they must bypass RLS using raw SQL
to set org context from the recipient's org_id. Same pattern as webhook_receiver.
UUID recipient IDs serve as the authentication token (cryptographically hard to guess).
"""

import base64
import logging

from django.db import connection
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

# 1x1 transparent PNG
TRANSPARENT_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _set_rls_for_recipient(recipient_id):
    """
    Set RLS context from recipient's org — public endpoints use UUID as auth.

    Uses raw SQL to bypass RLS (since no org context is available yet),
    then sets app.current_org so subsequent ORM queries work normally.
    Uses transaction-scoped config (true) so it resets after the request.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_org', cr.org_id::text, true) "
            "FROM campaign_recipient cr WHERE cr.id = %s",
            [str(recipient_id)]
        )
        return cursor.fetchone() is not None


@method_decorator(csrf_exempt, name="dispatch")
class TrackingPixelView(View):
    """
    Retorna imagem PNG 1x1 transparente e registra abertura.
    Apenas a primeira abertura atualiza opened_at.
    """

    def get(self, request, recipient_id):
        from campaigns.models import CampaignRecipient

        try:
            if not _set_rls_for_recipient(recipient_id):
                return HttpResponse(TRANSPARENT_PIXEL, content_type="image/png")

            recipient = CampaignRecipient.objects.select_related(
                "campaign"
            ).get(id=recipient_id)

            # Only update on first open
            if not recipient.opened_at:
                recipient.status = "opened"
                recipient.opened_at = timezone.now()
                recipient.save(update_fields=["status", "opened_at", "updated_at"])

                # Increment campaign counter
                campaign = recipient.campaign
                campaign.opened_count += 1
                campaign.save(update_fields=["opened_count"])

        except CampaignRecipient.DoesNotExist:
            pass  # Silently ignore unknown recipients
        except Exception:
            logger.exception("Error tracking open for recipient %s", recipient_id)

        return HttpResponse(TRANSPARENT_PIXEL, content_type="image/png")


@method_decorator(csrf_exempt, name="dispatch")
class UnsubscribeView(View):
    """
    Processa opt-out de um recipient.
    Atualiza email_opt_in=False no Contact e status=unsubscribed no recipient.
    """

    def get(self, request, recipient_id):
        from campaigns.models import CampaignRecipient

        try:
            if not _set_rls_for_recipient(recipient_id):
                return HttpResponse(
                    "<html><body><h2>Link inválido.</h2></body></html>",
                    content_type="text/html; charset=utf-8",
                    status=404,
                )

            recipient = CampaignRecipient.objects.select_related(
                "contact"
            ).get(id=recipient_id)

            # Update recipient status
            if recipient.status != "unsubscribed":
                recipient.status = "unsubscribed"
                recipient.save(update_fields=["status", "updated_at"])

            # Update contact opt-in
            contact = recipient.contact
            if contact and getattr(contact, "email_opt_in", True):
                contact.email_opt_in = False
                contact.save(update_fields=["email_opt_in"])

        except CampaignRecipient.DoesNotExist:
            pass  # Silently ignore unknown recipients
        except Exception:
            logger.exception("Error processing unsubscribe for %s", recipient_id)

        return HttpResponse(
            "<html><body><h2>Você foi descadastrado com sucesso.</h2>"
            "<p>Você não receberá mais emails desta campanha.</p>"
            "</body></html>",
            content_type="text/html; charset=utf-8",
        )
