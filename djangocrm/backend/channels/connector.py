"""
SMTPConnector — BaseConnector implementation for SMTP email.

Registrado automaticamente via AppConfig.connector_class para aparecer
no Hub de Integrações (/settings/integrations).

Diferente do SMTPNativeProvider (ChannelRegistry), este conector implementa
a interface BaseConnector para que o SMTP apareça na listagem de integrações
e possa ser configurado/ativado pelo admin via UI.
"""

import logging
import smtplib
from typing import Any

from integrations.base import BaseConnector

logger = logging.getLogger(__name__)


class SMTPConnector(BaseConnector):
    slug = "smtp"
    name = "Email (SMTP)"
    icon = "mail"
    version = "1.0.0"

    def connect(self, org, config: dict) -> bool:
        """Validar credenciais SMTP tentando autenticar no servidor."""
        host = config.get("smtp_host", "")
        port = int(config.get("smtp_port", 587))
        user = config.get("smtp_user", "")
        password = config.get("smtp_password", "")

        if not host or not user:
            raise ValueError("Host SMTP e usuário são obrigatórios.")

        try:
            use_ssl = port == 465
            logger.info(
                "SMTP connect attempt for org %s: host=%s port=%d ssl=%s user=%s pass_len=%d",
                org.id, host, port, use_ssl, user, len(password) if password else 0,
            )
            if use_ssl:
                with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                    server.ehlo()
                    if user and password:
                        server.login(user, password)
            else:
                with smtplib.SMTP(host, port, timeout=15) as server:
                    server.ehlo()
                    if port != 25:
                        server.starttls()
                        server.ehlo()
                    if user and password:
                        server.login(user, password)
            logger.info("SMTP connect SUCCESS for org %s", org.id)
            return True
        except smtplib.SMTPAuthenticationError:
            raise ValueError("Falha na autenticação SMTP. Verifique usuário e senha.")
        except smtplib.SMTPConnectError:
            raise ValueError(f"Não foi possível conectar ao servidor {host}:{port}.")
        except Exception as exc:
            logger.error(
                "SMTP connect failed for org %s: %s (type=%s, host=%s, port=%d, ssl=%s)",
                org.id, exc, type(exc).__name__, host, port, use_ssl,
            )
            raise ValueError(f"Erro ao conectar: {exc}")

    def disconnect(self, org) -> bool:
        """SMTP não mantém conexão persistente — apenas desativa."""
        return True

    def sync(self, org, sync_type: str, job_id: str) -> dict:
        """SMTP não possui sincronização bidirecional."""
        return {
            "status": "COMPLETED",
            "total_records": 0,
            "imported_count": 0,
            "message": "SMTP não requer sincronização.",
        }

    def get_status(self, org) -> dict:
        from integrations.models import IntegrationConnection

        conn = IntegrationConnection.objects.filter(
            org=org, connector_slug=self.slug
        ).first()
        if not conn:
            return {"is_connected": False}
        return {
            "is_connected": conn.is_connected,
            "last_sync_at": conn.last_sync_at,
        }

    def get_health(self, org) -> dict:
        from integrations.models import IntegrationConnection

        conn = IntegrationConnection.objects.filter(
            org=org, connector_slug=self.slug
        ).first()
        if not conn or not conn.is_active:
            return {"status": "unknown", "error_count": 0}

        config = conn.config_json or {}
        host = config.get("smtp_host", "")
        port = int(config.get("smtp_port", 587))

        if not host:
            return {"status": "down", "error_count": 1}

        try:
            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=5) as server:
                    server.ehlo()
            else:
                with smtplib.SMTP(host, port, timeout=5) as server:
                    server.ehlo()
            return {"status": "healthy", "error_count": 0}
        except Exception:
            return {"status": "degraded", "error_count": conn.error_count}

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "fields": [
                {
                    "name": "from_email",
                    "type": "text",
                    "label": "Email de Envio (From)",
                    "placeholder": "adm@talkhub.me",
                    "required": True,
                    "description": "Endereço de email usado como remetente.",
                },
                {
                    "name": "reply_to",
                    "type": "text",
                    "label": "Responder Para (Reply-To)",
                    "placeholder": "suporte@talkhub.me",
                    "required": False,
                    "description": "Endereço para respostas (opcional).",
                },
                {
                    "name": "smtp_host",
                    "type": "text",
                    "label": "Servidor SMTP",
                    "placeholder": "smtp.titan.email",
                    "required": True,
                    "description": "Hostname do servidor SMTP.",
                },
                {
                    "name": "smtp_port",
                    "type": "number",
                    "label": "Porta SMTP",
                    "placeholder": "587",
                    "required": True,
                    "description": "Porta do servidor (587 para STARTTLS, 465 para SSL).",
                },
                {
                    "name": "smtp_user",
                    "type": "text",
                    "label": "Usuário SMTP",
                    "placeholder": "adm@talkhub.me",
                    "required": True,
                    "description": "Usuário para autenticação SMTP.",
                },
                {
                    "name": "smtp_password",
                    "type": "password",
                    "label": "Senha SMTP",
                    "placeholder": "",
                    "required": True,
                    "description": "Senha para autenticação SMTP.",
                    "secret": True,
                },
            ],
            "required": ["from_email", "smtp_host", "smtp_port", "smtp_user", "smtp_password"],
        }

    def handle_webhook(self, org, payload: dict, headers: dict) -> Any:
        """SMTP não recebe webhooks."""
        logger.warning("SMTP connector received unexpected webhook for org %s", org.id)
        return {"status": "ignored", "message": "SMTP does not handle webhooks."}

    def get_sync_types(self) -> list[str]:
        """SMTP não possui tipos de sync."""
        return []
