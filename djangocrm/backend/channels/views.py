"""
Views do app channels.

- ChannelConfigListView: CRUD de configuração de canais.
- ChannelAvailableView: Listar provedores disponíveis.
- ChannelTestView: Testar conexão de canal.
- ChannelForActionView: Canais disponíveis para ação específica.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from channels.models import ChannelConfig
from channels.registry import ChannelRegistry
from channels.serializers import (
    ChannelConfigSerializer,
    ChannelForActionSerializer,
    ChannelProviderSerializer,
)
from common.permissions import HasOrgContext, IsOrgAdmin


class ChannelConfigListView(APIView):
    """GET/POST /api/channels/ — CRUD de canais configurados."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        queryset = ChannelConfig.objects.filter(org=request.org)
        serializer = ChannelConfigSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        self.permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)
        self.check_permissions(request)

        serializer = ChannelConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(org=request.org)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChannelConfigDetailView(APIView):
    """PATCH/DELETE /api/channels/<id>/ — Atualizar/remover canal."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def _get_object(self, request, pk):
        try:
            return ChannelConfig.objects.get(id=pk, org=request.org)
        except ChannelConfig.DoesNotExist:
            return None

    def patch(self, request, pk):
        obj = self._get_object(request, pk)
        if not obj:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChannelConfigSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get_object(request, pk)
        if not obj:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChannelAvailableView(APIView):
    """GET /api/channels/available/ — Listar provedores disponíveis."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        providers = ChannelRegistry.all()
        result = []
        for channel_type, provider_cls in providers.items():
            provider = provider_cls()
            result.append({
                "channel_type": channel_type,
                "name": provider_cls.name,
                "icon": getattr(provider_cls, "icon", ""),
                "capabilities": [c.value for c in provider.get_capabilities()],
                "config_schema": provider.get_config_schema(),
            })
        serializer = ChannelProviderSerializer(result, many=True)
        return Response(serializer.data)


class ChannelTestView(APIView):
    """POST /api/channels/<id>/test/ — Testar conexão de canal."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def post(self, request, pk):
        try:
            channel_config = ChannelConfig.objects.get(id=pk, org=request.org)
        except ChannelConfig.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        provider_cls = ChannelRegistry.get(channel_config.channel_type)
        if not provider_cls:
            return Response(
                {"error": "Provider not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider = provider_cls()
        try:
            result = provider.get_status(channel_config)
            return Response({"status": "ok", "details": result})
        except Exception as e:
            return Response(
                {"status": "error", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ChannelForActionView(APIView):
    """GET /api/channels/for-action/<action>/ — Canais disponíveis para ação."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request, action):
        from channels.base import MessageCapability

        # Mapear ação para capability
        action_capability_map = {
            "send_text": MessageCapability.TEXT,
            "send_email": MessageCapability.EMAIL,
            "send_sms": MessageCapability.SMS,
            "send_image": MessageCapability.IMAGE,
            "send_file": MessageCapability.FILE,
            "send_template": MessageCapability.TEMPLATE,
            "send_broadcast": MessageCapability.BROADCAST,
        }

        capability = action_capability_map.get(action)
        if not capability:
            return Response(
                {"error": f"Unknown action: {action}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Obter provedores que suportam a capability
        provider_classes = ChannelRegistry.get_for_capability(capability)
        provider_types = {
            p.channel_type.value if hasattr(p.channel_type, "value") else str(p.channel_type)
            for p in [cls() for cls in provider_classes]
        }

        # Filtrar canais configurados e ativos da org
        channels = ChannelConfig.objects.filter(
            org=request.org, is_active=True, channel_type__in=provider_types
        )

        result = []
        for ch in channels:
            provider_cls = ChannelRegistry.get(ch.channel_type)
            result.append({
                "channel_type": ch.channel_type,
                "provider_name": provider_cls.name if provider_cls else ch.provider,
                "display_name": ch.display_name,
                "is_active": ch.is_active,
            })

        serializer = ChannelForActionSerializer(result, many=True)
        return Response(serializer.data)
