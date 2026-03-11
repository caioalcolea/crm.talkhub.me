"""
Views do app integrations.

- webhook_receiver: Endpoint genérico de webhook (AllowAny).
- IntegrationViewSet: CRUD + ações de integração (Admin only).
- IntegrationLogViewSet: Logs filtráveis (Admin only).
- FieldMappingViewSet: CRUD de mapeamento de campos (Admin only).
"""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext, IsOrgAdmin
from integrations.models import (
    ConflictLog,
    FieldMapping,
    IntegrationConnection,
    IntegrationLog,
    OrgFeatureFlag,
    SyncJob,
    WebhookLog,
)
from integrations.registry import ConnectorRegistry
from integrations.serializers import (
    ConflictLogSerializer,
    FieldMappingSerializer,
    IntegrationConnectionConfigSerializer,
    IntegrationConnectionSerializer,
    IntegrationLogSerializer,
    OrgFeatureFlagSerializer,
    SyncJobSerializer,
    WebhookLogSerializer,
)
from integrations.tasks import process_webhook, run_connector_sync

logger = logging.getLogger(__name__)


def _validate_config_against_schema(config: dict, schema: dict) -> list[str]:
    """Valida config_json contra config_schema do conector. Retorna lista de erros."""
    errors = []
    required_fields = set(schema.get("required", []))
    field_defs = {f["name"]: f for f in schema.get("fields", [])}

    for field_name in required_fields:
        value = config.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            label = field_defs.get(field_name, {}).get("label", field_name)
            errors.append(f"Campo obrigatório ausente: {label}")

    return errors


def _encrypt_secret_fields(config: dict, schema: dict) -> dict:
    """Criptografa campos marcados como secret no config_schema com Fernet."""
    from cryptography.fernet import Fernet
    from django.conf import settings

    secret_fields = set()
    for field_def in schema.get("fields", []):
        if field_def.get("secret") or field_def.get("type") == "password":
            secret_fields.add(field_def.get("name"))

    if not secret_fields:
        return config

    fernet_key = getattr(settings, "FERNET_KEY", None)
    if not fernet_key:
        return config

    f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
    encrypted = dict(config)
    for field_name in secret_fields:
        value = encrypted.get(field_name)
        if value and isinstance(value, str) and not value.startswith("gAAAAA"):
            encrypted[field_name] = f.encrypt(value.encode()).decode()

    return encrypted


def _auto_create_channel_config(org, connector_slug, config):
    """Auto-create a ChannelConfig when a connector that maps to a channel connects."""
    from channels.models import ChannelConfig

    # Map connector slugs to channel types
    CONNECTOR_CHANNEL_MAP = {
        "smtp": ("smtp_native", "Email (SMTP)"),
        "chatwoot": ("chatwoot", "Chatwoot"),
    }

    mapping = CONNECTOR_CHANNEL_MAP.get(connector_slug)
    if not mapping:
        return

    channel_type, display_name = mapping

    # Build channel-specific config
    if connector_slug == "chatwoot":
        channel_config = {
            "chatwoot_url": config.get("chatwoot_url", ""),
            "account_id": config.get("account_id", ""),
        }
        capabilities = ["text", "image", "file"]
    else:
        channel_config = {
            "from_email": config.get("from_email", ""),
            "reply_to": config.get("reply_to", ""),
        }
        capabilities = ["text", "email", "file"]

    ChannelConfig.objects.update_or_create(
        org=org,
        channel_type=channel_type,
        defaults={
            "provider": connector_slug,
            "display_name": display_name,
            "config_json": channel_config,
            "is_active": True,
            "capabilities_json": capabilities,
        },
    )


def _check_feature_enabled(org, connector_slug):
    """Verifica se a feature flag está habilitada para o conector. Retorna None se OK, ou Response 403."""
    flag = OrgFeatureFlag.objects.filter(
        org=org, feature_key=connector_slug
    ).first()
    if flag and not flag.is_enabled:
        return Response(
            {"error": f"Integração '{connector_slug}' está desabilitada para esta organização."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


# ─── Health Dashboard ────────────────────────────────────────────────────────


class IntegrationHealthDashboardView(APIView):
    """GET /api/integrations/health/ — Saúde de todas as integrações ativas."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        connections = IntegrationConnection.objects.filter(
            org=request.org, is_active=True
        )
        data = []
        for conn in connections:
            data.append({
                "connector_slug": conn.connector_slug,
                "display_name": conn.display_name,
                "health_status": conn.health_status,
                "error_count": conn.error_count,
                "last_sync_at": conn.last_sync_at,
                "last_error": conn.last_error,
            })
        return Response(data)


# ─── Feature Flags (Admin only) ─────────────────────────────────────────────


class FeatureFlagListView(APIView):
    """GET /api/integrations/flags/ — Listar feature flags da org."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        flags = OrgFeatureFlag.objects.filter(org=request.org)
        serializer = OrgFeatureFlagSerializer(flags, many=True)
        return Response(serializer.data)


class FeatureFlagDetailView(APIView):
    """PATCH /api/integrations/flags/<feature_key>/ — Ativar/desativar flag."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def patch(self, request, feature_key):
        flag, _created = OrgFeatureFlag.objects.get_or_create(
            org=request.org,
            feature_key=feature_key,
            defaults={"is_enabled": False},
        )

        is_enabled = request.data.get("is_enabled")
        if is_enabled is not None:
            flag.is_enabled = bool(is_enabled)

        config_json = request.data.get("config_json")
        if config_json is not None:
            flag.config_json = config_json

        flag.save()

        # Ao desativar, desativar IntegrationConnection associada
        if not flag.is_enabled:
            IntegrationConnection.objects.filter(
                org=request.org, connector_slug=feature_key, is_active=True
            ).update(is_active=False)

        serializer = OrgFeatureFlagSerializer(flag)
        return Response(serializer.data)


# ─── Webhook Receiver (AllowAny) ────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([AllowAny])
def webhook_receiver(request, connector_slug, webhook_token=None):
    """
    Endpoint genérico de webhook.

    URLs:
        POST /api/integrations/webhooks/<connector_slug>/<webhook_token>/  (preferred)
        POST /api/integrations/webhooks/<connector_slug>/                  (legacy)

    Token-based: lookup direto por webhook_token (seguro, sem ambiguidade multi-tenant).
    Legacy: identifica org pelo header X-Org-Id ou account_id no payload.
    """
    connector_cls = ConnectorRegistry.get(connector_slug)
    if not connector_cls:
        return Response({"error": "Connector not found"}, status=status.HTTP_404_NOT_FOUND)

    from django.db import connection as db_conn

    connection = None
    org_id = None

    # ── PRIMARY: Token-based lookup (secure, no ambiguity) ──
    if webhook_token:
        with db_conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, org_id FROM integration_connection "
                "WHERE webhook_token = %s AND connector_slug = %s AND is_active = true "
                "LIMIT 1",
                [webhook_token, connector_slug],
            )
            row = cursor.fetchone()
        if not row:
            return Response({"error": "Invalid webhook token"}, status=status.HTTP_404_NOT_FOUND)
        conn_id, org_id = row[0], str(row[1])
        # Set RLS context
        with db_conn.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_org', %s, false)", [org_id]
            )
        connection = IntegrationConnection.objects.get(id=conn_id)

    # ── FALLBACK: Legacy org identification ──
    else:
        org_id = request.headers.get("X-Org-Id") or request.data.get("org_id")

        # Chatwoot (and similar) webhooks don't send X-Org-Id.
        # Identify org by matching account_id from the payload to IntegrationConnection.
        if not org_id:
            account_id = None
            if isinstance(request.data, dict):
                account_id = request.data.get("account", {}).get("id") if isinstance(request.data.get("account"), dict) else None
            if account_id:
                with db_conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, org_id FROM integration_connection "
                        "WHERE connector_slug = %s AND is_active = true "
                        "AND (config_json->>'account_id')::text = %s "
                        "LIMIT 1",
                        [connector_slug, str(account_id)],
                    )
                    row = cursor.fetchone()
                if row:
                    org_id = str(row[1])

        if not org_id:
            return Response({"error": "Organization not identified"}, status=status.HTTP_400_BAD_REQUEST)

        # Set RLS context for this org (webhook endpoints bypass middleware)
        with db_conn.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_org', %s, false)", [str(org_id)]
            )

        connection = IntegrationConnection.objects.filter(
            connector_slug=connector_slug, org_id=org_id, is_active=True
        ).first()

    if not connection:
        return Response(
            {"error": "Integration not active"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Validar autenticidade
    connector = connector_cls()
    if not connector.validate_webhook(
        request.body, dict(request.headers), connection.webhook_secret
    ):
        WebhookLog.objects.create(
            org_id=org_id,
            connector_slug=connector_slug,
            event_type=request.data.get("event", "unknown"),
            status="rejected",
        )
        return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

    # Enfileirar processamento async
    process_webhook.delay(
        connector_slug=connector_slug,
        org_id=str(org_id),
        payload=request.data,
        headers={k: v for k, v in request.headers.items()},
    )

    # Registrar webhook recebido
    WebhookLog.objects.create(
        org_id=org_id,
        connector_slug=connector_slug,
        event_type=request.data.get("event", "unknown"),
        status="queued",
    )

    return Response({"status": "accepted"}, status=status.HTTP_200_OK)


# ─── Integration ViewSet (Admin only) ───────────────────────────────────────


class IntegrationListView(APIView):
    """GET /api/integrations/ — Listar integrações disponíveis com status."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request):
        # Obter todos os conectores registrados
        connectors = ConnectorRegistry.all()
        org = request.org

        result = []
        for slug, connector_cls in connectors.items():
            connection = IntegrationConnection.objects.filter(
                org=org, connector_slug=slug
            ).first()

            data = {
                "slug": slug,
                "name": connector_cls.name,
                "icon": getattr(connector_cls, "icon", ""),
                "version": getattr(connector_cls, "version", "1.0.0"),
                "sync_types": connector_cls().get_sync_types(),
                "is_active": connection.is_active if connection else False,
                "is_connected": connection.is_connected if connection else False,
                "last_sync_at": connection.last_sync_at if connection else None,
                "health_status": connection.health_status if connection else "unknown",
                "error_count": connection.error_count if connection else 0,
            }
            result.append(data)

        return Response(result)


class IntegrationDetailView(APIView):
    """GET/PATCH /api/integrations/<slug>/ — Detalhe e config de integração."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request, connector_slug):
        connector_cls = ConnectorRegistry.get(connector_slug)
        if not connector_cls:
            return Response({"error": "Connector not found"}, status=status.HTTP_404_NOT_FOUND)

        # Verificar feature flag
        blocked = _check_feature_enabled(request.org, connector_slug)
        if blocked:
            return blocked

        connection = IntegrationConnection.objects.filter(
            org=request.org, connector_slug=connector_slug
        ).first()

        connector = connector_cls()
        schema = connector.get_config_schema()
        data = {
            "slug": connector_slug,
            "name": connector_cls.name,
            "icon": getattr(connector_cls, "icon", ""),
            "config_schema": schema,
            "sync_types": connector.get_sync_types(),
        }

        if connection:
            data.update(IntegrationConnectionSerializer(connection).data)
            # Expose non-secret config values for the frontend form.
            # Fields marked as secret in the schema are replaced with empty string.
            secret_fields = set()
            for field_def in schema.get("fields", []):
                if field_def.get("secret") or field_def.get("type") == "password":
                    secret_fields.add(field_def.get("name"))
            sanitized_config = {}
            for key, value in (connection.config_json or {}).items():
                sanitized_config[key] = "" if key in secret_fields else value
            data["config"] = sanitized_config
        else:
            data.update({
                "id": None,
                "is_active": False,
                "is_connected": False,
                "config": {},
                "sync_interval_minutes": 60,
                "conflict_strategy": "last_write_wins",
                "last_sync_at": None,
                "health_status": "unknown",
                "error_count": 0,
                "last_error": "",
                "display_name": connector_cls.name,
                "created_at": None,
                "updated_at": None,
            })

        return Response(data)

    def patch(self, request, connector_slug):
        """Atualizar configuração da integração. Cria connection se não existir."""
        connector_cls = ConnectorRegistry.get(connector_slug)
        if not connector_cls:
            return Response({"error": "Connector not found"}, status=status.HTTP_404_NOT_FOUND)

        connection, _created = IntegrationConnection.objects.get_or_create(
            org=request.org,
            connector_slug=connector_slug,
            defaults={"display_name": connector_cls.name},
        )

        # Validar e criptografar config_json contra config_schema do conector
        config_json = request.data.get("config_json")
        if config_json is not None:
            connector = connector_cls()
            schema = connector.get_config_schema()
            if schema and schema.get("fields"):
                # Mesclar campos secret ANTES da validação: se o frontend
                # envia string vazia, manter o valor criptografado existente.
                existing_config = connection.config_json or {}
                secret_fields = set()
                for field_def in schema.get("fields", []):
                    if field_def.get("secret") or field_def.get("type") == "password":
                        secret_fields.add(field_def.get("name"))

                for sf in secret_fields:
                    if not config_json.get(sf) and existing_config.get(sf):
                        config_json[sf] = existing_config[sf]

                errors = _validate_config_against_schema(config_json, schema)
                if errors:
                    return Response(
                        {"error": "Validação falhou", "field_errors": errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Criptografar campos secret antes de persistir
                config_json = _encrypt_secret_fields(config_json, schema)

            # Atualizar no request.data para o serializer
            request.data["config_json"] = config_json

        serializer = IntegrationConnectionConfigSerializer(
            connection, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(IntegrationConnectionSerializer(connection).data)



class IntegrationConnectView(APIView):
    """POST /api/integrations/<slug>/connect/ — Conectar integração."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def post(self, request, connector_slug):
        connector_cls = ConnectorRegistry.get(connector_slug)
        if not connector_cls:
            return Response({"error": "Connector not found"}, status=status.HTTP_404_NOT_FOUND)

        # Verificar feature flag
        blocked = _check_feature_enabled(request.org, connector_slug)
        if blocked:
            return blocked

        connector = connector_cls()
        config = request.data.get("config", {})

        # Validar config contra config_schema do conector
        schema = connector.get_config_schema()
        if schema and schema.get("fields"):
            # Mesclar campos secret vazios com config salvo existente
            # (frontend envia string vazia para campos secret/password)
            existing_conn = IntegrationConnection.objects.filter(
                org=request.org, connector_slug=connector_slug
            ).first()
            if existing_conn:
                existing_config = existing_conn.config_json or {}
                secret_fields = set()
                for field_def in schema.get("fields", []):
                    if field_def.get("secret") or field_def.get("type") == "password":
                        secret_fields.add(field_def.get("name"))

                for sf in secret_fields:
                    if not config.get(sf) and existing_config.get(sf):
                        config[sf] = existing_config[sf]

            errors = _validate_config_against_schema(config, schema)
            if errors:
                return Response(
                    {"error": "Validação falhou", "field_errors": errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Criptografar campos secret antes de persistir
            config = _encrypt_secret_fields(config, schema)

        # Descriptografar campos secret para o connector.connect()
        # (o conector precisa dos valores em texto plano para autenticar)
        connect_config = dict(config)
        if schema and schema.get("fields"):
            from cryptography.fernet import Fernet, InvalidToken
            from django.conf import settings as django_settings

            fernet_key = getattr(django_settings, "FERNET_KEY", None)
            if fernet_key:
                f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
                secret_fields = set()
                for field_def in schema.get("fields", []):
                    if field_def.get("secret") or field_def.get("type") == "password":
                        secret_fields.add(field_def.get("name"))

                for sf in secret_fields:
                    value = connect_config.get(sf, "")
                    if value and isinstance(value, str) and value.startswith("gAAAAA"):
                        try:
                            connect_config[sf] = f.decrypt(value.encode()).decode()
                        except (InvalidToken, Exception):
                            pass

        try:
            result = connector.connect(request.org, connect_config)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Criar ou atualizar IntegrationConnection
        connection, created = IntegrationConnection.objects.update_or_create(
            org=request.org,
            connector_slug=connector_slug,
            defaults={
                "display_name": connector_cls.name,
                "is_active": True,
                "is_connected": True,
                "config_json": config,
                "health_status": "healthy",
                "error_count": 0,
            },
        )

        # Auto-create ChannelConfig for connectors that map to a channel
        _auto_create_channel_config(request.org, connector_slug, config)

        # Post-connect hook (e.g. register webhook with token-based URL)
        try:
            connector.post_connect(request.org, connection)
        except Exception as exc:
            logger.warning("post_connect hook failed for %s: %s", connector_slug, exc)

        return Response(
            IntegrationConnectionSerializer(connection).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class IntegrationDisconnectView(APIView):
    """POST /api/integrations/<slug>/disconnect/ — Desconectar integração."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def post(self, request, connector_slug):
        connector_cls = ConnectorRegistry.get(connector_slug)
        if not connector_cls:
            return Response({"error": "Connector not found"}, status=status.HTTP_404_NOT_FOUND)

        connection = IntegrationConnection.objects.filter(
            org=request.org, connector_slug=connector_slug
        ).first()

        if not connection:
            return Response({"error": "Not connected"}, status=status.HTTP_404_NOT_FOUND)

        connector = connector_cls()
        connector.disconnect(request.org)

        connection.is_active = False
        connection.is_connected = False
        connection.save(update_fields=["is_active", "is_connected", "updated_at"])

        return Response({"status": "disconnected"})


class IntegrationHealthView(APIView):
    """GET /api/integrations/<slug>/health/ — Status de saúde."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request, connector_slug):
        connector_cls = ConnectorRegistry.get(connector_slug)
        if not connector_cls:
            return Response({"error": "Connector not found"}, status=status.HTTP_404_NOT_FOUND)

        connector = connector_cls()
        health = connector.get_health(request.org)
        return Response(health)


class IntegrationSyncView(APIView):
    """POST /api/integrations/<slug>/sync/ — Disparar sync manual."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def post(self, request, connector_slug):
        connector_cls = ConnectorRegistry.get(connector_slug)
        if not connector_cls:
            return Response({"error": "Connector not found"}, status=status.HTTP_404_NOT_FOUND)

        # Verificar feature flag
        blocked = _check_feature_enabled(request.org, connector_slug)
        if blocked:
            return blocked

        connection = IntegrationConnection.objects.filter(
            org=request.org, connector_slug=connector_slug, is_active=True
        ).first()

        if not connection:
            return Response(
                {"error": "Integration not active"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sync_type = request.data.get("sync_type", "all")

        # Criar SyncJob
        job = SyncJob.objects.create(
            org=request.org,
            connector_slug=connector_slug,
            sync_type=sync_type,
            status="PENDING",
        )

        # Enfileirar sync
        run_connector_sync.delay(
            connector_slug=connector_slug,
            org_id=str(request.org.id),
            sync_type=sync_type,
            job_id=str(job.id),
        )

        return Response(SyncJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class SyncJobDetailView(APIView):
    """GET /api/integrations/<slug>/sync/<job_id>/ — Status de sync job."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request, connector_slug, job_id):
        try:
            job = SyncJob.objects.get(
                id=job_id, org=request.org, connector_slug=connector_slug
            )
        except SyncJob.DoesNotExist:
            return Response({"error": "Sync job not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(SyncJobSerializer(job).data)


# ─── Integration Log ViewSet (Admin only) ───────────────────────────────────


class IntegrationLogListView(APIView, LimitOffsetPagination):
    """GET /api/integrations/logs/ — Logs de integração filtráveis."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request):
        queryset = IntegrationLog.objects.filter(org=request.org)

        # Filtros
        connector = request.query_params.get("connector")
        if connector:
            queryset = queryset.filter(connector_slug=connector)

        operation = request.query_params.get("operation")
        if operation:
            queryset = queryset.filter(operation=operation)

        log_status = request.query_params.get("status")
        if log_status:
            queryset = queryset.filter(status=log_status)

        entity_type = request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        direction = request.query_params.get("direction")
        if direction:
            queryset = queryset.filter(direction=direction)

        # Filtro por período
        date_from = request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        results = self.paginate_queryset(queryset, request, view=self)
        serializer = IntegrationLogSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


class WebhookLogListView(APIView, LimitOffsetPagination):
    """GET /api/integrations/webhooks/logs/ — Logs de webhooks."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request):
        queryset = WebhookLog.objects.filter(org=request.org)

        connector = request.query_params.get("connector")
        if connector:
            queryset = queryset.filter(connector_slug=connector)

        event_type = request.query_params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        results = self.paginate_queryset(queryset, request, view=self)
        serializer = WebhookLogSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)


# ─── Field Mapping ViewSet (Admin only) ─────────────────────────────────────


class FieldMappingListView(APIView):
    """GET/POST /api/integrations/field-mappings/ — CRUD de mapeamento de campos."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request):
        queryset = FieldMapping.objects.filter(org=request.org)

        connector = request.query_params.get("connector")
        if connector:
            queryset = queryset.filter(connector_slug=connector)

        serializer = FieldMappingSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FieldMappingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(org=request.org)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FieldMappingDetailView(APIView):
    """GET/PATCH/DELETE /api/integrations/field-mappings/<id>/ — Detalhe de mapeamento."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def _get_object(self, request, pk):
        try:
            return FieldMapping.objects.get(id=pk, org=request.org)
        except FieldMapping.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_object(request, pk)
        if not obj:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(FieldMappingSerializer(obj).data)

    def patch(self, request, pk):
        obj = self._get_object(request, pk)
        if not obj:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = FieldMappingSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get_object(request, pk)
        if not obj:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Conflict Log (Admin only, read-only) ───────────────────────────────────


class ConflictLogListView(APIView, LimitOffsetPagination):
    """GET /api/integrations/conflicts/ — Logs de conflitos."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request):
        queryset = ConflictLog.objects.filter(org=request.org)

        connector = request.query_params.get("connector")
        if connector:
            queryset = queryset.filter(connector_slug=connector)

        entity_type = request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        results = self.paginate_queryset(queryset, request, view=self)
        serializer = ConflictLogSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)

# ─── Integration Review (Admin only) ────────────────────────────────────────


class IntegrationReviewView(APIView):
    """
    GET /api/integrations/review/ — Executar revisão de integridade.
    POST /api/integrations/review/ — Executar revisão com auto-fix.

    Retorna relatório completo de consistência do sistema integrativo.
    """

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def get(self, request):
        from integrations.review_agent import IntegrationReviewAgent

        agent = IntegrationReviewAgent(request.org, auto_fix=False)
        report = agent.run_full_review()
        return Response(report.to_dict())

    def post(self, request):
        from integrations.review_agent import IntegrationReviewAgent

        auto_fix = request.data.get("auto_fix", False)
        agent = IntegrationReviewAgent(request.org, auto_fix=auto_fix)
        report = agent.run_full_review()
        return Response(report.to_dict())


# ─── Variable Registry (Admin only, read-only) ──────────────────────────────


class VariableRegistryView(APIView):
    """
    GET /api/integrations/variables/ — Listar variáveis unificadas do sistema.
    GET /api/integrations/variables/?entity=contact — Filtrar por entidade.

    Retorna o schema de variáveis canônicas com aliases.
    """

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        from integrations.variable_registry import (
            ACCOUNT_SCHEMA,
            CONTACT_SCHEMA,
            get_required_fields,
            get_unique_fields,
        )

        entity = request.query_params.get("entity")

        result = {}

        if not entity or entity == "contact":
            result["contact"] = {
                "fields": {
                    key: {
                        "crm_field": m.crm_field,
                        "category": m.category.value,
                        "aliases": list(m.aliases),
                        "transform": m.transform,
                        "required": m.required,
                        "unique_per_org": m.unique_per_org,
                        "description": m.description,
                    }
                    for key, m in CONTACT_SCHEMA.items()
                },
                "required_fields": get_required_fields("contact"),
                "unique_fields": get_unique_fields("contact"),
            }

        if not entity or entity == "account":
            result["account"] = {
                "fields": {
                    key: {
                        "crm_field": m.crm_field,
                        "category": m.category.value,
                        "aliases": list(m.aliases),
                        "transform": m.transform,
                        "required": m.required,
                        "unique_per_org": m.unique_per_org,
                        "description": m.description,
                    }
                    for key, m in ACCOUNT_SCHEMA.items()
                },
                "required_fields": get_required_fields("account"),
                "unique_fields": get_unique_fields("account"),
            }

        return Response(result)

