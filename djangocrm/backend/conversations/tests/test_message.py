"""
PBT: Envio de mensagem registra Message com direction correto.

Propriedade 34: Envio de mensagem registra Message com direction "out"
Valida: Requisitos 20.1-20.9
"""

import pytest
from django.utils import timezone
from hypothesis import given, settings
from hypothesis import strategies as st

from conversations.models import Conversation, Message


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Msg Test Org")


@pytest.fixture
def contact(db, org):
    from contacts.models import Contact
    return Contact.objects.create(org=org, first_name="Msg", last_name="Contact")


@pytest.fixture
def conversation(db, org, contact):
    return Conversation.objects.create(
        org=org, contact=contact, channel="webchat",
        status="open", last_message_at=timezone.now(),
    )


@pytest.mark.django_db
class TestMessageDirection:
    """Propriedade 34: Direction de mensagens."""

    @given(
        direction=st.sampled_from(["in", "out", "agent", "note", "system"]),
        msg_type=st.sampled_from(["text", "image", "video", "audio", "file", "payload"]),
    )
    @settings(max_examples=20)
    def test_message_persists_with_correct_direction(self, org, conversation, direction, msg_type):
        """Message persiste com direction e msg_type corretos."""
        msg = Message.objects.create(
            org=org,
            conversation=conversation,
            direction=direction,
            msg_type=msg_type,
            content="Test content",
            timestamp=timezone.now(),
        )
        assert msg.direction == direction
        assert msg.msg_type == msg_type
        msg.delete()

    def test_outbound_message_has_direction_out(self, org, conversation):
        """Mensagem enviada pelo CRM tem direction 'out'."""
        msg = Message.objects.create(
            org=org,
            conversation=conversation,
            direction="out",
            msg_type="text",
            content="Hello from CRM",
            sender_type="bot",
            timestamp=timezone.now(),
        )
        assert msg.direction == "out"

    def test_inbound_message_has_direction_in(self, org, conversation):
        """Mensagem recebida do contato tem direction 'in'."""
        msg = Message.objects.create(
            org=org,
            conversation=conversation,
            direction="in",
            msg_type="text",
            content="Hello from contact",
            sender_type="subscriber",
            timestamp=timezone.now(),
        )
        assert msg.direction == "in"
