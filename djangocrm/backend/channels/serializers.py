"""
Serializers do app channels.
"""

from rest_framework import serializers

from channels.models import ChannelConfig


class ChannelConfigSerializer(serializers.ModelSerializer):
    """Serializer CRUD para ChannelConfig."""

    class Meta:
        model = ChannelConfig
        fields = (
            "id",
            "channel_type",
            "provider",
            "display_name",
            "config_json",
            "is_active",
            "capabilities_json",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ChannelProviderSerializer(serializers.Serializer):
    """Serializer para listar provedores disponíveis."""

    channel_type = serializers.CharField()
    name = serializers.CharField()
    icon = serializers.CharField()
    capabilities = serializers.ListField(child=serializers.CharField())
    config_schema = serializers.DictField()


class ChannelForActionSerializer(serializers.Serializer):
    """Serializer para canais disponíveis para uma ação específica."""

    channel_type = serializers.CharField()
    provider_name = serializers.CharField()
    display_name = serializers.CharField()
    is_active = serializers.BooleanField()
