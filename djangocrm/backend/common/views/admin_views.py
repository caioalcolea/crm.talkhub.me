"""
Platform Administration API — Super Admin only.

Provides endpoints for managing organizations, users, and system health
across the entire platform. All endpoints require IsSuperAdmin permission.
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Org, Profile
from common.permissions import IsSuperAdmin

User = get_user_model()


class AdminDashboardView(APIView):
    """GET /api/admin/dashboard/ — platform-wide KPIs."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        orgs = Org.objects.filter(is_active=True)
        total_orgs = orgs.count()
        total_users = User.objects.filter(is_active=True).count()
        total_profiles = Profile.objects.filter(is_active=True).count()
        new_orgs_this_month = orgs.filter(created_at__gte=month_start).count()
        new_users_this_month = User.objects.filter(
            is_active=True, date_joined__gte=month_start
        ).count()

        return Response({
            "total_orgs": total_orgs,
            "total_users": total_users,
            "total_profiles": total_profiles,
            "new_orgs_this_month": new_orgs_this_month,
            "new_users_this_month": new_users_this_month,
            "server_time": now.isoformat(),
        })


class AdminOrgListView(APIView):
    """GET /api/admin/orgs/ — list all organizations with stats."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        orgs = Org.objects.filter(is_active=True).annotate(
            user_count=Count("profiles", filter=Q(profiles__is_active=True)),
        ).order_by("-created_at")

        search = request.query_params.get("search", "").strip()
        if search:
            orgs = orgs.filter(name__icontains=search)

        data = []
        for org in orgs:
            data.append({
                "id": str(org.id),
                "name": org.name,
                "user_count": org.user_count,
                "is_active": org.is_active,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "default_currency": getattr(org, "default_currency", "BRL"),
            })

        return Response({"orgs": data, "count": len(data)})


class AdminOrgDetailView(APIView):
    """GET/PATCH /api/admin/orgs/<pk>/ — org detail + update."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, pk):
        try:
            org = Org.objects.get(id=pk)
        except Org.DoesNotExist:
            return Response({"error": "Org not found"}, status=404)

        profiles = Profile.objects.filter(org=org, is_active=True).select_related("user")
        users_data = []
        for p in profiles:
            users_data.append({
                "id": str(p.id),
                "email": p.user.email,
                "role": p.role,
                "is_organization_admin": p.is_organization_admin,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        return Response({
            "id": str(org.id),
            "name": org.name,
            "is_active": org.is_active,
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "default_currency": getattr(org, "default_currency", "BRL"),
            "users": users_data,
        })

    def patch(self, request, pk):
        try:
            org = Org.objects.get(id=pk)
        except Org.DoesNotExist:
            return Response({"error": "Org not found"}, status=404)

        if "name" in request.data:
            org.name = request.data["name"]
        if "is_active" in request.data:
            org.is_active = request.data["is_active"]

        org.save()
        return Response({"message": "Organização atualizada com sucesso."})


class AdminUserListView(APIView):
    """GET /api/admin/users/ — list all platform users."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        users = User.objects.filter(is_active=True).order_by("-date_joined")

        search = request.query_params.get("search", "").strip()
        if search:
            users = users.filter(email__icontains=search)

        data = []
        for user in users[:200]:
            orgs = Profile.objects.filter(user=user, is_active=True).select_related("org")
            data.append({
                "id": str(user.id),
                "email": user.email,
                "is_superuser": user.is_superuser,
                "is_active": user.is_active,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "orgs": [
                    {"id": str(p.org.id), "name": p.org.name, "role": p.role}
                    for p in orgs
                ],
            })

        return Response({"users": data, "count": len(data)})


class AdminUserDetailView(APIView):
    """PATCH /api/admin/users/<pk>/ — toggle superuser, deactivate."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def patch(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        if "is_superuser" in request.data:
            user.is_superuser = request.data["is_superuser"]
        if "is_active" in request.data:
            user.is_active = request.data["is_active"]

        user.save()
        return Response({"message": "Usuário atualizado com sucesso."})
