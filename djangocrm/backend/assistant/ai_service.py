"""
AI-assisted config generation for the autopilot system.

Uses OpenAI GPT-4o to translate natural language descriptions into
structured JSON configs for automations, reminders, and campaigns.
"""

import json
import logging

from django.conf import settings

from .template_engine import ALLOWED_VARIABLES

logger = logging.getLogger(__name__)

# ── Schemas for the LLM system prompts ──────────────────────────────────

AUTOMATION_SCHEMAS = {
    "routine": {
        "description": "Rotina agendada que executa uma ação periodicamente",
        "config_fields": {
            "schedule_cron": "Intervalo em minutos (ex: 60) OU expressão cron (ex: '0 9 * * 1-5' = 9h seg-sex)",
            "action_type": "Tipo da ação: send_notification | send_email | create_task | update_field",
            "action_params": "Parâmetros da ação (dependem do action_type)",
        },
        "action_params_examples": {
            "send_notification": {"message": "Texto da notificação"},
            "send_email": {"to": "email@exemplo.com", "subject": "Assunto", "body": "Corpo do email"},
            "create_task": {"title": "Título da tarefa", "description": "Descrição", "priority": "High"},
            "update_field": {"app_label": "leads", "field_name": "status", "new_value": "contacted"},
        },
    },
    "logic_rule": {
        "description": "Regra condicional disparada por eventos do CRM",
        "config_fields": {
            "trigger_event": "Evento gatilho",
            "conditions": "Lista de condições (AND)",
            "actions": "Lista de ações a executar em sequência",
        },
        "trigger_events": [
            "lead.created", "lead.status_changed",
            "opportunity.created", "opportunity.stage_changed",
            "case.created", "task.completed", "contact.created",
        ],
        "condition_operators": ["equals", "not_equals", "contains", "greater_than", "less_than", "is_empty", "is_not_empty"],
        "action_types": ["send_notification", "send_email", "create_task", "update_field"],
    },
    "social": {
        "description": "Automação de canais de mensageria (WhatsApp, Instagram, etc.)",
        "config_fields": {
            "channel_type": "Canal: whatsapp | instagram | facebook | telegram",
            "social_event": "Evento: message_received | message_read | contact_started | contact_opted_out",
            "actions": "Lista de ações a executar",
        },
        "action_types": ["auto_reply", "assign_to_user", "create_lead", "add_tag", "send_to_automation_router"],
    },
}

REMINDER_SCHEMA = {
    "trigger_types": {
        "due_date": {
            "description": "Disparar em datas relativas a um campo de data (antes/depois do vencimento)",
            "required_fields": {"date_field": "Nome do campo de data", "offsets": "Lista de dias (negativos=antes, 0=no dia, positivos=depois)"},
        },
        "recurring": {
            "description": "Repetir a cada N dias a partir de uma data",
            "required_fields": {"interval_days": "Intervalo em dias", "max_runs": "Máximo de execuções", "start_after": "Campo de data de referência"},
        },
        "cron": {
            "description": "Expressão cron para agendamento preciso",
            "required_fields": {"cron_expression": "Expressão cron (ex: '0 9 * * 1-5')"},
        },
    },
    "channel_types": ["internal", "smtp_native"],
    "destination_types": ["owner_email", "contact_email", "assigned_email", "contact_phone"],
    "approval_policies": ["auto", "manual"],
    "date_fields_by_module": {
        "financeiro": ["data_vencimento"],
        "leads": ["next_follow_up", "last_contacted", "created_at"],
        "opportunity": ["closed_on", "stage_changed_at", "created_at"],
        "cases": ["created_at"],
        "tasks": ["due_date", "created_at"],
        "invoices": ["due_date", "created_at"],
    },
}

CAMPAIGN_SCHEMAS = {
    "email_blast": {
        "description": "Disparo em massa de email",
        "fields": {"name": "Nome da campanha", "subject": "Assunto do email", "body_template": "Corpo HTML do email"},
    },
    "whatsapp_broadcast": {
        "description": "Disparo em massa via WhatsApp",
        "fields": {"name": "Nome da campanha", "body_template": "Texto da mensagem WhatsApp"},
    },
    "nurture_sequence": {
        "description": "Sequência automatizada de mensagens com intervalos",
        "fields": {
            "name": "Nome da campanha",
            "steps": "Lista de etapas com: step_order, channel (email|whatsapp), subject (se email), body_template, delay_hours",
        },
    },
}

CAMPAIGN_VARIABLES = [
    "contact.first_name", "contact.last_name", "contact.email", "contact.organization",
]

# ── Preset examples for few-shot learning ────────────────────────────────

PRESET_EXAMPLES = {
    "financeiro": {
        "due_date": {
            "name": "Lembrete padrão - Contas a Receber",
            "trigger_type": "due_date",
            "trigger_config": {"date_field": "data_vencimento", "offsets": [-7, -3, 0, 1, 3]},
            "channel_config": {"channel_type": "internal", "destination_type": "owner_email"},
            "task_config": {"enabled": True, "mode": "per_run", "title_template": "Cobrança: {{contact_name}} - {{amount}} {{currency}}", "priority": "High"},
            "message_template": "Lembrete de cobrança: {{contact_name}} — {{amount}} {{currency}} vence em {{due_date}}.",
            "approval_policy": "auto",
        },
        "recurring": {
            "name": "Cobrança recorrente",
            "trigger_type": "recurring",
            "trigger_config": {"interval_days": 3, "max_runs": 10, "start_after": "data_vencimento"},
            "channel_config": {"channel_type": "internal", "destination_type": "owner_email"},
            "task_config": {"enabled": True, "mode": "per_run", "title_template": "Cobrança pendente: {{contact_name}}", "priority": "High"},
            "message_template": "Cobrança pendente: {{contact_name}} — {{amount}} {{currency}} está {{days_overdue}} dias em atraso.",
            "approval_policy": "auto",
        },
    },
    "leads": {
        "due_date": {
            "name": "Follow-up automático",
            "trigger_type": "due_date",
            "trigger_config": {"date_field": "next_follow_up", "offsets": [-1, 0, 1]},
            "channel_config": {"channel_type": "internal", "destination_type": "owner_email"},
            "task_config": {"enabled": True, "mode": "per_run", "title_template": "Follow-up: {{lead_name}}", "priority": "High"},
            "message_template": "Lembrete de follow-up: {{lead_name}} ({{lead_status}}). Responsável: {{assigned_to}}.",
            "approval_policy": "auto",
        },
    },
}

AUTOMATION_EXAMPLES = {
    "logic_rule": {
        "name": "Notificar quando lead criado",
        "config_json": {
            "trigger_event": "lead.created",
            "conditions": [],
            "actions": [{"action_type": "send_notification", "action_params": {"message": "Novo lead criado: verifique e entre em contato."}}],
        },
    },
    "routine": {
        "name": "Relatório diário 9h",
        "config_json": {
            "schedule_cron": "0 9 * * 1-5",
            "action_type": "send_notification",
            "action_params": {"message": "Bom dia! Lembre-se de verificar os leads pendentes."},
        },
    },
}


def _get_client():
    """Get OpenAI client, or None if not configured."""
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.error("Failed to create OpenAI client: %s", e)
        return None


def _call_openai(system_prompt, user_prompt, model="gpt-4o", temperature=0.3, max_tokens=2000):
    """Call OpenAI API and return parsed JSON response."""
    client = _get_client()
    if not client:
        return {"error": "IA não configurada. Defina OPENAI_API_KEY nas variáveis de ambiente."}

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error("OpenAI returned non-JSON response")
        return {"error": "A IA retornou uma resposta inválida. Tente reformular o pedido."}
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        return {"error": f"Erro ao chamar a IA: {str(e)}"}


# ── Public generation functions ──────────────────────────────────────────

def generate_automation_config(prompt, automation_type="logic_rule", module=None):
    """Generate an automation config from natural language."""
    schema = AUTOMATION_SCHEMAS.get(automation_type)
    if not schema:
        return {"error": f"Tipo de automação inválido: {automation_type}"}

    example = AUTOMATION_EXAMPLES.get(automation_type, {})

    # Build variables list for context
    variables = []
    if module and module in ALLOWED_VARIABLES:
        variables = ALLOWED_VARIABLES[module]

    system_prompt = f"""Você é um assistente de CRM que gera configurações de automação em JSON.
Gere APENAS JSON válido no formato especificado.

## Tipo de automação: {automation_type}
{schema['description']}

## Campos de configuração:
{json.dumps(schema['config_fields'], indent=2, ensure_ascii=False)}

## Tipos de ação disponíveis:
{json.dumps(schema.get('action_types', schema.get('action_params_examples', {}).keys().__class__(schema.get('action_params_examples', {}).keys())), ensure_ascii=False)}

{'## Eventos gatilho: ' + json.dumps(schema.get('trigger_events', []), ensure_ascii=False) if 'trigger_events' in schema else ''}

{'## Operadores de condição: ' + json.dumps(schema.get('condition_operators', []), ensure_ascii=False) if 'condition_operators' in schema else ''}

{'## Variáveis de template disponíveis para ' + module + ': ' + json.dumps(variables, ensure_ascii=False) if variables else ''}

## Exemplo de resposta:
{json.dumps(example, indent=2, ensure_ascii=False)}

## Regras:
1. Responda SEMPRE em português do Brasil
2. Retorne JSON com as chaves: "name" (string) e "config_json" (object com a config do tipo {automation_type})
3. O nome deve ser descritivo e curto (máx 60 chars)
4. Use variáveis de template com sintaxe {{{{variavel}}}} nas mensagens
5. Para condições, use campos reais do CRM (status, priority, source, email, phone, etc.)
6. Seja preciso: se o usuário pede "a cada hora", use schedule_cron: 60 (minutos) ou "0 * * * *" (cron)"""

    return _call_openai(system_prompt, prompt)


def generate_reminder_config(prompt, module_key="financeiro", tipo=None):
    """Generate a reminder policy config from natural language."""
    # Get module-specific variables and date fields
    variables = ALLOWED_VARIABLES.get(module_key, []) + ALLOWED_VARIABLES.get("system", [])
    date_fields = REMINDER_SCHEMA["date_fields_by_module"].get(module_key, [])
    examples = PRESET_EXAMPLES.get(module_key, {})

    tipo_context = ""
    if tipo:
        tipo_context = f"\nContexto: o lançamento é do tipo {tipo} (RECEBER = receita/cobrança, PAGAR = despesa/pagamento)."

    system_prompt = f"""Você é um assistente de CRM que gera configurações de lembrete automático em JSON.
Gere APENAS JSON válido no formato especificado.

## Módulo: {module_key}
{tipo_context}

## Tipos de gatilho disponíveis:
{json.dumps(REMINDER_SCHEMA['trigger_types'], indent=2, ensure_ascii=False)}

## Campos de data disponíveis para {module_key}: {json.dumps(date_fields, ensure_ascii=False)}

## Canais: {json.dumps(REMINDER_SCHEMA['channel_types'], ensure_ascii=False)}
## Destinos: {json.dumps(REMINDER_SCHEMA['destination_types'], ensure_ascii=False)}
## Políticas de aprovação: {json.dumps(REMINDER_SCHEMA['approval_policies'], ensure_ascii=False)}

## Variáveis de template disponíveis: {json.dumps(variables, ensure_ascii=False)}

## Exemplos de configuração para {module_key}:
{json.dumps(examples, indent=2, ensure_ascii=False)}

## Formato de resposta esperado:
{{
  "name": "Nome do lembrete (curto, descritivo)",
  "trigger_type": "due_date | recurring | cron",
  "trigger_config": {{ ... }},
  "channel_config": {{ "channel_type": "internal | smtp_native", "destination_type": "..." }},
  "task_config": {{ "enabled": true/false, "mode": "per_run | persistent", "title_template": "...", "priority": "High | Medium | Low" }},
  "message_template": "Mensagem com {{{{variáveis}}}}",
  "approval_policy": "auto | manual"
}}

## Regras:
1. Responda SEMPRE em português do Brasil
2. Use APENAS variáveis da lista de variáveis disponíveis
3. Para offsets: negativo = antes do vencimento, 0 = no dia, positivo = depois
4. Para email ao contato externo, use channel_type "smtp_native" e approval_policy "manual"
5. Para notificações internas, use channel_type "internal" e destination_type "owner_email"
6. Gere task_config.enabled=true quando o usuário mencionar "criar tarefa" ou "gerar tarefa"
7. O nome deve ter no máximo 60 caracteres"""

    return _call_openai(system_prompt, prompt)


def generate_campaign_content(prompt, campaign_type="email_blast"):
    """Generate campaign content from natural language."""
    schema = CAMPAIGN_SCHEMAS.get(campaign_type)
    if not schema:
        return {"error": f"Tipo de campanha inválido: {campaign_type}"}

    variables_str = json.dumps(CAMPAIGN_VARIABLES, ensure_ascii=False)

    nurture_example = ""
    if campaign_type == "nurture_sequence":
        nurture_example = """
## Exemplo de steps para nurture_sequence:
{
  "name": "Sequência de boas-vindas",
  "steps": [
    {"step_order": 1, "channel": "email", "subject": "Bem-vindo!", "body_template": "Olá {{contact.first_name}}, obrigado por se cadastrar!", "delay_hours": 0},
    {"step_order": 2, "channel": "email", "subject": "Primeiros passos", "body_template": "{{contact.first_name}}, aqui estão dicas para começar...", "delay_hours": 24},
    {"step_order": 3, "channel": "whatsapp", "subject": null, "body_template": "Oi {{contact.first_name}}! Precisa de ajuda com algo?", "delay_hours": 72}
  ]
}"""

    system_prompt = f"""Você é um copywriter de CRM que gera conteúdo de campanhas de marketing em JSON.
Gere APENAS JSON válido no formato especificado.

## Tipo de campanha: {campaign_type}
{schema['description']}

## Campos: {json.dumps(schema['fields'], indent=2, ensure_ascii=False)}

## Variáveis disponíveis: {variables_str}
Use a sintaxe {{{{contact.first_name}}}}, {{{{contact.last_name}}}}, etc.

{nurture_example}

## Formato de resposta para {campaign_type}:
{{"name": "Nome da campanha", "subject": "Assunto (somente para email)", "body_template": "Conteúdo...", "steps": [...] (somente para nurture_sequence)}}

## Regras:
1. Responda SEMPRE em português do Brasil
2. O tom deve ser profissional mas amigável
3. Para email_blast: body_template pode ter HTML simples (<h1>, <p>, <a>, <strong>)
4. Para whatsapp_broadcast: body_template deve ser texto puro (sem HTML), máx 1000 chars
5. Para nurture_sequence: gere 2-5 steps com delays progressivos (0, 24, 48-72h)
6. Use {{{{contact.first_name}}}} para personalização
7. O nome da campanha deve ter no máximo 60 caracteres
8. Para email, gere um subject atraente e conciso (máx 80 chars)"""

    return _call_openai(system_prompt, prompt)
