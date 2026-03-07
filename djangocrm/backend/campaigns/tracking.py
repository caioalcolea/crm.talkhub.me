"""
Public tracking endpoints for campaigns (no JWT required).

- TrackingPixelView: GET /track/open/<recipient_id>/ — 1x1 transparent PNG
- UnsubscribeView: GET /track/unsubscribe/<recipient_id>/ — opt-out
"""

import base64
import logging

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


@method_decorator(csrf_exempt, name="dispatch")
class TrackingPixelView(View):
    """
    Retorna imagem PNG 1x1 transparente e registra abertura.
    Apenas a primeira abertura atualiza opened_at.
    """

    def get(self, request, recipient_id):
        from campaigns.models import CampaignRecipient

        try:
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
