"""
SMTPNativeProvider — Provedor nativo de email via Django email backend.

Funciona sem nenhuma integração externa. Usa o backend de email
configurado no Django (SES, SMTP, etc.).
"""

from channels.base import ChannelProvider, ChannelType, MessageCapability


class SMTPNativeProvider(ChannelProvider):
    """Provedor nativo de email via Django email backend."""

    channel_type = ChannelType.SMTP_NATIVE
    name = "Email (SMTP Nativo)"
    icon = "mail"

    def send_message(self, channel_config, contact, message_data):
        from django.core.mail import send_mail

        send_mail(
            subject=message_data.get("subject", ""),
            message=message_data.get("content", ""),
            html_message=message_data.get("html_content"),
            from_email=channel_config.config_json.get("from_email"),
            recipient_list=[contact.email],
            fail_silently=False,
        )
        return {"status": "sent", "provider": "smtp_native"}

    def receive_message(self, channel_config, raw_payload):
        raise NotImplementedError("SMTP native does not support inbound messages")

    def get_capabilities(self):
        return [MessageCapability.TEXT, MessageCapability.EMAIL, MessageCapability.FILE]

    def get_status(self, channel_config):
        return {"is_active": True, "provider": "smtp_native"}

    def get_config_schema(self):
        return {
            "type": "object",
            "properties": {
                "from_email": {"type": "string", "format": "email", "title": "From Email"},
                "reply_to": {"type": "string", "format": "email", "title": "Reply To"},
            },
            "required": ["from_email"],
        }
