import logging
import time

import requests
from django.conf import settings
from rest_framework import serializers

from cowork.models import CoworkInvite, CoworkRoom

logger = logging.getLogger(__name__)

# Module-level cache for room counts from cowork-server (5s TTL)
_room_counts_cache = {"data": {}, "expires": 0}

COWORK_SERVER_URL = "http://crm_cowork_backend:3100"


def _get_room_counts():
    """Fetch room participant counts from the Socket.io cowork-server."""
    now = time.time()
    if now < _room_counts_cache["expires"]:
        return _room_counts_cache["data"]

    try:
        resp = requests.get(f"{COWORK_SERVER_URL}/rooms/status", timeout=2)
        if resp.status_code == 200:
            data = resp.json().get("rooms", {})
            _room_counts_cache["data"] = data
            _room_counts_cache["expires"] = now + 5
            return data
    except Exception:
        logger.debug("Failed to fetch room counts from cowork-server")

    return _room_counts_cache["data"]


class CoworkRoomSerializer(serializers.ModelSerializer):
    participant_count = serializers.SerializerMethodField()
    invite_count = serializers.SerializerMethodField()

    class Meta:
        model = CoworkRoom
        fields = [
            "id",
            "name",
            "map_id",
            "is_active",
            "max_participants",
            "settings_json",
            "participant_count",
            "invite_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_participant_count(self, obj):
        counts = _get_room_counts()
        return counts.get(str(obj.id), 0)

    def get_invite_count(self, obj):
        return obj.invites.filter(is_active=True).count()


class CoworkRoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoworkRoom
        fields = ["name", "map_id", "max_participants", "settings_json"]


class CoworkInviteSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source="room.name", read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    invite_url = serializers.SerializerMethodField()

    class Meta:
        model = CoworkInvite
        fields = [
            "id",
            "room",
            "room_name",
            "token",
            "guest_name",
            "guest_email",
            "expires_at",
            "max_uses",
            "use_count",
            "is_active",
            "is_valid",
            "invite_url",
            "created_at",
        ]
        read_only_fields = ["id", "token", "use_count", "created_at"]

    def get_invite_url(self, obj):
        return f"{settings.DOMAIN_NAME}/cowork/{obj.token}"


class CoworkInviteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoworkInvite
        fields = ["guest_name", "guest_email", "expires_at", "max_uses"]
