"""
Exceções customizadas do Hub de Integrações.

Cada exceção mapeia para um status HTTP específico e pode ser
capturada pelo DRF exception handler para respostas consistentes.
"""

from rest_framework.exceptions import APIException


class IntegrationError(APIException):
    """Erro genérico de integração."""

    status_code = 500
    default_detail = "An integration error occurred."
    default_code = "integration_error"


class ConnectorNotFoundError(APIException):
    """Conector não encontrado no registry."""

    status_code = 404
    default_detail = "Connector not found."
    default_code = "connector_not_found"


class ConnectorDisabledError(APIException):
    """Conector está desativado para esta org."""

    status_code = 403
    default_detail = "This connector is currently disabled."
    default_code = "connector_disabled"


class WebhookValidationError(APIException):
    """Falha na validação de autenticidade do webhook."""

    status_code = 401
    default_detail = "Webhook signature validation failed."
    default_code = "webhook_validation_error"


class SyncConflictError(APIException):
    """Conflito de sincronização bidirecional."""

    status_code = 409
    default_detail = "A sync conflict was detected."
    default_code = "sync_conflict"


class ChannelDisabledError(APIException):
    """Canal de comunicação está desativado."""

    status_code = 403
    default_detail = "This communication channel is disabled."
    default_code = "channel_disabled"


class OptOutBlockedError(APIException):
    """Contato fez opt-out do canal, envio bloqueado."""

    status_code = 403
    default_detail = "Contact has opted out of this channel."
    default_code = "opt_out_blocked"


class FieldMappingError(APIException):
    """Erro no mapeamento de campos."""

    status_code = 400
    default_detail = "Field mapping error."
    default_code = "field_mapping_error"
