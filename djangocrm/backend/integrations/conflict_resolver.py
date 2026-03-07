"""
Lógica de resolução de conflitos de sincronização bidirecional.

Estratégias suportadas:
- last_write_wins: O registro mais recente vence.
- crm_wins: O valor do CRM sempre prevalece.
- external_wins: O valor do sistema externo sempre prevalece.
"""

import logging

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


def resolve_conflict(
    crm_value,
    external_value,
    strategy: str,
    crm_updated_at=None,
    external_updated_at=None,
) -> tuple:
    """
    Resolver conflito conforme estratégia configurada.

    Args:
        crm_value: Valor atual no CRM.
        external_value: Valor do sistema externo.
        strategy: Estratégia de resolução (last_write_wins, crm_wins, external_wins).
        crm_updated_at: Timestamp da última atualização no CRM.
        external_updated_at: Timestamp da última atualização no sistema externo.

    Returns:
        Tuple (winning_value, resolved_by) onde resolved_by é "crm", "external" ou "last_write".
    """
    if strategy == "crm_wins":
        return crm_value, "crm"

    if strategy == "external_wins":
        return external_value, "external"

    # last_write_wins (padrão)
    if crm_updated_at and external_updated_at:
        if crm_updated_at >= external_updated_at:
            return crm_value, "last_write"
        return external_value, "last_write"

    # Sem timestamps, external vence (webhook é mais recente)
    return external_value, "last_write"


def detect_conflict(entity_id: str, org_id: str, window_seconds: int = 5) -> bool:
    """
    Detectar se há conflito na janela de tempo (anti-loop).

    Verifica se o entity foi atualizado recentemente pelo CRM,
    indicando que um webhook recebido pode ser eco da própria atualização.

    Args:
        entity_id: ID da entidade (ou entity_key como "contact:{subscriber_id}").
        org_id: ID da organização.
        window_seconds: Janela de tempo em segundos.

    Returns:
        True se há conflito potencial (atualizado recentemente).
    """
    cache_key = f"sync_lock:{entity_id}:{org_id}"
    return cache.get(cache_key) is not None


def set_sync_lock(entity_id: str, org_id: str, ttl: int = 5):
    """
    Definir sync lock para anti-loop.

    Args:
        entity_id: ID da entidade (ou entity_key como "contact:{subscriber_id}").
        org_id: ID da organização.
        ttl: Time-to-live em segundos.
    """
    cache_key = f"sync_lock:{entity_id}:{org_id}"
    cache.set(cache_key, True, timeout=ttl)


def log_conflict(
    org,
    connector_slug: str,
    entity_type: str,
    entity_id: str,
    crm_value,
    external_value,
    resolved_by: str,
    fields_overwritten: list | None = None,
):
    """
    Registrar ConflictLog no banco de dados.

    Args:
        org: Instância de Org.
        connector_slug: Slug do conector.
        entity_type: Tipo da entidade (contact, case, lead).
        entity_id: ID da entidade.
        crm_value: Valor do CRM (JSON-serializable).
        external_value: Valor externo (JSON-serializable).
        resolved_by: Quem venceu (crm, external, last_write).
        fields_overwritten: Lista de campos sobrescritos.
    """
    from integrations.models import ConflictLog

    ConflictLog.objects.create(
        org=org,
        connector_slug=connector_slug,
        entity_type=entity_type,
        entity_id=str(entity_id),
        crm_value=crm_value,
        external_value=external_value,
        resolved_by=resolved_by,
        fields_overwritten=fields_overwritten or [],
    )
    logger.info(
        "Conflict logged: %s %s:%s resolved by %s",
        connector_slug,
        entity_type,
        entity_id,
        resolved_by,
    )
