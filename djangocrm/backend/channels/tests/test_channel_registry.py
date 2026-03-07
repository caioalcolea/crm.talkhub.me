"""
PBT: Canal desativado bloqueia envio e múltiplos provedores por tipo.

Propriedade 31: Canal desativado bloqueia envio
Propriedade 32: Múltiplos provedores por tipo de comunicação
Valida: Requisitos 13.7, 13.8
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from channels.base import ChannelProvider, ChannelType, MessageCapability
from channels.registry import ChannelRegistry


def _make_provider(channel_type_val, capabilities, name="TestProvider"):
    """Create a minimal ChannelProvider subclass."""
    class FakeProvider(ChannelProvider):
        channel_type = channel_type_val
        name = name
        icon = "test.svg"

        def send_message(self, channel_config, contact, message_data):
            if channel_config and not channel_config.get("is_active", True):
                raise RuntimeError("Channel is disabled")
            return {"status": "sent"}

        def receive_message(self, channel_config, raw_payload):
            return raw_payload

        def get_capabilities(self):
            return capabilities

        def get_status(self, channel_config):
            return {"is_active": True}

        def get_config_schema(self):
            return {}

    FakeProvider.__name__ = name
    return FakeProvider


class TestChannelDisabledBlocksSend:
    """Propriedade 31: Canal desativado bloqueia envio."""

    def test_disabled_channel_raises_on_send(self):
        """Envio por canal desativado levanta exceção."""
        provider_cls = _make_provider(ChannelType.WEBCHAT, [MessageCapability.TEXT])
        provider = provider_cls()

        with pytest.raises(RuntimeError, match="disabled"):
            provider.send_message({"is_active": False}, None, {"text": "hello"})

    def test_active_channel_sends_successfully(self):
        """Envio por canal ativo funciona."""
        provider_cls = _make_provider(ChannelType.WEBCHAT, [MessageCapability.TEXT])
        provider = provider_cls()

        result = provider.send_message({"is_active": True}, None, {"text": "hello"})
        assert result["status"] == "sent"


class TestMultipleProviders:
    """Propriedade 32: Múltiplos provedores por tipo de comunicação."""

    def test_multiple_providers_coexist(self):
        """Múltiplos provedores podem ser registrados e coexistir."""
        ChannelRegistry._providers = {}

        p1 = _make_provider(ChannelType.TALKHUB_OMNI, [MessageCapability.TEXT, MessageCapability.IMAGE], "TalkHub")
        p2 = _make_provider(ChannelType.SMTP_NATIVE, [MessageCapability.TEXT, MessageCapability.EMAIL], "SMTP")

        ChannelRegistry.register(p1)
        ChannelRegistry.register(p2)

        assert len(ChannelRegistry.all()) == 2
        assert ChannelRegistry.get("talkhub_omni") is p1
        assert ChannelRegistry.get("smtp_native") is p2

    @given(
        cap=st.sampled_from(list(MessageCapability)),
    )
    @settings(max_examples=10)
    def test_get_for_capability_returns_matching_providers(self, cap):
        """get_for_capability retorna provedores que suportam a capacidade."""
        ChannelRegistry._providers = {}

        all_caps = list(MessageCapability)
        p_with = _make_provider(ChannelType.WEBCHAT, all_caps, "AllCaps")
        p_without = _make_provider(ChannelType.SMTP_NATIVE, [], "NoCaps")

        ChannelRegistry.register(p_with)
        ChannelRegistry.register(p_without)

        matching = ChannelRegistry.get_for_capability(cap)
        assert p_with in matching
        assert p_without not in matching
