"""
PBT: Configuração de canais — modelo ChannelConfig.

Complemento da Propriedade 31/32 para persistência.
Valida: Requisitos 13.6, 13.7
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from channels.models import ChannelConfig


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Channel Test Org")


@pytest.mark.django_db
class TestChannelConfigModel:

    @given(
        channel_type=st.sampled_from([
            "talkhub_omni", "smtp_native", "chatwoot",
            "evolution_api", "webchat", "email",
        ]),
        is_active=st.booleans(),
    )
    @settings(max_examples=10)
    def test_channel_config_persists_correctly(self, org, channel_type, is_active):
        """ChannelConfig persiste com tipo e status corretos."""
        config = ChannelConfig.objects.create(
            org=org,
            channel_type=channel_type,
            provider=f"provider-{channel_type}",
            display_name=f"Test {channel_type}",
            is_active=is_active,
        )
        assert config.pk is not None
        assert config.channel_type == channel_type
        assert config.is_active == is_active

        # Cleanup
        config.delete()
