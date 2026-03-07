from django.db import models

from common.base import BaseOrgModel


class ChannelConfig(BaseOrgModel):
    """Configuração de canal de comunicação por org."""

    CHANNEL_TYPE_CHOICES = [
        ("talkhub_omni", "TalkHub Omni"),
        ("smtp_native", "SMTP Nativo"),
        ("chatwoot", "Chatwoot"),
        ("evolution_api", "Evolution API"),
        ("whatsapp_direct", "WhatsApp Direto"),
        ("tiktok", "TikTok"),
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("email", "Email"),
        ("webchat", "Web Chat"),
    ]

    channel_type = models.CharField(max_length=50, choices=CHANNEL_TYPE_CHOICES)
    provider = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    capabilities_json = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "channel_config"
        indexes = [
            models.Index(fields=["org", "channel_type"]),
            models.Index(fields=["org", "is_active"]),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.channel_type}) - {self.org}"
