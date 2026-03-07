"""
TalkHub Omni integration models.

Stores per-org connection credentials, sync configuration, channel configs,
team member mappings, ticket list mappings, and statistics snapshots.
All models inherit BaseModel (UUID pk, audit fields) and are org-scoped for RLS.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.base import BaseModel, OrgScopedMixin
from common.models import Org, Profile


class TalkHubConnection(OrgScopedMixin, BaseModel):
    """One-to-one connection to TalkHub Omni per organization."""

    org = models.OneToOneField(
        Org,
        on_delete=models.CASCADE,
        related_name="talkhub_connection",
    )
    api_key = models.TextField(help_text="TalkHub Omni API Key (Bearer token)")
    workspace_url = models.URLField(
        default="https://chat.talkhub.me",
        help_text="TalkHub workspace base URL",
    )
    workspace_name = models.CharField(max_length=255, blank=True, default="")
    owner_email = models.EmailField(blank=True, default="")
    is_connected = models.BooleanField(default=False)
    connected_by = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True
    )
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "talkhub_connection"
        verbose_name = "TalkHub Connection"
        verbose_name_plural = "TalkHub Connections"

    def __str__(self):
        return f"TalkHub<{self.org}> {'connected' if self.is_connected else 'disconnected'}"


class TalkHubSyncJob(OrgScopedMixin, BaseModel):
    """
    Async synchronisation job (Celery task tracking).

    DEPRECATED: Para novas integrações, use integrations.models.SyncJob.
    Este modelo é mantido para compatibilidade com dados existentes do TalkHub Omni.
    Novas operações devem usar SyncJob genérico com connector_slug="talkhub-omni".
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]
    SYNC_TYPE_CHOICES = [
        ("contacts", "Contacts"),
        ("tickets", "Tickets"),
        ("tags", "Tags"),
        ("team_members", "Team Members"),
        ("statistics", "Statistics"),
        ("conversations", "Conversations"),
        ("all", "All"),
    ]

    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="talkhub_sync_jobs"
    )
    sync_type = models.CharField(max_length=50, choices=SYNC_TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="PENDING"
    )
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
        db_table = "talkhub_sync_job"
        verbose_name = "TalkHub Sync Job"
        verbose_name_plural = "TalkHub Sync Jobs"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"SyncJob<{self.sync_type}|{self.status}>"


class TalkHubFieldMapping(OrgScopedMixin, BaseModel):
    """
    Dynamic field mapping: TalkHub custom var → CRM field.

    DEPRECATED: Para novas integrações, use integrations.models.FieldMapping.
    Este modelo é mantido para compatibilidade com dados existentes.
    O variable_registry.py é a fonte canônica de mapeamentos.
    """

    FIELD_TYPE_CHOICES = [
        ("text", "Text"),
        ("number", "Number"),
        ("date", "Date"),
        ("select", "Select"),
    ]

    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="talkhub_field_mappings"
    )
    talkhub_var_ns = models.CharField(
        max_length=255, help_text="TalkHub variable namespace (e.g. user_field_ns)"
    )
    talkhub_field_name = models.CharField(max_length=255)
    crm_field_key = models.CharField(
        max_length=255, help_text="Target CRM field key"
    )
    field_type = models.CharField(
        max_length=50, choices=FIELD_TYPE_CHOICES, default="text"
    )

    class Meta:
        db_table = "talkhub_field_mapping"
        verbose_name = "TalkHub Field Mapping"
        verbose_name_plural = "TalkHub Field Mappings"
        unique_together = ("org", "talkhub_var_ns")
        indexes = [
            models.Index(fields=["org", "talkhub_var_ns"]),
        ]

    def __str__(self):
        return f"{self.talkhub_field_name} → {self.crm_field_key}"


# ─── NEW MODELS (Phase 6 Refactoring) ────────────────────────────────────────


class TalkHubOmniChannel(OrgScopedMixin, BaseModel):
    """
    Per-org channel configuration for TalkHub Omni.
    Each channel type (WhatsApp, Instagram, etc.) can have its own API key.
    """

    CHANNEL_TYPE_CHOICES = [
        ("whatsapp_cloud", "WhatsApp Cloud"),
        ("whatsapp_groups", "WhatsApp Groups"),
        ("instagram", "Instagram / Facebook"),
        ("telegram", "Telegram"),
        ("sms", "SMS"),
        ("webchat", "Web Chat"),
        ("email", "Email"),
    ]

    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="talkhub_omni_channels"
    )
    channel_type = models.CharField(max_length=50, choices=CHANNEL_TYPE_CHOICES)
    api_key = models.TextField(
        blank=True, default="",
        help_text="API key específica deste canal (se diferente da conexão principal)",
    )
    is_active = models.BooleanField(default=True)
    is_connected = models.BooleanField(default=False)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    display_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "talkhub_omni_channel"
        verbose_name = "TalkHub Omni Channel"
        verbose_name_plural = "TalkHub Omni Channels"
        unique_together = ("org", "channel_type")
        indexes = [
            models.Index(fields=["org", "is_active"]),
        ]

    def __str__(self):
        return f"{self.get_channel_type_display()} ({self.org})"


class TalkHubSyncConfig(OrgScopedMixin, BaseModel):
    """
    Per-org sync configuration — controls which modules sync and at what intervals.
    """

    org = models.OneToOneField(
        Org, on_delete=models.CASCADE, related_name="talkhub_sync_config"
    )
    sync_enabled = models.BooleanField(default=True)

    # Module toggles
    sync_contacts = models.BooleanField(default=True)
    sync_tickets = models.BooleanField(default=True)
    sync_tags = models.BooleanField(default=True)
    sync_team_members = models.BooleanField(default=True)
    sync_statistics = models.BooleanField(default=True)
    sync_conversations = models.BooleanField(default=True)

    # Intervals (in minutes)
    contacts_interval_minutes = models.PositiveIntegerField(
        default=5, help_text="Intervalo de sync de contatos (minutos)"
    )
    tickets_interval_minutes = models.PositiveIntegerField(
        default=10, help_text="Intervalo de sync de tickets (minutos)"
    )
    statistics_interval_minutes = models.PositiveIntegerField(
        default=60, help_text="Intervalo de sync de estatísticas (minutos)"
    )

    class Meta:
        db_table = "talkhub_sync_config"
        verbose_name = "TalkHub Sync Config"
        verbose_name_plural = "TalkHub Sync Configs"

    def __str__(self):
        return f"SyncConfig<{self.org}> {'enabled' if self.sync_enabled else 'disabled'}"


class TalkHubTeamMember(OrgScopedMixin, BaseModel):
    """
    Mirror of TalkHub Omni team members.
    Sync is additive — members are never deleted from CRM.
    """

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("agent", "Agent"),
        ("viewer", "Viewer"),
    ]

    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="talkhub_team_members"
    )
    omni_agent_id = models.CharField(
        max_length=255, help_text="TalkHub Omni agent/member ID"
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    image = models.URLField(blank=True, default="")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="agent")
    is_online = models.BooleanField(default=False)
    crm_profile = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="talkhub_team_member",
        help_text="Perfil CRM vinculado a este membro",
    )

    class Meta:
        db_table = "talkhub_team_member"
        verbose_name = "TalkHub Team Member"
        verbose_name_plural = "TalkHub Team Members"
        unique_together = ("org", "omni_agent_id")
        indexes = [
            models.Index(fields=["org", "is_online"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.role})"


class TalkHubTicketListMapping(OrgScopedMixin, BaseModel):
    """
    Maps a TalkHub Omni ticket list to a CRM pipeline (Lead or Case).
    Determines whether tickets from this list become Leads or Cases.
    """

    PIPELINE_TYPE_CHOICES = [
        ("lead", "Funil de Vendas (Lead Pipeline)"),
        ("case", "Suporte (Case Pipeline)"),
    ]

    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="talkhub_ticket_list_mappings"
    )
    omni_list_id = models.CharField(
        max_length=255, help_text="TalkHub Omni ticket list ID"
    )
    omni_list_name = models.CharField(max_length=255, blank=True, default="")
    pipeline_type = models.CharField(
        max_length=10, choices=PIPELINE_TYPE_CHOICES, default="lead"
    )
    lead_pipeline = models.ForeignKey(
        "leads.LeadPipeline",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="talkhub_ticket_list_mappings",
        help_text="Pipeline de leads destino (quando pipeline_type='lead')",
    )
    case_pipeline = models.ForeignKey(
        "cases.CasePipeline",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="talkhub_ticket_list_mappings",
        help_text="Pipeline de cases destino (quando pipeline_type='case')",
    )

    class Meta:
        db_table = "talkhub_ticket_list_mapping"
        verbose_name = "TalkHub Ticket List Mapping"
        verbose_name_plural = "TalkHub Ticket List Mappings"
        unique_together = ("org", "omni_list_id")
        indexes = [
            models.Index(fields=["org", "pipeline_type"]),
        ]

    def __str__(self):
        return f"{self.omni_list_name} → {self.get_pipeline_type_display()}"


class OmniStatisticsSnapshot(OrgScopedMixin, BaseModel):
    """
    Periodic snapshot of TalkHub Omni statistics/metrics.
    Stored for historical analysis and dashboard display.
    """

    PERIOD_CHOICES = [
        ("hourly", "Hourly"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="omni_statistics_snapshots"
    )
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="hourly")
    bot_users_count = models.IntegerField(default=0)
    messages_count = models.IntegerField(default=0)
    avg_response_time_seconds = models.FloatField(default=0.0)
    resolution_rate = models.FloatField(
        default=0.0, help_text="Taxa de resolução (0.0 a 1.0)"
    )
    agents_online = models.IntegerField(default=0)
    agent_productivity = models.JSONField(
        default=dict, blank=True,
        help_text="Produtividade por agente: {agent_id: {messages, avg_time, ...}}",
    )
    raw_data = models.JSONField(
        default=dict, blank=True,
        help_text="Dados brutos consolidados das APIs de métricas",
    )

    class Meta:
        db_table = "omni_statistics_snapshot"
        verbose_name = "Omni Statistics Snapshot"
        verbose_name_plural = "Omni Statistics Snapshots"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["org", "period"]),
        ]

    def __str__(self):
        return f"Stats<{self.org}|{self.period}|{self.created_at}>"
