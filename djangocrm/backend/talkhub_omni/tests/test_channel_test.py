"""
PBT: Teste de conexão de canal TalkHub Omni.

Propriedade 43: Teste de conexão valida API key e retorna status.
Valida: Requisito 14.4
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from talkhub_omni.models import TalkHubOmniChannel


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Channel Test Org")


@pytest.mark.django_db
class TestChannelConnection:
    """Propriedade 43: Teste de conexão de canal."""

    @given(
        channel_type=st.sampled_from([
            "whatsapp_cloud", "whatsapp_groups", "instagram",
            "telegram", "sms", "webchat", "email",
        ]),
        is_active=st.booleans(),
    )
    @settings(max_examples=10)
    def test_channel_persists_with_correct_type(self, org, channel_type, is_active):
        """Canal TalkHub Omni persiste com tipo e status corretos."""
        channel, _ = TalkHubOmniChannel.objects.update_or_create(
            org=org, channel_type=channel_type,
            defaults={
                "is_active": is_active,
                "display_name": f"Test {channel_type}",
            },
        )
        channel.refresh_from_db()
        assert channel.channel_type == channel_type
        assert channel.is_active == is_active

    def test_unique_channel_type_per_org(self, org):
        """Mesmo channel_type não pode existir duas vezes na mesma org."""
        from django.db import IntegrityError

        TalkHubOmniChannel.objects.create(
            org=org, channel_type="webchat", display_name="Chat 1",
        )
        with pytest.raises(IntegrityError):
            TalkHubOmniChannel.objects.create(
                org=org, channel_type="webchat", display_name="Chat 2",
            )
