from rest_framework import serializers

from cowork.models import CoworkInvite, CoworkRoom


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
        # Will be populated from Socket.io server state in the future
        return 0

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
        request = self.context.get("request")
        if request:
            return f"{request.scheme}://{request.get_host()}/cowork/{obj.token}"
        return f"/cowork/{obj.token}"


class CoworkInviteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoworkInvite
        fields = ["guest_name", "guest_email", "expires_at", "max_uses"]
