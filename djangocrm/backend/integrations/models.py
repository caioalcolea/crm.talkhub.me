from django.db import models

from common.base import BaseOrgModel


class OrgFeatureFlag(BaseOrgModel):
    """Feature flag por organização para controlar integrações habilitadas."""

    feature_key = models.CharField(max_length=100, db_index=True)
    is_enabled = models.BooleanField(default=False)
    config_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "org_feature_flag"
        unique_together = ("org", "feature_key")
        indexes = [
            models.Index(fields=["org", "feature_key"]),
        ]

    def __str__(self):
        status = "ativo" if self.is_enabled else "inativo"
        return f"{self.feature_key} ({status}) - {self.org}"


class IntegrationConnection(BaseOrgModel):
    """Conexão de integração por org. Modelo base genérico."""

    HEALTH_CHOICES = [
        ("healthy", "Healthy"),
        ("degraded", "Degraded"),
        ("down", "Down"),
        ("unknown", "Unknown"),
    ]
    CONFLICT_CHOICES = [
        ("last_write_wins", "Last Write Wins"),
        ("crm_wins", "CRM Wins"),
        ("external_wins", "External Wins"),
    ]

    connector_slug = models.CharField(max_length=100, db_index=True)
    display_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    is_connected = models.BooleanField(default=False)
    config_json = models.JSONField(default=dict, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True, default="")
    last_sync_at = models.DateTimeField(null=True, blank=True)
    health_status = models.CharField(max_length=20, default="unknown", choices=HEALTH_CHOICES)
    error_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    sync_interval_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Intervalo de sincronização em minutos (5-1440)",
    )
    conflict_strategy = models.CharField(
        max_length=20, default="last_write_wins", choices=CONFLICT_CHOICES
    )

    class Meta:
        db_table = "integration_connection"
        unique_together = ("org", "connector_slug")
        indexes = [
            models.Index(fields=["org", "connector_slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.connector_slug}) - {self.org}"


class SyncJob(BaseOrgModel):
    """Job de sincronização genérico."""

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]

    connector_slug = models.CharField(max_length=100, db_index=True)
    sync_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    total_records = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    progress_detail = models.JSONField(default=dict, blank=True)
    error_log = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sync_job"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["connector_slug", "status"]),
        ]

    def __str__(self):
        return f"SyncJob {self.sync_type} ({self.status}) - {self.connector_slug}"


class IntegrationLog(BaseOrgModel):
    """Log de operação de integração."""

    DIRECTION_CHOICES = [("in", "In"), ("out", "Out")]
    STATUS_CHOICES = [("success", "Success"), ("error", "Error")]

    connector_slug = models.CharField(max_length=100, db_index=True)
    operation = models.CharField(max_length=50)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_detail = models.TextField(blank=True, default="")
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "integration_log"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["connector_slug", "status"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.operation} {self.entity_type} ({self.status}) - {self.connector_slug}"


class WebhookLog(BaseOrgModel):
    """Log de webhook recebido."""

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("processed", "Processed"),
        ("failed", "Failed"),
        ("rejected", "Rejected"),
    ]

    connector_slug = models.CharField(max_length=100, db_index=True)
    event_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default="queued", choices=STATUS_CHOICES)
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)
    payload_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "webhook_log"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["connector_slug", "event_type"]),
        ]

    def __str__(self):
        return f"Webhook {self.event_type} ({self.status}) - {self.connector_slug}"


class FieldMapping(BaseOrgModel):
    """Mapeamento de campos configurável por org e conector."""

    FIELD_TYPE_CHOICES = [
        ("text", "Text"),
        ("number", "Number"),
        ("date", "Date"),
        ("select", "Select"),
        ("concat", "Concatenation"),
        ("split", "Split"),
        ("phone_format", "Phone Format"),
    ]

    connector_slug = models.CharField(max_length=100)
    source_field = models.CharField(max_length=255)
    target_field = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, default="text", choices=FIELD_TYPE_CHOICES)
    transform_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "field_mapping"
        unique_together = ("org", "connector_slug", "source_field")
        indexes = [
            models.Index(fields=["org", "connector_slug"]),
        ]

    def __str__(self):
        return f"{self.source_field} → {self.target_field} ({self.connector_slug})"


class ConflictLog(BaseOrgModel):
    """Log de conflitos de sincronização bidirecional."""

    RESOLVED_BY_CHOICES = [
        ("crm", "CRM"),
        ("external", "External"),
        ("last_write", "Last Write"),
    ]

    connector_slug = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=100)
    crm_value = models.JSONField()
    external_value = models.JSONField()
    resolved_by = models.CharField(max_length=20, choices=RESOLVED_BY_CHOICES)
    fields_overwritten = models.JSONField(default=list)

    class Meta:
        db_table = "conflict_log"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
        ]

    def __str__(self):
        return f"Conflict {self.entity_type}:{self.entity_id} → {self.resolved_by}"
