"""
ChannelProvider ABC, ChannelType enum e MessageCapability enum.

O sistema de canais é uma funcionalidade nativa da plataforma.
Funciona sem nenhuma integração ativa. Integrações apenas registram
provedores adicionais.
"""

from abc import ABC, abstractmethod
from enum import Enum


class ChannelType(str, Enum):
    TALKHUB_OMNI = "talkhub_omni"
    SMTP_NATIVE = "smtp_native"
    CHATWOOT = "chatwoot"
    EVOLUTION_API = "evolution_api"
    WHATSAPP_DIRECT = "whatsapp_direct"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    EMAIL = "email"
    WEBCHAT = "webchat"


class MessageCapability(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    TEMPLATE = "template"
    RICH_CARD = "rich_card"
    BROADCAST = "broadcast"
    SMS = "sms"
    EMAIL = "email"


class ChannelProvider(ABC):
    """Interface base para provedores de canal de comunicação."""

    channel_type: ChannelType
    name: str
    icon: str

    @abstractmethod
    def send_message(self, channel_config, contact, message_data: dict) -> dict:
        """Enviar mensagem. Retorna {message_id, status, ...}."""
        ...

    @abstractmethod
    def receive_message(self, channel_config, raw_payload: dict) -> dict:
        """Processar mensagem recebida. Retorna dados normalizados."""
        ...

    @abstractmethod
    def get_capabilities(self) -> list[MessageCapability]:
        """Retornar capacidades suportadas pelo canal."""
        ...

    @abstractmethod
    def get_status(self, channel_config) -> dict:
        """Retornar status do canal: {is_active, last_message_at, ...}."""
        ...

    @abstractmethod
    def get_config_schema(self) -> dict:
        """Retornar JSON Schema do formulário de configuração."""
        ...
