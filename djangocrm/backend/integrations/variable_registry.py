"""
Registro Unificado de Variáveis do Sistema Integrativo.

Define o mapeamento canônico entre variáveis de fontes externas
(TalkHub Omni, webhooks, CSV imports, etc.) e campos do CRM.

Cada entidade CRM (Contact, Account, Lead) tem um schema de variáveis
que garante consistência em TODOS os caminhos de integração:
  - webhook → Contact
  - sync → Contact
  - TalkHub subscriber → Contact
  - Lead conversion → Contact + Account
  - Field mapping transforms → Contact/Account

Uso:
    from integrations.variable_registry import CONTACT_SCHEMA, resolve_variable
    crm_field = resolve_variable("contact", "subscriber_name")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class VariableSource(str, Enum):
    """Fontes de dados reconhecidas pelo sistema."""
    TALKHUB_OMNI = "talkhub_omni"
    WEBHOOK = "webhook"
    CSV_IMPORT = "csv_import"
    MANUAL = "manual"
    LEAD_CONVERSION = "lead_conversion"
    API = "api"


class FieldCategory(str, Enum):
    """Categorias de campos para agrupamento lógico."""
    IDENTITY = "identity"
    CONTACT_INFO = "contact_info"
    SOCIAL = "social"
    ADDRESS = "address"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    TRACKING = "tracking"
    SYSTEM = "system"


@dataclass(frozen=True)
class VariableMapping:
    """Mapeamento de uma variável externa para um campo CRM."""
    crm_field: str
    category: FieldCategory
    aliases: tuple[str, ...] = ()
    transform: str | None = None  # nome da transformação em field_transforms
    required: bool = False
    unique_per_org: bool = False
    description: str = ""


# ─── CONTACT SCHEMA ──────────────────────────────────────────────────────────
# Mapeamento canônico: variável externa → campo Contact
# Aliases cobrem variações de nome entre TalkHub, webhooks, CSV, etc.

CONTACT_SCHEMA: dict[str, VariableMapping] = {
    "first_name": VariableMapping(
        crm_field="first_name",
        category=FieldCategory.IDENTITY,
        aliases=("nome", "name", "first", "subscriber_first_name", "given_name"),
        required=True,
        description="Primeiro nome do contato",
    ),
    "last_name": VariableMapping(
        crm_field="last_name",
        category=FieldCategory.IDENTITY,
        aliases=("sobrenome", "surname", "last", "subscriber_last_name", "family_name"),
        required=True,
        description="Sobrenome do contato",
    ),
    "full_name": VariableMapping(
        crm_field="first_name",  # split produz first_name + last_name
        category=FieldCategory.IDENTITY,
        aliases=("nome_completo", "subscriber_name", "display_name", "contact_name"),
        transform="split",
        description="Nome completo (será dividido em first_name + last_name)",
    ),
    "email": VariableMapping(
        crm_field="email",
        category=FieldCategory.CONTACT_INFO,
        aliases=("e-mail", "email_address", "subscriber_email", "mail"),
        unique_per_org=True,
        description="Email do contato (único por org)",
    ),
    "phone": VariableMapping(
        crm_field="phone",
        category=FieldCategory.CONTACT_INFO,
        aliases=("telefone", "phone_number", "subscriber_phone", "mobile", "celular", "whatsapp"),
        transform="phone_format",
        description="Telefone do contato",
    ),
    "organization": VariableMapping(
        crm_field="organization",
        category=FieldCategory.PROFESSIONAL,
        aliases=("empresa", "company", "company_name", "org_name", "subscriber_company"),
        description="Nome da empresa/organização do contato",
    ),
    "title": VariableMapping(
        crm_field="title",
        category=FieldCategory.PROFESSIONAL,
        aliases=("cargo", "job_title", "position", "role"),
        description="Cargo/título profissional",
    ),
    "department": VariableMapping(
        crm_field="department",
        category=FieldCategory.PROFESSIONAL,
        aliases=("departamento", "dept", "area", "setor"),
        description="Departamento",
    ),
    "instagram": VariableMapping(
        crm_field="instagram",
        category=FieldCategory.SOCIAL,
        aliases=("ig", "instagram_handle", "instagram_username"),
        description="Handle do Instagram",
    ),
    "facebook": VariableMapping(
        crm_field="facebook",
        category=FieldCategory.SOCIAL,
        aliases=("fb", "facebook_url", "facebook_id"),
        description="Facebook ID ou URL",
    ),
    "tiktok": VariableMapping(
        crm_field="tiktok",
        category=FieldCategory.SOCIAL,
        aliases=("tt", "tiktok_handle", "tiktok_username"),
        description="Handle do TikTok",
    ),
    "telegram": VariableMapping(
        crm_field="telegram",
        category=FieldCategory.SOCIAL,
        aliases=("tg", "telegram_handle", "telegram_username"),
        description="Handle do Telegram",
    ),
    "linkedin_url": VariableMapping(
        crm_field="linkedin_url",
        category=FieldCategory.SOCIAL,
        aliases=("linkedin", "linkedin_profile"),
        description="URL do perfil LinkedIn",
    ),
    "address_line": VariableMapping(
        crm_field="address_line",
        category=FieldCategory.ADDRESS,
        aliases=("endereco", "address", "street", "logradouro"),
        description="Endereço",
    ),
    "city": VariableMapping(
        crm_field="city",
        category=FieldCategory.ADDRESS,
        aliases=("cidade", "town", "municipality"),
        description="Cidade",
    ),
    "state": VariableMapping(
        crm_field="state",
        category=FieldCategory.ADDRESS,
        aliases=("estado", "province", "region", "uf"),
        description="Estado/Província",
    ),
    "postcode": VariableMapping(
        crm_field="postcode",
        category=FieldCategory.ADDRESS,
        aliases=("cep", "zip", "zip_code", "postal_code"),
        description="CEP/Código postal",
    ),
    "country": VariableMapping(
        crm_field="country",
        category=FieldCategory.ADDRESS,
        aliases=("pais", "country_code"),
        description="País (ISO 3166-1 alpha-3)",
    ),
    "source": VariableMapping(
        crm_field="source",
        category=FieldCategory.TRACKING,
        aliases=("origem", "lead_source", "channel_source"),
        description="Canal de origem do contato",
    ),
    "description": VariableMapping(
        crm_field="description",
        category=FieldCategory.SYSTEM,
        aliases=("notas", "notes", "bio", "about"),
        description="Notas/descrição do contato",
    ),
    "talkhub_subscriber_id": VariableMapping(
        crm_field="talkhub_subscriber_id",
        category=FieldCategory.TRACKING,
        aliases=("user_ns", "subscriber_id", "omni_user_ns"),
        description="TalkHub Omni subscriber namespace ID",
    ),
    "talkhub_channel_type": VariableMapping(
        crm_field="talkhub_channel_type",
        category=FieldCategory.TRACKING,
        aliases=("channel_type", "omni_channel_type"),
        description="Tipo do canal TalkHub de origem",
    ),
    "talkhub_channel_id": VariableMapping(
        crm_field="talkhub_channel_id",
        category=FieldCategory.TRACKING,
        aliases=("channel_id", "omni_channel_id"),
        description="ID do canal TalkHub de origem",
    ),
}


# ─── ACCOUNT SCHEMA ──────────────────────────────────────────────────────────

ACCOUNT_SCHEMA: dict[str, VariableMapping] = {
    "name": VariableMapping(
        crm_field="name",
        category=FieldCategory.IDENTITY,
        aliases=("company_name", "empresa", "organization", "org_name", "account_name"),
        required=True,
        unique_per_org=True,
        description="Nome da empresa (único por org)",
    ),
    "email": VariableMapping(
        crm_field="email",
        category=FieldCategory.CONTACT_INFO,
        aliases=("company_email", "corporate_email"),
        description="Email corporativo",
    ),
    "phone": VariableMapping(
        crm_field="phone",
        category=FieldCategory.CONTACT_INFO,
        aliases=("company_phone", "corporate_phone", "office_phone"),
        transform="phone_format",
        description="Telefone corporativo",
    ),
    "website": VariableMapping(
        crm_field="website",
        category=FieldCategory.CONTACT_INFO,
        aliases=("site", "url", "company_website"),
        description="Website da empresa",
    ),
    "industry": VariableMapping(
        crm_field="industry",
        category=FieldCategory.BUSINESS,
        aliases=("setor", "segment", "vertical", "ramo"),
        description="Setor/indústria",
    ),
    "number_of_employees": VariableMapping(
        crm_field="number_of_employees",
        category=FieldCategory.BUSINESS,
        aliases=("employees", "headcount", "num_employees", "funcionarios"),
        transform="number",
        description="Número de funcionários",
    ),
    "annual_revenue": VariableMapping(
        crm_field="annual_revenue",
        category=FieldCategory.BUSINESS,
        aliases=("revenue", "faturamento", "receita_anual"),
        transform="number",
        description="Receita anual",
    ),
    "currency": VariableMapping(
        crm_field="currency",
        category=FieldCategory.BUSINESS,
        aliases=("moeda", "currency_code"),
        description="Moeda (ISO 4217)",
    ),
    "address_line": VariableMapping(
        crm_field="address_line",
        category=FieldCategory.ADDRESS,
        aliases=("endereco", "address", "company_address"),
        description="Endereço da empresa",
    ),
    "city": VariableMapping(
        crm_field="city",
        category=FieldCategory.ADDRESS,
        aliases=("cidade",),
        description="Cidade",
    ),
    "state": VariableMapping(
        crm_field="state",
        category=FieldCategory.ADDRESS,
        aliases=("estado", "uf"),
        description="Estado",
    ),
    "postcode": VariableMapping(
        crm_field="postcode",
        category=FieldCategory.ADDRESS,
        aliases=("cep", "zip"),
        description="CEP",
    ),
    "country": VariableMapping(
        crm_field="country",
        category=FieldCategory.ADDRESS,
        aliases=("pais",),
        description="País",
    ),
    "description": VariableMapping(
        crm_field="description",
        category=FieldCategory.SYSTEM,
        aliases=("notas", "notes", "about"),
        description="Notas sobre a empresa",
    ),
}


# ─── LEAD → CONTACT CONVERSION MAP ──────────────────────────────────────────
# Campos do Lead que mapeiam diretamente para Contact na conversão

LEAD_TO_CONTACT_MAP: dict[str, str] = {
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "phone": "phone",
    "job_title": "title",
    "company_name": "organization",
    "address_line": "address_line",
    "city": "city",
    "state": "state",
    "postcode": "postcode",
    "country": "country",
    "description": "description",
    "linkedin_url": "linkedin_url",
}

# Campos do Lead que mapeiam para Account na conversão
LEAD_TO_ACCOUNT_MAP: dict[str, str] = {
    "company_name": "name",
    "website": "website",
    "industry": "industry",
    "address_line": "address_line",
    "city": "city",
    "state": "state",
    "postcode": "postcode",
    "country": "country",
}


# ─── ALIAS INDEX (built at import time) ──────────────────────────────────────

def _build_alias_index(schema: dict[str, VariableMapping]) -> dict[str, str]:
    """Construir índice reverso: alias → canonical_key."""
    index: dict[str, str] = {}
    for key, mapping in schema.items():
        index[key.lower()] = key
        for alias in mapping.aliases:
            index[alias.lower()] = key
    return index


_CONTACT_ALIAS_INDEX = _build_alias_index(CONTACT_SCHEMA)
_ACCOUNT_ALIAS_INDEX = _build_alias_index(ACCOUNT_SCHEMA)


def resolve_variable(entity_type: str, variable_name: str) -> VariableMapping | None:
    """
    Resolver uma variável externa para seu mapeamento canônico.

    Args:
        entity_type: "contact" ou "account"
        variable_name: Nome da variável (aceita aliases)

    Returns:
        VariableMapping ou None se não encontrado.
    """
    name_lower = variable_name.lower().strip()

    if entity_type == "contact":
        canonical = _CONTACT_ALIAS_INDEX.get(name_lower)
        return CONTACT_SCHEMA.get(canonical) if canonical else None
    elif entity_type == "account":
        canonical = _ACCOUNT_ALIAS_INDEX.get(name_lower)
        return ACCOUNT_SCHEMA.get(canonical) if canonical else None

    return None


def resolve_to_crm_field(entity_type: str, variable_name: str) -> str | None:
    """
    Resolver variável externa diretamente para o nome do campo CRM.

    Args:
        entity_type: "contact" ou "account"
        variable_name: Nome da variável (aceita aliases)

    Returns:
        Nome do campo CRM ou None.
    """
    mapping = resolve_variable(entity_type, variable_name)
    return mapping.crm_field if mapping else None


def get_all_aliases(entity_type: str) -> dict[str, list[str]]:
    """Retornar todos os aliases agrupados por campo canônico."""
    schema = CONTACT_SCHEMA if entity_type == "contact" else ACCOUNT_SCHEMA
    return {key: list(m.aliases) for key, m in schema.items()}


def get_required_fields(entity_type: str) -> list[str]:
    """Retornar campos obrigatórios para a entidade."""
    schema = CONTACT_SCHEMA if entity_type == "contact" else ACCOUNT_SCHEMA
    return [key for key, m in schema.items() if m.required]


def get_unique_fields(entity_type: str) -> list[str]:
    """Retornar campos com constraint unique_per_org."""
    schema = CONTACT_SCHEMA if entity_type == "contact" else ACCOUNT_SCHEMA
    return [key for key, m in schema.items() if m.unique_per_org]
