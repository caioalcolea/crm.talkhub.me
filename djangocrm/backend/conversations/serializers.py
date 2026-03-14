"""
Serializers do app conversations.
"""

import re

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
    is_group = serializers.SerializerMethodField()

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
            "is_group",
            "last_message",
            "metadata_json",
            "created_at",
        )
        read_only_fields = fields

    def get_is_group(self, obj):
        return bool((obj.metadata_json or {}).get("is_group"))

    def get_last_message(self, obj):
        # Use prefetched messages if available (avoids N+1)
        if hasattr(obj, "_latest_messages") and obj._latest_messages:
            msg = obj._latest_messages[0]
        else:
            msg = obj.messages.order_by("-timestamp").first()
        if msg:
            content = msg.content or ""
            meta = msg.metadata_json or {}
            # For email messages: use stored text_body if available,
            # otherwise strip HTML from full content BEFORE truncating
            if meta.get("text_body"):
                content = meta["text_body"]
            elif meta.get("content_type") == "html" or (
                content and re.search(r"<[a-z][\s\S]*>", content[:500], re.IGNORECASE)
            ):
                content = re.sub(r"<[^>]+>", "", content)
                content = re.sub(r"&\w+;", " ", content)
            content = " ".join(content.split())  # Normalize whitespace
            return {
                "content": content[:100],
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
    is_group = serializers.SerializerMethodField()

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
            "is_group",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_is_group(self, obj):
        return bool((obj.metadata_json or {}).get("is_group"))

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}".strip()
        return ""

    def get_contact_email(self, obj):
        return obj.contact.email if obj.contact else ""

    def get_assigned_to_name(self, obj):
        if obj.assigned_to and obj.assigned_to.user:
            return obj.assigned_to.user.email
        return None


class ConversationUpdateSerializer(serializers.ModelSerializer):
    """Serializer para PATCH de conversa (status, assigned_to, contact)."""

    class Meta:
        model = Conversation
        fields = ("status", "assigned_to", "contact")
