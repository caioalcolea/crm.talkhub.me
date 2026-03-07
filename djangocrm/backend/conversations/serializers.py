"""
Serializers do app conversations.
"""

from django.utils import timezone
from rest_framework import serializers

from conversations.models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer para leitura de Message."""

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation",
            "direction",
            "msg_type",
            "content",
            "media_url",
            "sender_type",
            "sender_name",
            "sender_id",
            "timestamp",
            "metadata_json",
            "created_at",
        )
        read_only_fields = fields


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer para envio de mensagem com seleção de canal."""

    channel_type = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Message
        fields = (
            "msg_type",
            "content",
            "media_url",
            "metadata_json",
            "channel_type",
        )

    def create(self, validated_data):
        validated_data.pop("channel_type", None)
        validated_data.setdefault("timestamp", timezone.now())
        validated_data.setdefault("direction", "out")
        validated_data.setdefault("sender_type", "agent")
        return super().create(validated_data)


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer para listagem de conversas com última mensagem."""

    last_message = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "channel",
            "status",
            "assigned_to",
            "last_message_at",
            "contact",
            "contact_name",
            "last_message",
            "created_at",
        )
        read_only_fields = fields

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-timestamp").first()
        if msg:
            return {
                "content": msg.content[:100],
                "direction": msg.direction,
                "msg_type": msg.msg_type,
                "timestamp": msg.timestamp,
            }
        return None

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}".strip()
        return ""


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer de detalhe de conversa com info do contato."""

    contact_name = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "channel",
            "integration_provider",
            "status",
            "assigned_to",
            "assigned_to_name",
            "last_message_at",
            "omni_user_ns",
            "metadata_json",
            "contact",
            "contact_name",
            "contact_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}".strip()
        return ""

    def get_contact_email(self, obj):
        return obj.contact.email if obj.contact else ""

    def get_assigned_to_name(self, obj):
        if obj.assigned_to and obj.assigned_to.user:
            return obj.assigned_to.user.get_full_name() or obj.assigned_to.user.email
        return None


class ConversationUpdateSerializer(serializers.ModelSerializer):
    """Serializer para PATCH de conversa (status, assigned_to, contact)."""

    class Meta:
        model = Conversation
        fields = ("status", "assigned_to", "contact")
