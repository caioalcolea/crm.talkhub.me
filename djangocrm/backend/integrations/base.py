"""
BaseConnector ABC — Interface comum para conectores de integração.

Todo conector externo (TalkHub Omni, etc.) deve herdar
desta classe e implementar todos os métodos abstratos.

Registro automático via Django app registry:
    - Definir `connector_class = MeuConector` no AppConfig do app
    - ConnectorRegistry.discover() registra automaticamente no ready()
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Interface comum que todo conector de integração deve implementar."""

    slug: str  # ex: "talkhub-omni", "salesforce"
    name: str  # ex: "TalkHub Omni"
    icon: str  # path para ícone SVG
    version: str = "1.0.0"

    @abstractmethod
    def connect(self, org, config: dict) -> bool:
        """Estabelecer conexão com o sistema externo."""
        ...

    @abstractmethod
    def disconnect(self, org) -> bool:
        """Desconectar do sistema externo."""
        ...

    @abstractmethod
    def sync(self, org, sync_type: str, job_id: str) -> dict:
        """Executar sincronização. Retorna dict com contadores."""
        ...

    @abstractmethod
    def get_status(self, org) -> dict:
        """Retornar status da conexão: {is_connected, last_sync_at, ...}."""
        ...

    @abstractmethod
    def get_health(self, org) -> dict:
        """Retornar saúde: {status: 'healthy'|'degraded'|'down', error_count, ...}."""
        ...

    @abstractmethod
    def get_config_schema(self) -> dict:
        """Retornar JSON Schema do formulário de configuração."""
        ...

    @abstractmethod
    def handle_webhook(self, org, payload: dict, headers: dict) -> Any:
        """Processar payload de webhook. Chamado dentro de Celery task."""
        ...

    def validate_webhook(self, payload: bytes, headers: dict, secret: str) -> bool:
        """Validar autenticidade do webhook (HMAC). Override opcional."""
        return True

    def post_connect(self, org, connection) -> None:
        """Chamado após IntegrationConnection ser salva. Override para post-connect hooks."""
        pass

    def get_sync_types(self) -> list[str]:
        """Retornar tipos de sync suportados. Override opcional."""
        return ["all"]
