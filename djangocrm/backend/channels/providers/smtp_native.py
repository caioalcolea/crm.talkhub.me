"""
SMTPNativeProvider — Provedor nativo de email via SMTP configurado pela org.

Usa as credenciais SMTP configuradas na IntegrationConnection (conector smtp)
para enviar emails. Cria conversas e mensagens no modelo de conversations.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from channels.base import ChannelProvider, ChannelType, MessageCapability

logger = logging.getLogger(__name__)


def _get_smtp_config(org):
    """Get decrypted SMTP config from IntegrationConnection."""
    from integrations.models import IntegrationConnection

    conn = IntegrationConnection.objects.filter(
        org=org, connector_slug="smtp", is_active=True, is_connected=True
    ).first()
    if not conn or not conn.config_json:
        return None

    config = dict(conn.config_json)

    # Decrypt secret fields
    from cryptography.fernet import Fernet, InvalidToken
    from django.conf import settings

    fernet_key = getattr(settings, "FERNET_KEY", None)
    if fernet_key:
        f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
        for field in ("smtp_password",):
            value = config.get(field, "")
            if value and isinstance(value, str) and value.startswith("gAAAAA"):
                try:
                    config[field] = f.decrypt(value.encode()).decode()
                except (InvalidToken, Exception):
                    logger.error("Failed to decrypt %s for org %s", field, org.id)

    return config


def _send_via_smtp(smtp_config, from_email, to_email, subject, text_body, html_body=None, reply_to=None):
    """Send an email using the org's SMTP configuration."""
    host = smtp_config.get("smtp_host", "")
    port = int(smtp_config.get("smtp_port", 587))
    user = smtp_config.get("smtp_user", "")
    password = smtp_config.get("smtp_password", "")

    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject or "(sem assunto)"
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    use_ssl = port == 465
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=30) as server:
            server.ehlo()
            if user and password:
                server.login(user, password)
            server.sendmail(from_email, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            if port != 25:
                server.starttls()
                server.ehlo()
            if user and password:
                server.login(user, password)
            server.sendmail(from_email, [to_email], msg.as_string())

    logger.info("Email sent via SMTP: from=%s to=%s subject=%s", from_email, to_email, subject)


class SMTPNativeProvider(ChannelProvider):
    """Provedor nativo de email via SMTP configurado pela org."""

    channel_type = ChannelType.SMTP_NATIVE
    name = "Email (SMTP Nativo)"
    icon = "mail"

    def send_message(self, channel_config, contact, message_data):
        org = channel_config.org
        smtp_config = _get_smtp_config(org)
        if not smtp_config:
            raise ValueError("SMTP não configurado. Configure a integração SMTP primeiro.")

        from_email = smtp_config.get("from_email", "")
        reply_to = smtp_config.get("reply_to", "")
        to_email = contact.email if hasattr(contact, "email") else message_data.get("to_email", "")

        if not to_email:
            raise ValueError("Contato não possui email configurado.")

        subject = message_data.get("subject", "")
        content = message_data.get("content", "")
        html_content = message_data.get("html_content")

        # If no subject, try to get from conversation metadata
        if not subject:
            conversation_id = message_data.get("conversation_id")
            if conversation_id:
                from conversations.models import Conversation
                try:
                    conv = Conversation.objects.get(id=conversation_id)
                    subject = conv.metadata_json.get("email_subject", "")
                except Conversation.DoesNotExist:
                    pass

        if not subject:
            subject = f"Re: Conversa com {contact.first_name}" if hasattr(contact, "first_name") else ""

        _send_via_smtp(smtp_config, from_email, to_email, subject, content, html_content, reply_to)
        return {"status": "sent", "provider": "smtp_native"}

    def receive_message(self, channel_config, raw_payload):
        """Process a received email into a normalized message dict."""
        return {
            "direction": "in",
            "msg_type": "text",
            "content": raw_payload.get("body", ""),
            "sender_name": raw_payload.get("from_name", ""),
            "sender_id": raw_payload.get("from_email", ""),
            "metadata_json": {
                "email_subject": raw_payload.get("subject", ""),
                "email_from": raw_payload.get("from_email", ""),
                "email_to": raw_payload.get("to_email", ""),
                "email_message_id": raw_payload.get("message_id", ""),
                "email_in_reply_to": raw_payload.get("in_reply_to", ""),
                "email_references": raw_payload.get("references", ""),
            },
        }

    def get_capabilities(self):
        return [MessageCapability.TEXT, MessageCapability.EMAIL, MessageCapability.FILE]

    def get_status(self, channel_config):
        org = channel_config.org
        smtp_config = _get_smtp_config(org)
        return {
            "is_active": smtp_config is not None,
            "provider": "smtp_native",
        }

    def get_config_schema(self):
        return {
            "type": "object",
            "properties": {
                "from_email": {"type": "string", "format": "email", "title": "From Email"},
                "reply_to": {"type": "string", "format": "email", "title": "Reply To"},
            },
            "required": ["from_email"],
        }
