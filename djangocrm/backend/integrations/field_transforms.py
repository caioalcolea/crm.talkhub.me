"""
Lógica de mapeamento de campos e transformações.

Aplica FieldMapping configurado por org/conector para transformar
dados entre o sistema externo e o CRM.
"""

import logging
import re

from integrations.exceptions import FieldMappingError

logger = logging.getLogger(__name__)


def apply_field_mapping(source_data: dict, mappings) -> dict:
    """
    Aplicar mapeamentos de campo a dados de entrada.

    Args:
        source_data: Dados do sistema externo (dict).
        mappings: QuerySet ou lista de FieldMapping ativos.

    Returns:
        Dict com campos mapeados para o CRM.
    """
    result = {}
    for mapping in mappings:
        if not mapping.is_active:
            continue

        source_value = source_data.get(mapping.source_field)
        if source_value is None:
            continue

        try:
            transformed = _apply_transform(source_value, mapping.field_type, mapping.transform_config)
            if isinstance(transformed, dict):
                # Transformações que produzem múltiplos campos (ex: split)
                result.update(transformed)
            else:
                result[mapping.target_field] = transformed
        except Exception as e:
            logger.warning(
                "Field transform failed: %s → %s (%s): %s",
                mapping.source_field,
                mapping.target_field,
                mapping.field_type,
                e,
            )

    return result


def _apply_transform(value, field_type: str, config: dict):
    """Aplicar transformação baseada no tipo de campo."""
    transforms = {
        "text": lambda v, c: str(v),
        "number": _transform_number,
        "date": lambda v, c: str(v),
        "select": map_select_value,
        "concat": lambda v, c: concat_name(v, c.get("separator", " ")),
        "split": lambda v, c: split_full_name(str(v)),
        "phone_format": lambda v, c: format_phone(str(v), c.get("country_code", "BR")),
    }
    transform_fn = transforms.get(field_type)
    if not transform_fn:
        return value
    return transform_fn(value, config)


def _transform_number(value, config: dict):
    """Converter valor para número."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0


def split_full_name(full_name: str) -> dict:
    """
    Dividir nome completo em first_name e last_name.

    Args:
        full_name: Nome completo.

    Returns:
        Dict com first_name e last_name.
    """
    if not full_name or not full_name.strip():
        return {"first_name": "", "last_name": ""}

    parts = full_name.strip().split(None, 1)
    return {
        "first_name": parts[0],
        "last_name": parts[1] if len(parts) > 1 else "",
    }


def concat_name(first_name: str, last_name: str = "") -> str:
    """
    Concatenar first_name e last_name em nome completo.

    Args:
        first_name: Primeiro nome.
        last_name: Sobrenome (opcional).

    Returns:
        Nome completo.
    """
    parts = [p for p in [str(first_name).strip(), str(last_name).strip()] if p]
    return " ".join(parts)


def format_phone(phone: str, country_code: str = "BR") -> str:
    """
    Formatar número de telefone.

    Remove caracteres não numéricos e adiciona código do país se necessário.

    Args:
        phone: Número de telefone.
        country_code: Código do país (ISO 3166-1 alpha-2).

    Returns:
        Telefone formatado.
    """
    if not phone:
        return ""

    # Remover tudo que não é dígito ou +
    digits = re.sub(r"[^\d+]", "", phone)

    if not digits:
        return ""

    # Se já começa com +, retornar como está
    if digits.startswith("+"):
        return digits

    # Adicionar código do país
    country_codes = {
        "BR": "+55",
        "US": "+1",
        "PT": "+351",
    }
    prefix = country_codes.get(country_code.upper(), "")
    if prefix and not digits.startswith(prefix.lstrip("+")):
        return f"{prefix}{digits}"

    return digits


def map_select_value(value, config: dict):
    """
    Mapear valor de campo select usando configuração de mapeamento.

    Args:
        value: Valor original.
        config: Dict com mapeamento {valor_externo: valor_crm}.

    Returns:
        Valor mapeado ou valor original se não encontrado.
    """
    mapping = config.get("mapping", {})
    return mapping.get(str(value), value)
