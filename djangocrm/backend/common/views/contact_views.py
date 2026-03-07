"""
Public contact form view — no authentication required.
Rate-limited to 5 requests per hour per IP.
"""

import logging

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.serializers import ContactFormSubmissionSerializer
from common.tasks import send_contact_form_email

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter (per process)
# For production multi-process environments the Celery task delay acts as
# a natural back-pressure; a Redis-based throttle can be added if needed.
from django.core.cache import cache


def _rate_key(request):
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
    return f"contact_form_rate:{ip.split(',')[0].strip()}"


def _is_rate_limited(request):
    key = _rate_key(request)
    count = cache.get(key, 0)
    if count >= 5:
        return True
    cache.set(key, count + 1, timeout=3600)
    return False


@method_decorator(never_cache, name="dispatch")
class ContactFormSubmitView(APIView):
    """
    Public endpoint — receives contact form submissions and queues
    an email to adm@talkhub.me via Celery.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if _is_rate_limited(request):
            return Response(
                {"detail": "Muitas solicitações. Tente novamente em 1 hora."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = ContactFormSubmissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        submission = serializer.save(
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            referrer=request.META.get("HTTP_REFERER", "")[:500] or None,
        )

        send_contact_form_email.delay(str(submission.id))
        logger.info(
            "Contact form submission created: id=%s reason=%s email=%s",
            submission.id,
            submission.reason,
            submission.email,
        )

        return Response(
            {"detail": "Mensagem enviada com sucesso. Em breve entraremos em contato."},
            status=status.HTTP_201_CREATED,
        )
