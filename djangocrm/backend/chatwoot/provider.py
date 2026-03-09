"""
ChatwootProvider — ChannelProvider para comunicação via Chatwoot.

Permite enviar mensagens do CRM de volta ao Chatwoot, que as entrega
ao cliente final via WhatsApp, Instagram, Web Chat, etc.
"""

import logging

from channels.base import ChannelProvider, ChannelType, MessageCapability

logger = logging.getLogger(__name__)


def _get_chatwoot_config(org):
    """Get decrypted Chatwoot config from IntegrationConnection."""
    from chatwoot.connector import _decrypt_config
    from integrations.models import IntegrationConnection

    conn = IntegrationConnection.objects.filter(
        org=org, connector_slug="chatwoot", is_active=True, is_connected=True
    ).first()
    if not conn or not conn.config_json:
        return None

    return _decrypt_config(conn.config_json)


class ChatwootProvider(ChannelProvider):
    """Provedor de canal Chatwoot para envio de mensagens."""

    channel_type = ChannelType.CHATWOOT
    name = "Chatwoot"
    icon = "message-circle"

    def send_message(self, channel_config, contact, message_data):
        from chatwoot.connector import _api_request

        org = channel_config.org
        config = _get_chatwoot_config(org)
        if not config:
            raise ValueError("Chatwoot não configurado. Configure a integração Chatwoot primeiro.")

        # Get chatwoot_conversation_id from conversation metadata
        conversation_id = message_data.get("conversation_id")
        if not conversation_id:
            raise ValueError("conversation_id é obrigatório para enviar mensagem.")

        from conversations.models import Conversation
        try:
            conv = Conversation.objects.get(id=conversation_id, org=org)
        except Conversation.DoesNotExist:
            raise ValueError("Conversa não encontrada.")

        cw_conv_id = conv.metadata_json.get("chatwoot_conversation_id")
        if not cw_conv_id:
            raise ValueError("Conversa não está vinculada ao Chatwoot.")

        content = message_data.get("content", "")
        if not content:
            raise ValueError("Conteúdo da mensagem é obrigatório.")

        # Send message via Chatwoot API
        resp = _api_request(config, "POST", f"/conversations/{cw_conv_id}/messages", json={
            "content": content,
            "message_type": "outgoing",
            "content_attributes": {"external_created": True},
        })

        if resp.status_code not in (200, 201):
            logger.error("Chatwoot send_message failed: %s %s", resp.status_code, resp.text[:200])
            raise ValueError(f"Erro ao enviar mensagem no Chatwoot: HTTP {resp.status_code}")

        data = resp.json()
        external_id = data.get("id")
        logger.info("Chatwoot message sent: cw_conv=%s, msg_id=%s", cw_conv_id, external_id)

        return {
            "status": "sent",
            "provider": "chatwoot",
            "external_id": external_id,
        }

    def receive_message(self, channel_config, raw_payload):
        """Normalize a Chatwoot webhook payload into standard message dict."""
        sender = raw_payload.get("sender", {}) or {}
        msg_type_num = raw_payload.get("message_type", 0)
        direction_map = {0: "in", 1: "out", 2: "note", 3: "system"}

        return {
            "direction": direction_map.get(msg_type_num, "in"),
            "msg_type": "text",
            "content": raw_payload.get("content", ""),
            "sender_name": sender.get("name", ""),
            "sender_id": str(sender.get("id", "")),
            "metadata_json": {
                "chatwoot_message_id": raw_payload.get("id"),
                "chatwoot_conversation_id": raw_payload.get("conversation", {}).get("id"),
                "chatwoot_content_type": raw_payload.get("content_type", "text"),
            },
        }

    def get_capabilities(self):
        return [MessageCapability.TEXT, MessageCapability.IMAGE, MessageCapability.FILE]

    def get_status(self, channel_config):
        org = channel_config.org
        config = _get_chatwoot_config(org)
        return {
            "is_active": config is not None,
            "provider": "chatwoot",
        }

    def get_config_schema(self):
        return {
            "type": "object",
            "properties": {
                "chatwoot_url": {"type": "string", "title": "URL do Chatwoot"},
                "account_id": {"type": "integer", "title": "ID da Conta"},
            },
            "required": ["chatwoot_url", "account_id"],
        }
