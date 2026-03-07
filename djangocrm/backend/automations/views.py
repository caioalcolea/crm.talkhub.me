"""
Views do app automations.

- AutomationListCreateView: GET (listar) / POST (criar) automações.
- AutomationDetailView: GET / PATCH / DELETE automação individual.
- AutomationLogListView: GET logs de uma automação.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext

from automations.models import Automation, AutomationLog
from automations.serializers import (
    AutomationLogSerializer,
    AutomationSerializer,
    AutomationWriteSerializer,
)


class AutomationListCreateView(APIView):
    """Listar e criar automações da organização."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        qs = Automation.objects.for_org(request.org)

        # Filtros opcionais
        automation_type = request.query_params.get("type")
        if automation_type:
            qs = qs.filter(automation_type=automation_type)

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        serializer = AutomationSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AutomationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(org=request.org)
        return Response(
            AutomationSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )


class AutomationDetailView(APIView):
    """Detalhe, atualização e exclusão de automação."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def _get_automation(self, request, pk):
        try:
            return Automation.objects.for_org(request.org).get(pk=pk)
        except Automation.DoesNotExist:
            return None

    def get(self, request, pk):
        automation = self._get_automation(request, pk)
        if not automation:
            return Response(
                {"error": "Automação não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(AutomationSerializer(automation).data)

    def patch(self, request, pk):
        automation = self._get_automation(request, pk)
        if not automation:
            return Response(
                {"error": "Automação não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = AutomationWriteSerializer(
            automation, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AutomationSerializer(serializer.instance).data)

    def delete(self, request, pk):
        automation = self._get_automation(request, pk)
        if not automation:
            return Response(
                {"error": "Automação não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        automation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AutomationLogListView(APIView):
    """Listar logs de execução de uma automação."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request, pk):
        # Verificar que a automação pertence à org
        if not Automation.objects.for_org(request.org).filter(pk=pk).exists():
            return Response(
                {"error": "Automação não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = AutomationLog.objects.filter(
            automation_id=pk, org=request.org
        ).order_by("-created_at")

        # Filtro por status
        log_status = request.query_params.get("status")
        if log_status:
            qs = qs.filter(status=log_status)

        # Paginação simples
        limit = min(int(request.query_params.get("limit", 50)), 200)
        offset = int(request.query_params.get("offset", 0))
        total = qs.count()

        serializer = AutomationLogSerializer(qs[offset : offset + limit], many=True)
        return Response(
            {
                "results": serializer.data,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )
