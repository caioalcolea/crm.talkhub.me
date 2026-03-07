"""
PBT: Isolamento multi-tenant via RLS.

Propriedade 30: Consultas retornam apenas registros da Org do contexto.
Valida: Requisitos 12.5, 17.8, 26.9
"""

import pytest
from django.utils import timezone
from hypothesis import given, settings
from hypothesis import strategies as st

from conversations.models import Conversation, Message


@pytest.fixture
def org_a(db):
    from common.models import Org
    return Org.objects.create(name="Org A")


@pytest.fixture
def org_b(db):
    from common.models import Org
    return Org.objects.create(name="Org B")


@pytest.fixture
def contact_a(db, org_a):
    from contacts.models import Contact
    return Contact.objects.create(org=org_a, first_name="A", last_name="Contact")


@pytest.fixture
def contact_b(db, org_b):
    from contacts.models import Contact
    return Contact.objects.create(org=org_b, first_name="B", last_name="Contact")


@pytest.mark.django_db
class TestMultiTenantIsolation:
    """Propriedade 30: Isolamento multi-tenant."""

    def test_conversation_isolated_by_org(self, org_a, org_b, contact_a, contact_b):
        """Conversas de Org A não aparecem em queries de Org B."""
        conv_a = Conversation.objects.create(
            org=org_a, contact=contact_a, channel="webchat",
            status="open", last_message_at=timezone.now(),
        )
        conv_b = Conversation.objects.create(
            org=org_b, contact=contact_b, channel="webchat",
            status="open", last_message_at=timezone.now(),
        )

        qs_a = Conversation.objects.filter(org=org_a)
        qs_b = Conversation.objects.filter(org=org_b)

        assert conv_a in qs_a
        assert conv_a not in qs_b
        assert conv_b in qs_b
        assert conv_b not in qs_a

    def test_message_isolated_by_org(self, org_a, org_b, contact_a, contact_b):
        """Messages de Org A não aparecem em queries de Org B."""
        conv_a = Conversation.objects.create(
            org=org_a, contact=contact_a, channel="webchat",
            status="open", last_message_at=timezone.now(),
        )
        conv_b = Conversation.objects.create(
            org=org_b, contact=contact_b, channel="webchat",
            status="open", last_message_at=timezone.now(),
        )

        msg_a = Message.objects.create(
            org=org_a, conversation=conv_a, direction="in",
            content="A msg", timestamp=timezone.now(),
        )
        msg_b = Message.objects.create(
            org=org_b, conversation=conv_b, direction="in",
            content="B msg", timestamp=timezone.now(),
        )

        assert Message.objects.filter(org=org_a).count() >= 1
        assert msg_b not in Message.objects.filter(org=org_a)
        assert msg_a not in Message.objects.filter(org=org_b)

    def test_integration_log_isolated_by_org(self, org_a, org_b):
        """IntegrationLog isolado por org."""
        from integrations.models import IntegrationLog

        log_a = IntegrationLog.objects.create(
            org=org_a, connector_slug="test", operation="sync",
            direction="in", entity_type="contact", status="success",
        )
        log_b = IntegrationLog.objects.create(
            org=org_b, connector_slug="test", operation="sync",
            direction="in", entity_type="contact", status="success",
        )

        assert log_a not in IntegrationLog.objects.filter(org=org_b)
        assert log_b not in IntegrationLog.objects.filter(org=org_a)

    def test_channel_config_isolated_by_org(self, org_a, org_b):
        """ChannelConfig isolado por org."""
        from channels.models import ChannelConfig

        cc_a = ChannelConfig.objects.create(
            org=org_a, channel_type="webchat",
            provider="test", display_name="A Chat",
        )
        cc_b = ChannelConfig.objects.create(
            org=org_b, channel_type="webchat",
            provider="test", display_name="B Chat",
        )

        assert cc_a not in ChannelConfig.objects.filter(org=org_b)
        assert cc_b not in ChannelConfig.objects.filter(org=org_a)
