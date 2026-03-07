"""
PBT: Filtro de conversas e atribuição de agente.

Propriedade 33: Filtro de conversas por canal/status/agente
Propriedade 36: Atribuição de agente atualiza Conversation
Valida: Requisitos 17.3, 22.7
"""

import pytest
from django.utils import timezone
from hypothesis import given, settings
from hypothesis import strategies as st

from conversations.models import Conversation


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Conv Test Org")


@pytest.fixture
def contact(db, org):
    from contacts.models import Contact
    return Contact.objects.create(
        org=org, first_name="Test", last_name="Contact",
    )


@pytest.fixture
def profile(db, org):
    from django.contrib.auth.models import User
    from common.models import Profile
    user = User.objects.create_user(username="agent_conv", password="pass")
    return Profile.objects.create(user=user, org=org, role="ADMIN")


@pytest.mark.django_db
class TestConversationFilters:
    """Propriedade 33: Filtro de conversas."""

    @given(
        status=st.sampled_from(["open", "pending", "resolved"]),
        channel=st.sampled_from(["talkhub_omni", "smtp_native", "webchat"]),
    )
    @settings(max_examples=15)
    def test_filter_by_status_and_channel(self, org, contact, status, channel):
        """Conversas filtradas por status e canal retornam apenas matches."""
        conv = Conversation.objects.create(
            org=org, contact=contact, channel=channel,
            status=status, last_message_at=timezone.now(),
        )

        qs = Conversation.objects.filter(org=org, status=status, channel=channel)
        assert conv in qs

        # Filtro com status diferente não inclui
        other_status = [s for s in ["open", "pending", "resolved"] if s != status][0]
        qs_other = Conversation.objects.filter(org=org, status=other_status, channel=channel)
        assert conv not in qs_other

        conv.delete()


@pytest.mark.django_db
class TestAgentAssignment:
    """Propriedade 36: Atribuição de agente."""

    def test_assign_agent_updates_conversation(self, org, contact, profile):
        """Atribuir agente atualiza campo assigned_to."""
        conv = Conversation.objects.create(
            org=org, contact=contact, channel="webchat",
            status="open", last_message_at=timezone.now(),
        )
        assert conv.assigned_to is None

        conv.assigned_to = profile
        conv.save()
        conv.refresh_from_db()

        assert conv.assigned_to == profile

    def test_unassign_agent(self, org, contact, profile):
        """Desatribuir agente limpa campo assigned_to."""
        conv = Conversation.objects.create(
            org=org, contact=contact, channel="webchat",
            status="open", assigned_to=profile,
            last_message_at=timezone.now(),
        )
        conv.assigned_to = None
        conv.save()
        conv.refresh_from_db()

        assert conv.assigned_to is None
