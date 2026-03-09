"""
Invitation Views — Sistema de convite por email para novos usuários.

Endpoints:
- GET  /api/invitations/          — Lista convites pendentes da org
- POST /api/invitations/          — Cria convite (vincula direto se email já registrado)
- DELETE /api/invitations/<id>/   — Cancela convite (status → cancelled)

Endpoint público (sem JWT):
- GET /invite/accept/<token>/     — Valida token e redireciona para registro
"""

import logging

from django.conf import settings
from django.db import connection
from django.shortcuts import redirect
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Org, PendingInvitation, Profile, User
from common.permissions import HasOrgContext, IsOrgAdmin
from common.serializers import (
    PendingInvitationCreateSerializer,
    PendingInvitationSerializer,
)

logger = logging.getLogger(__name__)


def _set_rls_context(org_id):
    """Set RLS context so org-scoped INSERTs (e.g. Profile) are allowed."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_org', %s, false)",
            [str(org_id)],
        )


class InvitationListCreateView(APIView):
    """
    GET  — Lista convites pendentes da org.
    POST — Cria convite. Se email já registrado, vincula direto à org.
    """

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request, *args, **kwargs):
        invitations = PendingInvitation.objects.filter(
            org=request.profile.org,
            status="pending",
        ).select_related("invited_by").order_by("-created_at")

        serializer = PendingInvitationSerializer(invitations, many=True)
        return Response({"invitations": serializer.data})

    def post(self, request, *args, **kwargs):
        serializer = PendingInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]
        org = request.profile.org

        # Check if user already has a profile in this org
        existing_profile = Profile.objects.filter(
            user__email=email, org=org
        ).first()
        if existing_profile:
            if existing_profile.is_active:
                return Response(
                    {"error": "Este usuário já faz parte da organização."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Reactivate inactive profile
            existing_profile.is_active = True
            existing_profile.role = role
            existing_profile.save(update_fields=["is_active", "role", "updated_at"])
            return Response(
                {"message": "Usuário reativado na organização.", "linked": True},
                status=status.HTTP_200_OK,
            )

        # Check if user exists in the platform but not in this org
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            # Link user directly — create profile
            Profile.objects.create(
                user=existing_user,
                org=org,
                role=role,
                is_organization_admin=(role == "ADMIN"),
                is_active=True,
                created_by=request.user,
            )
            return Response(
                {"message": "Usuário vinculado à organização.", "linked": True},
                status=status.HTTP_201_CREATED,
            )

        # Check for existing pending invitation
        existing_invite = PendingInvitation.objects.filter(
            org=org, email=email, status="pending"
        ).first()
        if existing_invite:
            return Response(
                {"error": "Já existe um convite pendente para este email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create new invitation
        invitation = PendingInvitation.objects.create(
            email=email,
            role=role,
            invited_by=request.user,
            org=org,
            created_by=request.user,
        )

        # Send invitation email asynchronously
        from common.tasks import send_invitation_email

        send_invitation_email.delay(str(invitation.id))

        result = PendingInvitationSerializer(invitation).data
        return Response(
            {"invitation": result, "linked": False},
            status=status.HTTP_201_CREATED,
        )


class InvitationCancelView(APIView):
    """DELETE — Cancela convite pendente."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def delete(self, request, pk, *args, **kwargs):
        try:
            invitation = PendingInvitation.objects.get(
                id=pk,
                org=request.profile.org,
                status="pending",
            )
        except PendingInvitation.DoesNotExist:
            return Response(
                {"error": "Convite não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        invitation.status = "cancelled"
        invitation.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationResendView(APIView):
    """POST — Reenvia email de convite pendente."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def post(self, request, pk, *args, **kwargs):
        try:
            invitation = PendingInvitation.objects.get(
                id=pk,
                org=request.profile.org,
                status="pending",
            )
        except PendingInvitation.DoesNotExist:
            return Response(
                {"error": "Convite não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if expired, refresh if so
        if invitation.expires_at < timezone.now():
            from datetime import timedelta

            invitation.expires_at = timezone.now() + timedelta(days=7)
            invitation.save(update_fields=["expires_at", "updated_at"])

        from common.tasks import send_invitation_email

        send_invitation_email.delay(str(invitation.id))

        return Response({"message": "Email de convite reenviado."})


class InvitationAcceptView(APIView):
    """
    GET /invite/accept/<token>/ — Endpoint público (sem JWT).
    Valida token, verifica expiração, redireciona para registro.

    NOTE: pending_invitation has RLS DISABLED (migration 0003),
    so ORM queries work without org context.
    """

    permission_classes = (AllowAny,)
    authentication_classes = []

    def get(self, request, token, *args, **kwargs):
        try:
            invitation = PendingInvitation.objects.select_related("org").get(
                token=token
            )
        except PendingInvitation.DoesNotExist:
            return redirect(
                f"{settings.FRONTEND_URL}/login?error=invite_not_found"
            )

        if invitation.status == "accepted":
            return redirect(
                f"{settings.FRONTEND_URL}/login?info=invite_already_accepted"
            )

        if invitation.status in ("expired", "cancelled"):
            return redirect(
                f"{settings.FRONTEND_URL}/login?error=invite_expired"
            )

        if invitation.expires_at < timezone.now():
            invitation.status = "expired"
            invitation.save(update_fields=["status", "updated_at"])
            return redirect(
                f"{settings.FRONTEND_URL}/login?error=invite_expired"
            )

        # Redirect to login page with invite token
        # After login/registration, the frontend will call accept-invite API
        return redirect(
            f"{settings.FRONTEND_URL}/login"
            f"?invite={token}"
        )


class InvitationAcceptAPIView(APIView):
    """
    POST /api/auth/accept-invite/ — Aceita convite após autenticação.

    Recebe {token}, valida, cria Profile na org do convite,
    e retorna org_id para o frontend fazer switch-org.

    NOTE: pending_invitation has RLS DISABLED (migration 0003).
    Profile creation requires setting RLS context first.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        token = request.data.get("token")
        if not token:
            return Response(
                {"error": "Token é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            invitation = PendingInvitation.objects.select_related("org").get(
                token=token
            )
        except PendingInvitation.DoesNotExist:
            return Response(
                {"error": "Convite não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if invitation.status != "pending":
            return Response(
                {"error": f"Convite já foi {invitation.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invitation.expires_at < timezone.now():
            invitation.status = "expired"
            invitation.save(update_fields=["status", "updated_at"])
            return Response(
                {"error": "Convite expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify email matches
        if request.user.email.lower() != invitation.email.lower():
            return Response(
                {"error": "Este convite foi enviado para outro email."},
                status=status.HTTP_403_FORBIDDEN,
            )

        org = invitation.org

        # Set RLS context for profile operations on this org
        _set_rls_context(org.id)

        # Check if user already has a profile in this org
        existing_profile = Profile.objects.filter(
            user=request.user, org=org
        ).first()

        if existing_profile:
            if existing_profile.is_active:
                # Already a member, just mark invite as accepted
                invitation.status = "accepted"
                invitation.accepted_at = timezone.now()
                invitation.save(update_fields=["status", "accepted_at", "updated_at"])
                return Response({
                    "message": "Você já faz parte desta organização.",
                    "org_id": str(org.id),
                    "org_name": org.name,
                })
            # Reactivate inactive profile
            existing_profile.is_active = True
            existing_profile.role = invitation.role
            existing_profile.save(update_fields=["is_active", "role", "updated_at"])
        else:
            # Create new profile in the org
            Profile.objects.create(
                user=request.user,
                org=org,
                role=invitation.role,
                is_organization_admin=(invitation.role == "ADMIN"),
                is_active=True,
                created_by=invitation.invited_by,
            )

        # Mark invitation as accepted
        invitation.status = "accepted"
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_at", "updated_at"])

        logger.info(
            "Invitation accepted: user=%s org=%s role=%s",
            request.user.email, org.name, invitation.role,
        )

        return Response({
            "message": "Convite aceito com sucesso.",
            "org_id": str(org.id),
            "org_name": org.name,
        })
