"""
AutomationRouter — despacho centralizado de mensagens.

Canais suportados:
- email: Envio via SMTP (settings.DEFAULT_FROM_EMAIL)
- whatsapp: Envio via TalkHub Omni client (send_text)
- internal: Notificação in-app (log)

Uso:
    from automations.router import dispatch
    result = dispatch(
        org_id="...",
        channel="email",
        recipient={"email": "user@example.com"},
        message="Olá!",
        metadata={"source": "routine"},
    )
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage

from common.tasks import set_rls_context

logger = logging.getLogger(__name__)


def _validate_recipient(channel, recipient):
    """Valida dados de contato do recipient para o canal escolhido."""
    if channel == "email":
        email = recipient.get("email")
        if not email:
            return False, "Recipient deve ter 'email' para canal email"
        return True, None

    elif channel == "whatsapp":
        phone = recipient.get("phone") or recipient.get("subscriber_id")
        if not phone:
            return False, "Recipient deve ter 'phone' ou 'subscriber_id' para canal whatsapp"
        return True, None

    elif channel == "internal":
        return True, None

    return False, f"Canal desconhecido: {channel}"


def _dispatch_email(recipient, message, metadata):
    """Enviar mensagem via SMTP."""
    to_email = recipient.get("email")
    subject = metadata.get("subject", "Notificação TalkHub CRM")
    name = recipient.get("name", "")

    msg = EmailMessage(
        subject,
        f"<p>{message}</p>",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    msg.content_subtype = "html"
    msg.send()

    return {"channel": "email", "sent_to": to_email, "subject": subject}


def _dispatch_whatsapp(org_id, recipient, message, metadata):
    """Enviar mensagem via TalkHub Omni (WhatsApp)."""
    from talkhub_omni.client import TalkHubClient
    from talkhub_omni.models import TalkHubConnection
    from common.models import Org

    org = Org.objects.get(id=org_id)
    conn = TalkHubConnection.objects.filter(org=org, is_active=True).first()
    if not conn:
        raise ValueError("Nenhuma conexão TalkHub ativa para esta organização")

    api_key = conn.api_key
    if not api_key:
        raise ValueError("API key não configurada na conexão TalkHub")

    client = TalkHubClient(api_key=api_key)

    subscriber_id = recipient.get("subscriber_id") or recipient.get("phone")
    client.send_text(subscriber_id, message)

    return {"channel": "whatsapp", "sent_to": subscriber_id}


def _dispatch_internal(org_id, recipient, message, metadata):
    """Notificação in-app (log-based)."""
    user_id = recipient.get("user_id", "system")
    logger.info(
        "Internal notification [org=%s, user=%s]: %s",
        org_id, user_id, message,
    )
    return {"channel": "internal", "user_id": user_id, "message": message}


def dispatch(org_id, channel, recipient, message, metadata=None):
    """
    Despacha mensagem pelo canal especificado.

    Args:
        org_id: UUID da organização
        channel: Canal de envio ("email", "whatsapp", "internal")
        recipient: Dict com dados do destinatário
        message: Conteúdo da mensagem
        metadata: Dados extras (subject, source, etc.)

    Returns:
        Dict com resultado do despacho

    Raises:
        ValueError: Se recipient inválido ou canal não suportado
    """
    metadata = metadata or {}

    # Validar recipient
    valid, error = _validate_recipient(channel, recipient)
    if not valid:
        raise ValueError(error)

    if channel == "email":
        return _dispatch_email(recipient, message, metadata)
    elif channel == "whatsapp":
        return _dispatch_whatsapp(org_id, recipient, message, metadata)
    elif channel == "internal":
        return _dispatch_internal(org_id, recipient, message, metadata)
    else:
        raise ValueError(f"Canal não suportado: {channel}")


@shared_task(name="automations.tasks.dispatch_message")
def dispatch_message_task(org_id, channel, recipient, message, metadata=None):
    """Celery task para despacho assíncrono via AutomationRouter."""
    set_rls_context(org_id)

    try:
        result = dispatch(org_id, channel, recipient, message, metadata)
        logger.info("Dispatch success: %s", result)
        return result
    except Exception as exc:
        logger.exception("Dispatch failed: %s", exc)
        raise
