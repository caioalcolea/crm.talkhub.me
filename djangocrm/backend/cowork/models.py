import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.base import BaseOrgModel


class CoworkRoom(BaseOrgModel):
    """Virtual coworking room for an organization."""

    name = models.CharField(max_length=200)
    map_id = models.CharField(
        max_length=50,
        default="office_default",
        help_text="Predefined map template identifier",
    )
    is_active = models.BooleanField(default=True)
    max_participants = models.IntegerField(default=25)
    settings_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Room configuration (Agora, custom tiles, etc.)",
    )

    class Meta(BaseOrgModel.Meta):
        verbose_name = "Cowork Room"
        verbose_name_plural = "Cowork Rooms"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class CoworkInvite(BaseOrgModel):
    """Guest invite link for a cowork room."""

    room = models.ForeignKey(
        CoworkRoom,
        on_delete=models.CASCADE,
        related_name="invites",
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        db_index=True,
        help_text="Unique invite token. Auto-generated.",
    )
    guest_name = models.CharField(max_length=200)
    guest_email = models.EmailField(blank=True, default="")
    expires_at = models.DateTimeField()
    max_uses = models.IntegerField(default=1)
    use_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta(BaseOrgModel.Meta):
        verbose_name = "Cowork Invite"
        verbose_name_plural = "Cowork Invites"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite for {self.guest_name} → {self.room.name}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return (
            self.is_active
            and self.use_count < self.max_uses
            and self.expires_at > timezone.now()
        )
