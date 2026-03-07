"""
Engine de LogicRules — avaliação de condições e execução de ações.

Trigger events suportados:
- lead.created, lead.status_changed
- opportunity.created, opportunity.stage_changed
- case.created
- task.completed
- contact.created

Operadores de condição:
- equals, not_equals, contains, greater_than, less_than, is_empty, is_not_empty
"""

import logging

from common.tasks import set_rls_context

logger = logging.getLogger(__name__)

# Eventos válidos para LogicRules
VALID_TRIGGER_EVENTS = [
    "lead.created",
    "lead.status_changed",
    "opportunity.created",
    "opportunity.stage_changed",
    "case.created",
    "task.completed",
    "contact.created",
]

# Operadores válidos
VALID_OPERATORS = [
    "equals",
    "not_equals",
    "contains",
    "greater_than",
    "less_than",
    "is_empty",
    "is_not_empty",
]


def validate_logic_rule_config(config_json):
    """Valida config_json para tipo logic_rule."""
    if not isinstance(config_json, dict):
        return False, "config_json deve ser um dicionário"

    trigger_event = config_json.get("trigger_event")
    if not trigger_event:
        return False, "Campo 'trigger_event' é obrigatório"
    if trigger_event not in VALID_TRIGGER_EVENTS:
        return False, f"trigger_event inválido. Opções: {', '.join(VALID_TRIGGER_EVENTS)}"

    conditions = config_json.get("conditions", [])
    if not isinstance(conditions, list):
        return False, "'conditions' deve ser uma lista"

    for cond in conditions:
        if not isinstance(cond, dict):
            return False, "Cada condição deve ser um dicionário"
        if "field" not in cond:
            return False, "Cada condição deve ter 'field'"
        operator = cond.get("operator")
        if not operator:
            return False, "Cada condição deve ter 'operator'"
        if operator not in VALID_OPERATORS:
            return False, f"Operador inválido: {operator}. Opções: {', '.join(VALID_OPERATORS)}"

    actions = config_json.get("actions", [])
    if not isinstance(actions, list) or not actions:
        return False, "'actions' deve ser uma lista não vazia"

    return True, None


def _evaluate_condition(condition, instance_data):
    """
    Avalia uma condição contra os dados da instância.

    condition: {"field": "status", "operator": "equals", "value": "won"}
    instance_data: dict com campos do model
    """
    field = condition.get("field")
    operator = condition.get("operator")
    expected = condition.get("value")

    actual = instance_data.get(field)

    if operator == "equals":
        return str(actual) == str(expected) if actual is not None else expected is None
    elif operator == "not_equals":
        return str(actual) != str(expected) if actual is not None else expected is not None
    elif operator == "contains":
        return str(expected).lower() in str(actual).lower() if actual else False
    elif operator == "greater_than":
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    elif operator == "less_than":
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False
    elif operator == "is_empty":
        return not actual or actual == "" or actual is None
    elif operator == "is_not_empty":
        return actual is not None and actual != ""
    else:
        return False


def evaluate_conditions(conditions, instance_data):
    """Avalia todas as condições (AND lógico). Retorna True se todas passam."""
    if not conditions:
        return True
    return all(_evaluate_condition(c, instance_data) for c in conditions)


def _get_instance_data(instance):
    """Extrai dados relevantes de uma instância de model como dict."""
    data = {}
    for field in instance._meta.get_fields():
        if hasattr(field, "attname"):
            try:
                value = getattr(instance, field.attname, None)
                data[field.name] = value
                # Também incluir o attname (ex: org_id)
                if field.attname != field.name:
                    data[field.attname] = value
            except Exception:
                pass
    return data


def process_event(event_name, instance, org_id, extra_data=None):
    """
    Processa um evento e despacha LogicRules ativas que correspondem.

    Chamado pelos signals Django. Despacha execução assíncrona via Celery.

    Args:
        event_name: Nome do evento (ex: "lead.created")
        instance: Instância do model que disparou o evento
        org_id: UUID da organização
        extra_data: Dados extras (ex: campo anterior para status_changed)
    """
    from automations.tasks import execute_logic_rule

    instance_data = _get_instance_data(instance)
    if extra_data:
        instance_data.update(extra_data)

    # Buscar LogicRules ativas para este evento e org
    from automations.models import Automation

    rules = Automation.objects.filter(
        org_id=org_id,
        automation_type="logic_rule",
        is_active=True,
    )

    for rule in rules:
        config = rule.config_json
        if config.get("trigger_event") != event_name:
            continue

        # Avaliar condições
        conditions = config.get("conditions", [])
        if evaluate_conditions(conditions, instance_data):
            # Despachar execução assíncrona
            execute_logic_rule.delay(
                str(rule.id),
                str(org_id),
                instance_data={k: str(v) for k, v in instance_data.items() if v is not None},
                event_name=event_name,
            )


# --- SocialAutomations ---

VALID_CHANNEL_TYPES = ["whatsapp", "instagram", "facebook", "telegram"]

VALID_SOCIAL_EVENTS = [
    "message_received",
    "message_read",
    "contact_started",
    "contact_opted_out",
]

VALID_SOCIAL_ACTIONS = [
    "auto_reply",
    "assign_to_user",
    "create_lead",
    "add_tag",
    "send_to_automation_router",
]


def validate_social_config(config_json):
    """Valida config_json para tipo social."""
    if not isinstance(config_json, dict):
        return False, "config_json deve ser um dicionário"

    channel_type = config_json.get("channel_type")
    if not channel_type:
        return False, "Campo 'channel_type' é obrigatório"
    if channel_type not in VALID_CHANNEL_TYPES:
        return False, f"channel_type inválido. Opções: {', '.join(VALID_CHANNEL_TYPES)}"

    social_event = config_json.get("social_event")
    if not social_event:
        return False, "Campo 'social_event' é obrigatório"
    if social_event not in VALID_SOCIAL_EVENTS:
        return False, f"social_event inválido. Opções: {', '.join(VALID_SOCIAL_EVENTS)}"

    actions = config_json.get("actions", [])
    if not isinstance(actions, list) or not actions:
        return False, "'actions' deve ser uma lista não vazia"

    for action in actions:
        action_type = action.get("action_type")
        if action_type not in VALID_SOCIAL_ACTIONS:
            return False, f"action_type inválido: {action_type}. Opções: {', '.join(VALID_SOCIAL_ACTIONS)}"

    return True, None


def process_social_event(social_event, channel_type, org_id, webhook_data):
    """
    Processa um evento social e despacha SocialAutomations ativas.

    Chamado pelos webhook handlers do talkhub_omni.

    Args:
        social_event: Nome do evento (ex: "message_received")
        channel_type: Tipo de canal (ex: "whatsapp")
        org_id: UUID da organização
        webhook_data: Dados do webhook
    """
    from automations.tasks import execute_social_automation
    from automations.models import Automation

    automations = Automation.objects.filter(
        org_id=org_id,
        automation_type="social",
        is_active=True,
    )

    for automation in automations:
        config = automation.config_json
        if config.get("social_event") != social_event:
            continue
        if config.get("channel_type") != channel_type:
            continue

        execute_social_automation.delay(
            str(automation.id),
            str(org_id),
            webhook_data=webhook_data,
            social_event=social_event,
            channel_type=channel_type,
        )
