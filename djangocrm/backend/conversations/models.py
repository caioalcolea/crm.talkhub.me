"""
Modelos do módulo de conversas.

Conversation e Message são genéricos e independentes de integração.
Qualquer ChannelProvider pode criar conversas e mensagens.
"""

from django.contrib.postgres.indexes import GinIndex
from django.db import models

from common.base import BaseOrgModel


class Conversation(BaseOrgModel):
    """Conversa entre CRM e contato. Genérica, independente de integração."""

    STATUS_CHOICES = [
        ("open", "Aberta"),
        ("pending", "Pendente"),
        ("resolved", "Concluída"),
    ]

    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    channel = models.CharField(max_length=50)
    integration_provider = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    assigned_to = models.ForeignKey(
        "common.Profile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_conversations",
    )
    last_message_at = models.DateTimeField(null=True, blank=True)
    omni_user_ns = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    tags = models.ManyToManyField("common.Tags", related_name="conversation_tags", blank=True)

    class Meta:
        db_table = "conversation"
        ordering = ("-last_message_at",)
        indexes = [
            models.Index(fields=["org", "-last_message_at"]),
            models.Index(fields=["org", "status"]),
            models.Index(fields=["org", "channel"]),
            models.Index(fields=["contact"]),
            models.Index(fields=["omni_user_ns"]),
            GinIndex(fields=["metadata_json"], name="conv_metadata_gin"),
            models.Index(fields=["org", "assigned_to"], name="conv_org_assigned"),
            models.Index(fields=["org", "-updated_at"], name="conv_org_updated"),
        ]

    def __str__(self):
        return f"Conversation {self.channel} - {self.contact} ({self.status})"


class Message(BaseOrgModel):
    """Mensagem individual dentro de uma conversa."""

    DIRECTION_CHOICES = [
        ("in", "Entrada"),
        ("out", "Saída"),
        ("agent", "Agente"),
        ("note", "Nota"),
        ("system", "Sistema"),
    ]
    MSG_TYPE_CHOICES = [
        ("text", "Texto"),
        ("image", "Imagem"),
        ("video", "Vídeo"),
        ("audio", "Áudio"),
        ("file", "Arquivo"),
        ("payload", "Payload Estruturado"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    msg_type = models.CharField(max_length=20, choices=MSG_TYPE_CHOICES, default="text")
    content = models.TextField(blank=True, default="")
    media_url = models.URLField(max_length=1024, blank=True, null=True)
    sender_type = models.CharField(max_length=50, blank=True, default="")
    sender_name = models.CharField(max_length=255, blank=True, default="")
    sender_id = models.CharField(max_length=255, blank=True, default="")
    timestamp = models.DateTimeField()
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "message"
        ordering = ("timestamp",)
        indexes = [
            models.Index(fields=["conversation", "timestamp"]),
            models.Index(fields=["org", "-timestamp"]),
        ]

    def __str__(self):
        return f"Message {self.direction} ({self.msg_type}) - {self.conversation_id}"
