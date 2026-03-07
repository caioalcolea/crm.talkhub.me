"""
TalkHubOmniProvider — ChannelProvider implementation for TalkHub Omni.

Suporta todas as capacidades de mensageria do TalkHub Omni:
text, image, video, audio, file, template, rich_card, broadcast, sms, email.

Registrado automaticamente via AppConfig.ready() → ChannelRegistry.register().
"""

import logging

from channels.base import ChannelProvider, ChannelType, MessageCapability

from .client import TalkHubAPIError, TalkHubClient

logger = logging.getLogger(__name__)


class TalkHubOmniProvider(ChannelProvider):
    channel_type = ChannelType.TALKHUB_OMNI
    name = "TalkHub Omni"
    icon = "talkhub-omni.svg"

    def send_message(self, channel_config, contact, message_data: dict) -> dict:
        client = self._get_client(channel_config)
        user_ns = contact.talkhub_subscriber_id
        if not user_ns:
            raise ValueError("Contact has no talkhub_subscriber_id")

        msg_type = message_data.get("type", "text")

        try:
            if msg_type == "text":
                return client.send_text(user_ns, message_data["content"])
            elif msg_type == "sms":
                if getattr(contact, "sms_opt_in", False) is False:
                    raise ValueError("Contact has not opted in to SMS")
                return client.send_sms(user_ns, message_data["content"])
            elif msg_type == "email":
                if getattr(contact, "email_opt_in", False) is False:
                    raise ValueError("Contact has not opted in to email")
                return client.send_email(
                    user_ns, message_data["content"],
                    message_data.get("subject", ""),
                )
            elif msg_type == "content":
                return client.send_content(user_ns, message_data)
            elif msg_type == "whatsapp_template":
                return client.send_whatsapp_template(user_ns, message_data.get("template", {}))
            elif msg_type == "broadcast":
                return client.send_broadcast(message_data)
            elif msg_type == "flow":
                flow_ns = message_data.get("flow_ns", "")
                return client.send_main_flow(user_ns, flow_ns)
            else:
                raise ValueError(f"Unsupported message type: {msg_type}")
        except TalkHubAPIError as exc:
            logger.error("TalkHub send failed: type=%s, user=%s, err=%s", msg_type, user_ns, exc)
            return {"status": "error", "error": str(exc)}

    def receive_message(self, channel_config, raw_payload: dict) -> dict:
        return {
            "sender_id": raw_payload.get("user_ns"),
            "content": raw_payload.get("text", ""),
            "msg_type": raw_payload.get("type", "text"),
            "media_url": raw_payload.get("media_url"),
            "timestamp": raw_payload.get("timestamp"),
            "channel": raw_payload.get("channel", ""),
        }

    def get_capabilities(self) -> list[MessageCapability]:
        return [
            MessageCapability.TEXT,
            MessageCapability.IMAGE,
            MessageCapability.VIDEO,
            MessageCapability.AUDIO,
            MessageCapability.FILE,
            MessageCapability.TEMPLATE,
            MessageCapability.RICH_CARD,
            MessageCapability.BROADCAST,
            MessageCapability.SMS,
            MessageCapability.EMAIL,
        ]

    def get_status(self, channel_config) -> dict:
        client = self._get_client(channel_config)
        try:
            info = client.get_team_info()
            return {
                "is_active": True,
                "workspace": info.get("name", ""),
                "provider": "talkhub_omni",
            }
        except TalkHubAPIError:
            return {"is_active": False, "provider": "talkhub_omni"}

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "api_key": {"type": "string", "title": "API Key"},
                "base_url": {
                    "type": "string",
                    "format": "uri",
                    "default": "https://chat.talkhub.me",
                },
            },
            "required": ["api_key"],
        }

    def _get_client(self, channel_config) -> TalkHubClient:
        config = channel_config.config_json or {}
        return TalkHubClient(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://chat.talkhub.me"),
        )
