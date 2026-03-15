"""
Models do app campaigns.

- Campaign: Campanha de marketing (email_blast, nurture_sequence, whatsapp_broadcast).
- CampaignAudience: Segmento de audiência com critérios de filtro.
- CampaignRecipient: Destinatário individual vinculado a um Contact.
- CampaignStep: Etapa de nurture sequence com delay entre envios.
"""

from django.db import models

from common.base import BaseOrgModel


class Campaign(BaseOrgModel):
    """Campanha de marketing configurável por organização."""

    TYPE_CHOICES = [
        ("email_blast", "Email Blast"),
        ("nurture_sequence", "Nurture Sequence"),
        ("whatsapp_broadcast", "WhatsApp Broadcast"),
    ]

    STATUS_CHOICES = [
        ("draft", "Rascunho"),
        ("scheduled", "Agendada"),
        ("running", "Em Execução"),
        ("paused", "Pausada"),
        ("completed", "Concluída"),
        ("cancelled", "Cancelada"),
    ]

    name = models.CharField(max_length=255)
    campaign_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    subject = models.CharField(max_length=500, blank=True, null=True)
    body_template = models.TextField(blank=True, default="")

    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Counters
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    opened_count = models.PositiveIntegerField(default=0)
    clicked_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    bounce_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "campaign"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["campaign_type", "status"]),
            models.Index(fields=["status", "scheduled_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.campaign_type}) - {self.status}"


class CampaignAudience(BaseOrgModel):
    """Segmento de audiência com critérios de filtro JSON."""

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="audiences",
    )
    name = models.CharField(max_length=255)
    filter_criteria = models.JSONField(default=dict, blank=True)
    contact_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "campaign_audience"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["campaign"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.contact_count} contatos)"


class CampaignRecipient(BaseOrgModel):
    """Destinatário individual de campanha vinculado a um Contact."""

    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("sent", "Enviado"),
        ("delivered", "Entregue"),
        ("opened", "Aberto"),
        ("clicked", "Clicado"),
        ("bounced", "Bounce"),
        ("failed", "Falhou"),
        ("unsubscribed", "Descadastrado"),
    ]

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.CASCADE,
        related_name="campaign_recipients",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    error_detail = models.TextField(blank=True, default="")

    # Nurture sequence tracking
    current_step = models.PositiveIntegerField(default=0)

    # Link to ScheduledJob for unified execution tracking
    scheduled_job = models.ForeignKey(
        "assistant.ScheduledJob",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_recipients",
    )

    class Meta:
        db_table = "campaign_recipient"
        ordering = ("-created_at",)
        unique_together = [("campaign", "contact")]
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["contact"]),
        ]

    def __str__(self):
        return f"{self.contact} - {self.campaign.name} ({self.status})"


class CampaignStep(BaseOrgModel):
    """Etapa de nurture sequence com delay entre envios."""

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("whatsapp", "WhatsApp"),
    ]

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    step_order = models.PositiveIntegerField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="email")
    subject = models.CharField(max_length=500, blank=True, null=True)
    body_template = models.TextField(blank=True, default="")
    delay_hours = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "campaign_step"
        ordering = ("step_order",)
        unique_together = [("campaign", "step_order")]
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["campaign", "step_order"]),
        ]

    def __str__(self):
        return f"Step {self.step_order} - {self.campaign.name}"
