"""
Serializers do app integrations.

Serializers para IntegrationConnection, SyncJob, IntegrationLog,
WebhookLog, FieldMapping e ConflictLog.
"""

from rest_framework import serializers

from integrations.models import (
    ConflictLog,
    FieldMapping,
    IntegrationConnection,
    IntegrationLog,
    OrgFeatureFlag,
    SyncJob,
    WebhookLog,
)


class OrgFeatureFlagSerializer(serializers.ModelSerializer):
    """Serializer para OrgFeatureFlag."""

    class Meta:
        model = OrgFeatureFlag
        fields = (
            "id",
            "feature_key",
            "is_enabled",
            "config_json",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class IntegrationConnectionSerializer(serializers.ModelSerializer):
    """Serializer de leitura para IntegrationConnection."""

    class Meta:
        model = IntegrationConnection
        fields = (
            "id",
            "connector_slug",
            "display_name",
            "is_active",
            "is_connected",
            "webhook_token",
            "last_sync_at",
            "health_status",
            "error_count",
            "last_error",
            "sync_interval_minutes",
            "conflict_strategy",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class IntegrationConnectionConfigSerializer(serializers.ModelSerializer):
    """Serializer para atualização de configuração de integração."""

    sync_interval_minutes = serializers.IntegerField(
        min_value=5, max_value=1440, required=False
    )

    class Meta:
        model = IntegrationConnection
        fields = (
            "config_json",
            "conflict_strategy",
            "webhook_secret",
            "sync_interval_minutes",
        )


class SyncJobSerializer(serializers.ModelSerializer):
    """Serializer para SyncJob."""

    class Meta:
        model = SyncJob
        fields = (
            "id",
            "connector_slug",
            "sync_type",
            "status",
            "total_records",
            "imported_count",
            "updated_count",
            "skipped_count",
            "error_count",
            "progress_detail",
            "error_log",
            "started_at",
            "completed_at",
            "created_at",
        )
        read_only_fields = fields


class IntegrationLogSerializer(serializers.ModelSerializer):
    """Serializer para IntegrationLog com filtros."""

    class Meta:
        model = IntegrationLog
        fields = (
            "id",
            "connector_slug",
            "operation",
            "direction",
            "entity_type",
            "entity_id",
            "status",
            "error_detail",
            "processing_time_ms",
            "metadata_json",
            "created_at",
        )
        read_only_fields = fields


class WebhookLogSerializer(serializers.ModelSerializer):
    """Serializer para WebhookLog."""

    class Meta:
        model = WebhookLog
        fields = (
            "id",
            "connector_slug",
            "event_type",
            "status",
            "processing_time_ms",
            "payload_json",
            "created_at",
        )
        read_only_fields = fields


class FieldMappingSerializer(serializers.ModelSerializer):
    """Serializer CRUD para FieldMapping."""

    class Meta:
        model = FieldMapping
        fields = (
            "id",
            "connector_slug",
            "source_field",
            "target_field",
            "field_type",
            "transform_config",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_target_field(self, value):
        """Validar que o campo destino é um campo válido do CRM via variable_registry."""
        from integrations.variable_registry import ACCOUNT_SCHEMA, CONTACT_SCHEMA

        valid_fields = (
            {m.crm_field for m in CONTACT_SCHEMA.values()}
            | {m.crm_field for m in ACCOUNT_SCHEMA.values()}
        )
        if value not in valid_fields:
            raise serializers.ValidationError(
                f"'{value}' is not a recognized CRM field. "
                f"Valid fields: {', '.join(sorted(valid_fields))}"
            )
        return value


class ConflictLogSerializer(serializers.ModelSerializer):
    """Serializer para ConflictLog."""

    class Meta:
        model = ConflictLog
        fields = (
            "id",
            "connector_slug",
            "entity_type",
            "entity_id",
            "crm_value",
            "external_value",
            "resolved_by",
            "fields_overwritten",
            "created_at",
        )
        read_only_fields = fields
