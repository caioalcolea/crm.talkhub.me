"""
TalkHubOmniConnector — BaseConnector implementation for TalkHub Omni.

Registrado automaticamente via AppConfig.connector_class.
"""

import logging
from typing import Any

from integrations.base import BaseConnector

from .client import TalkHubAPIError, TalkHubClient
from .models import TalkHubConnection, TalkHubSyncJob

logger = logging.getLogger(__name__)


class TalkHubOmniConnector(BaseConnector):
    slug = "talkhub-omni"
    name = "TalkHub Omni"
    icon = "talkhub-omni.svg"
    version = "2.0.0"

    def connect(self, org, config: dict) -> bool:
        client = TalkHubClient(
            api_key=config["api_key"],
            base_url=config.get("workspace_url", "https://chat.talkhub.me"),
        )
        try:
            info = client.get_team_info()
        except TalkHubAPIError as exc:
            logger.error("TalkHub connect failed for org %s: %s", org.id, exc)
            return False

        TalkHubConnection.objects.update_or_create(
            org=org,
            defaults={
                "api_key": config["api_key"],
                "workspace_url": config.get("workspace_url", "https://chat.talkhub.me"),
                "workspace_name": info.get("name") or info.get("team_name", ""),
                "owner_email": info.get("email") or info.get("owner_email", ""),
                "is_connected": True,
            },
        )
        return True

    def disconnect(self, org) -> bool:
        TalkHubConnection.objects.filter(org=org).update(
            is_connected=False, api_key=""
        )
        return True

    def sync(self, org, sync_type: str, job_id: str) -> dict:
        from .models import TalkHubSyncJob
        from .sync_engine import run_sync

        # O IntegrationSyncView cria um SyncJob genérico, mas o sync_engine
        # espera um TalkHubSyncJob. Criar um TalkHubSyncJob correspondente.
        th_job = TalkHubSyncJob.objects.create(
            org=org,
            sync_type=sync_type,
            status="PENDING",
        )
        result = run_sync(org, sync_type, str(th_job.id))

        # Propagar resultado para o formato esperado pelo run_connector_sync
        return {
            "total": result.get("imported", 0) + result.get("updated", 0) + result.get("errors", 0),
            "imported": result.get("imported", 0),
            "updated": result.get("updated", 0),
            "skipped": 0,
            "errors": result.get("errors", 0),
        }

    def get_status(self, org) -> dict:
        conn = TalkHubConnection.objects.filter(org=org).first()
        if not conn:
            return {"is_connected": False}
        return {
            "is_connected": conn.is_connected,
            "last_sync_at": conn.last_sync_at,
            "workspace_name": conn.workspace_name,
            "workspace_url": conn.workspace_url,
        }

    def get_health(self, org) -> dict:
        recent = TalkHubSyncJob.objects.filter(org=org).order_by("-created_at")[:5]
        error_count = sum(1 for j in recent if j.status == "FAILED")
        if error_count >= 3:
            return {"status": "degraded", "error_count": error_count}
        if error_count > 0:
            return {"status": "warning", "error_count": error_count}
        return {"status": "healthy", "error_count": 0}

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "fields": [
                {
                    "name": "api_key",
                    "type": "password",
                    "label": "API Key",
                    "placeholder": "Insira sua API Key do TalkHub Omni",
                    "required": True,
                    "secret": True,
                    "description": "Token de autenticação da API do TalkHub Omni.",
                },
                {
                    "name": "workspace_url",
                    "type": "text",
                    "label": "Workspace URL",
                    "placeholder": "https://chat.talkhub.me",
                    "required": False,
                    "description": "URL base do workspace TalkHub Omni (padrão: https://chat.talkhub.me).",
                },
            ],
            "required": ["api_key"],
        }

    def handle_webhook(self, org, payload: dict, headers: dict) -> Any:
        from .webhook_handlers import route_webhook
        return route_webhook(org, payload)

    def validate_webhook(self, payload: bytes, headers: dict, secret: str) -> bool:
        # TalkHub Omni uses Bearer token auth, no HMAC validation needed
        return True

    def get_sync_types(self) -> list[str]:
        return [
            "contacts", "tickets", "tags",
            "team_members", "statistics", "conversations", "all",
        ]
