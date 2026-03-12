import jwt
from datetime import timedelta

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.permissions import HasOrgContext
from cowork.models import CoworkInvite, CoworkRoom
from cowork.serializers import (
    CoworkInviteCreateSerializer,
    CoworkInviteSerializer,
    CoworkRoomCreateSerializer,
    CoworkRoomSerializer,
)


class CoworkRoomListCreateView(ListCreateAPIView):
    """List all rooms for the org, or create a new room."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CoworkRoomCreateSerializer
        return CoworkRoomSerializer

    def get_queryset(self):
        return CoworkRoom.objects.filter(org=self.request.org, is_active=True)

    def perform_create(self, serializer):
        serializer.save(org=self.request.org)


class CoworkRoomDetailView(RetrieveUpdateDestroyAPIView):
    """Get, update, or deactivate a room."""

    serializer_class = CoworkRoomSerializer
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get_queryset(self):
        return CoworkRoom.objects.filter(org=self.request.org)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class CoworkInviteListCreateView(ListCreateAPIView):
    """List invites for a room, or create a new invite."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CoworkInviteCreateSerializer
        return CoworkInviteSerializer

    def get_queryset(self):
        room_id = self.kwargs["room_id"]
        return CoworkInvite.objects.filter(
            room_id=room_id, room__org=self.request.org
        ).select_related("room")

    def perform_create(self, serializer):
        room = CoworkRoom.objects.get(
            id=self.kwargs["room_id"], org=self.request.org
        )
        serializer.save(org=self.request.org, room=room)


class CoworkInviteRevokeView(APIView):
    """Revoke (deactivate) an invite."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def delete(self, request, pk):
        try:
            invite = CoworkInvite.objects.get(id=pk, org=request.org)
        except CoworkInvite.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        invite.is_active = False
        invite.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CoworkAuthTokenView(APIView):
    """Generate a cowork-scoped JWT for an authenticated CRM user."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request):
        room_id = request.data.get("room_id")
        if not room_id:
            return Response(
                {"error": "room_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            room = CoworkRoom.objects.get(
                id=room_id, org=request.org, is_active=True
            )
        except CoworkRoom.DoesNotExist:
            return Response(
                {"error": "Room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        now = timezone.now()
        payload = {
            "user_id": str(request.user.id),
            "org_id": str(request.org.id),
            "room_id": str(room.id),
            "display_name": request.user.email,
            "email": request.user.email,
            "is_guest": False,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=2)).timestamp()),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return Response({"token": token, "room": CoworkRoomSerializer(room).data})


class CoworkGuestJoinView(APIView):
    """
    Public endpoint: validate an invite token and return a guest JWT.
    Bypasses RLS via raw SQL (token IS the authentication).
    Rate-limited to 10 req/min per IP to prevent token brute-force.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "cowork_guest"

    def get(self, request, token):
        # Bypass RLS — lookup invite by token directly
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT ci.id, ci.guest_name, ci.guest_email, ci.expires_at,
                       ci.max_uses, ci.use_count, ci.is_active,
                       ci.room_id, ci.org_id,
                       cr.name as room_name, cr.map_id, cr.is_active as room_active
                FROM cowork_coworkinvite ci
                JOIN cowork_coworkroom cr ON cr.id = ci.room_id
                WHERE ci.token = %s
                LIMIT 1
                """,
                [token],
            )
            row = cursor.fetchone()

        if not row:
            return Response(
                {"error": "Invalid invite link"},
                status=status.HTTP_404_NOT_FOUND,
            )

        (
            invite_id, guest_name, guest_email, expires_at,
            max_uses, use_count, is_active,
            room_id, org_id, room_name, map_id, room_active,
        ) = row

        if not is_active:
            return Response(
                {"error": "This invite has been revoked"},
                status=status.HTTP_410_GONE,
            )
        if not room_active:
            return Response(
                {"error": "This room is no longer active"},
                status=status.HTTP_410_GONE,
            )
        if timezone.now() > expires_at:
            return Response(
                {"error": "This invite has expired"},
                status=status.HTTP_410_GONE,
            )
        if use_count >= max_uses:
            return Response(
                {"error": "This invite has reached its usage limit"},
                status=status.HTTP_410_GONE,
            )

        # Increment use count (raw SQL to bypass RLS)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE cowork_coworkinvite SET use_count = use_count + 1 WHERE id = %s",
                [str(invite_id)],
            )

        # Generate guest JWT
        now = timezone.now()
        payload = {
            "user_id": f"guest_{token[:12]}",
            "org_id": str(org_id),
            "room_id": str(room_id),
            "display_name": guest_name,
            "email": guest_email or "",
            "is_guest": True,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=30)).timestamp()),
        }
        guest_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        return Response({
            "token": guest_token,
            "room": {
                "id": str(room_id),
                "name": room_name,
                "map_id": map_id,
            },
            "guest": {
                "name": guest_name,
                "email": guest_email or "",
            },
        })
