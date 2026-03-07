"""
DRF serializers para TalkHub Omni integration (refatorado).
"""

from rest_framework import serializers

from .models import (
    OmniStatisticsSnapshot,
    TalkHubConnection,
    TalkHubFieldMapping,
    TalkHubOmniChannel,
    TalkHubSyncConfig,
    TalkHubSyncJob,
    TalkHubTeamMember,
    TalkHubTicketListMapping,
)


# ─── Connection ───────────────────────────────────────────────────────


class TalkHubCredentialsSerializer(serializers.Serializer):
    api_key = serializers.CharField(min_length=10)
    workspace_url = serializers.URLField(
        required=False, default="https://chat.talkhub.me"
    )


class TalkHubStatusSerializer(serializers.Serializer):
    connected = serializers.BooleanField()
    workspace_name = serializers.CharField(allow_blank=True, required=False)
    owner_email = serializers.EmailField(allow_blank=True, required=False)
    workspace_url = serializers.URLField(required=False)
    last_sync_at = serializers.DateTimeField(required=False, allow_null=True)


# ─── Sync Jobs ────────────────────────────────────────────────────────


class TalkHubSyncJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalkHubSyncJob
        fields = [
            "id", "sync_type", "status", "total_records",
            "imported_count", "updated_count", "skipped_count",
            "error_count", "progress_detail", "error_log",
            "started_at", "completed_at", "created_at",
        ]
        read_only_fields = fields


class TalkHubSyncHistorySerializer(serializers.ModelSerializer):
    """Serializer compacto para listagem de histórico."""
    class Meta:
        model = TalkHubSyncJob
        fields = [
            "id", "sync_type", "status", "total_records",
            "imported_count", "error_count", "started_at",
            "completed_at", "created_at",
        ]
        read_only_fields = fields


# ─── Channels ─────────────────────────────────────────────────────────


class TalkHubOmniChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalkHubOmniChannel
        fields = [
            "id", "channel_type", "api_key", "is_active",
            "is_connected", "last_tested_at", "display_name",
        ]
        read_only_fields = ["id", "is_connected", "last_tested_at"]
        extra_kwargs = {"api_key": {"write_only": True}}


# ─── Sync Config ──────────────────────────────────────────────────────


class TalkHubSyncConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalkHubSyncConfig
        fields = [
            "sync_enabled", "sync_contacts", "sync_tickets",
            "sync_tags", "sync_team_members", "sync_statistics",
            "sync_conversations", "contacts_interval_minutes",
            "tickets_interval_minutes", "statistics_interval_minutes",
        ]


# ─── Messaging ────────────────────────────────────────────────────────


class SendTextSerializer(serializers.Serializer):
    content = serializers.CharField()


class SendSMSSerializer(serializers.Serializer):
    content = serializers.CharField()


class SendEmailSerializer(serializers.Serializer):
    subject = serializers.CharField(required=False, default="")
    content = serializers.CharField()


class SendContentSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(
        choices=["image", "video", "audio", "file"]
    )
    url = serializers.URLField()
    caption = serializers.CharField(required=False, default="")


class SendWhatsAppTemplateSerializer(serializers.Serializer):
    template_name = serializers.CharField()
    template_params = serializers.DictField(required=False, default=dict)


class SendBroadcastSerializer(serializers.Serializer):
    message = serializers.CharField()
    segment_ns = serializers.CharField(required=False, default="")
    tag = serializers.CharField(required=False, default="")


class SendFlowSerializer(serializers.Serializer):
    flow_ns = serializers.CharField()
    flow_type = serializers.ChoiceField(
        choices=["main", "sub"], default="main"
    )


# ─── Opt-in / Opt-out ────────────────────────────────────────────────


class OptInOutSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=["sms", "email"])
    action = serializers.ChoiceField(choices=["opt_in", "opt_out"])


# ─── Tags & Labels ───────────────────────────────────────────────────


class TagActionSerializer(serializers.Serializer):
    tags = serializers.ListField(child=serializers.CharField(), min_length=1)


class LabelActionSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField(), min_length=1)


# ─── Agent Assignment ────────────────────────────────────────────────


class AssignAgentSerializer(serializers.Serializer):
    agent_id = serializers.CharField()


class AssignGroupSerializer(serializers.Serializer):
    group_id = serializers.CharField()


# ─── Team Members ────────────────────────────────────────────────────


class TalkHubTeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalkHubTeamMember
        fields = [
            "id", "omni_agent_id", "name", "email",
            "image", "role", "is_online", "crm_profile",
        ]
        read_only_fields = fields


# ─── Ticket List Mapping ─────────────────────────────────────────────


class TalkHubTicketListMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalkHubTicketListMapping
        fields = [
            "id", "omni_list_id", "omni_list_name",
            "pipeline_type", "lead_pipeline", "case_pipeline",
        ]


# ─── Field Mapping ───────────────────────────────────────────────────


class TalkHubFieldMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalkHubFieldMapping
        fields = [
            "id", "talkhub_var_ns", "talkhub_field_name",
            "crm_field_key", "field_type",
        ]


# ─── Bot Control ─────────────────────────────────────────────────────


class LogEventSerializer(serializers.Serializer):
    event_name = serializers.CharField()
    event_data = serializers.DictField(required=False, default=dict)


class UserFieldsSerializer(serializers.Serializer):
    fields = serializers.DictField(child=serializers.CharField())



