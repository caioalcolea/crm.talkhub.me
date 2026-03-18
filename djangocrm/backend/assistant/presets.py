"""
Preset configurations for common reminder/automation patterns.

Presets provide one-click setup for common use cases.
"""

FINANCEIRO_PRESETS = {
    "contas_receber_padrao": {
        "name": "Lembrete padrão - Contas a Receber",
        "description": "Lembretes automáticos: 7 dias antes, 3 dias antes, no vencimento, 1 dia após e 3 dias após",
        "trigger_type": "due_date",
        "trigger_config": {
            "date_field": "data_vencimento",
            "offsets": [-7, -3, 0, 1, 3],
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {
            "enabled": True,
            "mode": "per_run",
            "title_template": "Cobrança: {{contact_name}} - {{amount}} {{currency}}",
            "description_template": "Parcela {{parcela_number}} de {{lancamento_descricao}} com vencimento em {{due_date}}. Valor: {{amount}} {{currency}}",
            "priority": "High",
        },
        "message_template": "Lembrete de cobrança: {{contact_name}} — {{amount}} {{currency}} vence em {{due_date}}. Parcela {{parcela_number}} de {{lancamento_descricao}}.",
        "approval_policy": "auto",
    },
    "contas_receber_email": {
        "name": "Lembrete por email - Contas a Receber",
        "description": "Envia email ao contato: 5 dias antes, no vencimento e 2 dias após",
        "trigger_type": "due_date",
        "trigger_config": {
            "date_field": "data_vencimento",
            "offsets": [-5, 0, 2],
        },
        "channel_config": {
            "channel_type": "smtp_native",
            "destination_type": "contact_email",
        },
        "task_config": {"enabled": False},
        "message_template": "Olá {{contact_name}}, este é um lembrete sobre o valor de {{amount}} {{currency}} com vencimento em {{due_date}}.",
        "approval_policy": "manual",
    },
    "contas_pagar_padrao": {
        "name": "Lembrete padrão - Contas a Pagar",
        "description": "Lembretes internos: 5 dias antes, 1 dia antes e no vencimento",
        "trigger_type": "due_date",
        "trigger_config": {
            "date_field": "data_vencimento",
            "offsets": [-5, -1, 0],
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {
            "enabled": True,
            "mode": "per_run",
            "title_template": "Pagar: {{account_name}} - {{amount}} {{currency}}",
            "description_template": "Parcela {{parcela_number}} de {{lancamento_descricao}} vence em {{due_date}}.",
            "priority": "Medium",
        },
        "message_template": "Lembrete de pagamento: {{account_name}} — {{amount}} {{currency}} vence em {{due_date}}.",
        "approval_policy": "auto",
    },
    "cobranca_recorrente": {
        "name": "Cobrança recorrente",
        "description": "Envia lembrete a cada 3 dias até máximo de 10 vezes após o vencimento",
        "trigger_type": "recurring",
        "trigger_config": {
            "interval_days": 3,
            "max_runs": 10,
            "start_after": "data_vencimento",
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {
            "enabled": True,
            "mode": "per_run",
            "title_template": "Cobrança pendente: {{contact_name}} - {{amount}} {{currency}}",
            "priority": "High",
        },
        "message_template": "Cobrança pendente: {{contact_name}} — {{amount}} {{currency}} está {{days_overdue}} dias em atraso.",
        "approval_policy": "auto",
    },
}

LEADS_PRESETS = {
    "follow_up_padrao": {
        "name": "Follow-up automático",
        "description": "Lembretes: 1 dia antes, no dia e 1 dia após o follow-up agendado",
        "trigger_type": "due_date",
        "trigger_config": {
            "date_field": "next_follow_up",
            "offsets": [-1, 0, 1],
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {
            "enabled": True,
            "mode": "per_run",
            "title_template": "Follow-up: {{lead_name}}",
            "priority": "High",
        },
        "message_template": "Lembrete de follow-up: {{lead_name}} ({{lead_status}}). Responsável: {{assigned_to}}.",
        "approval_policy": "auto",
    },
    "lead_esfriando": {
        "name": "Lead esfriando",
        "description": "Alerta a cada 5 dias (max 6x) quando lead fica sem contato",
        "trigger_type": "recurring",
        "trigger_config": {
            "interval_days": 5,
            "max_runs": 6,
            "start_after": "last_contacted",
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {
            "enabled": True,
            "mode": "per_run",
            "title_template": "Lead sem contato: {{lead_name}}",
            "priority": "Medium",
        },
        "message_template": "Lead {{lead_name}} está sem contato. Status: {{lead_status}}. Responsável: {{assigned_to}}.",
        "approval_policy": "auto",
    },
}

OPPORTUNITY_PRESETS = {
    "close_date_approaching": {
        "name": "Fechamento se aproximando",
        "description": "Lembretes: 7, 3 e 1 dia antes e no dia do fechamento previsto",
        "trigger_type": "due_date",
        "trigger_config": {
            "date_field": "closed_on",
            "offsets": [-7, -3, -1, 0],
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {
            "enabled": True,
            "mode": "per_run",
            "title_template": "Negócio prestes a fechar: {{opportunity_name}}",
            "priority": "High",
        },
        "message_template": "Oportunidade {{opportunity_name}} ({{opportunity_stage}}) — fechamento previsto em {{close_date}}. Valor: {{amount}} {{currency}}.",
        "approval_policy": "auto",
    },
    "deal_stale": {
        "name": "Negócio parado",
        "description": "Alerta a cada 7 dias (max 4x) quando negócio fica sem avanço de stage",
        "trigger_type": "recurring",
        "trigger_config": {
            "interval_days": 7,
            "max_runs": 4,
            "start_after": "stage_changed_at",
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {
            "enabled": True,
            "mode": "per_run",
            "title_template": "Negócio parado: {{opportunity_name}}",
            "priority": "Medium",
        },
        "message_template": "Oportunidade {{opportunity_name}} está parada no estágio {{opportunity_stage}}. Valor: {{amount}} {{currency}}.",
        "approval_policy": "auto",
    },
}

CASES_PRESETS = {
    "sla_resolution": {
        "name": "SLA de resolução",
        "description": "Alerta a cada 2 dias quando chamado não foi resolvido dentro do SLA",
        "trigger_type": "recurring",
        "trigger_config": {
            "interval_days": 2,
            "max_runs": 5,
            "start_after": "created_at",
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {
            "enabled": True,
            "mode": "per_run",
            "title_template": "SLA: {{case_name}} — {{case_priority}}",
            "priority": "High",
        },
        "message_template": "Chamado {{case_name}} ({{case_priority}}) — SLA de resolução: {{sla_deadline}}. Status: {{case_status}}.",
        "approval_policy": "auto",
    },
    "case_escalation": {
        "name": "Escalonamento automático",
        "description": "Alerta a cada 4 horas se chamado urgente não resolvido (via recorrente diário)",
        "trigger_type": "recurring",
        "trigger_config": {
            "interval_days": 1,
            "max_runs": 10,
            "start_after": "created_at",
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {"enabled": False},
        "message_template": "Chamado {{case_name}} requer atenção. Prioridade: {{case_priority}}. Status: {{case_status}}.",
        "approval_policy": "auto",
    },
}

TASKS_PRESETS = {
    "task_due_date": {
        "name": "Lembrete de prazo",
        "description": "Lembretes: 1 dia antes, no dia e 1 dia após o prazo",
        "trigger_type": "due_date",
        "trigger_config": {
            "date_field": "due_date",
            "offsets": [-1, 0, 1],
            "time_of_day_hour": None,
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "assigned_email",
        },
        "task_config": {"enabled": False},
        "message_template": "Tarefa '{{task_title}}' vence em {{due_date}} {{due_time}}. Prioridade: {{task_priority}}.",
        "approval_policy": "auto",
    },
    "task_overdue": {
        "name": "Tarefa atrasada",
        "description": "Alerta a cada 2 dias (max 5x) quando tarefa fica atrasada",
        "trigger_type": "recurring",
        "trigger_config": {
            "interval_days": 2,
            "max_runs": 5,
            "start_after": "due_date",
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "assigned_email",
        },
        "task_config": {"enabled": False},
        "message_template": "Tarefa '{{task_title}}' está atrasada. Prazo: {{due_date}} {{due_time}}. Status: {{task_status}}.",
        "approval_policy": "auto",
    },
}

INVOICES_PRESETS = {
    "invoice_due_date": {
        "name": "Lembrete de vencimento",
        "description": "Lembretes: 7, 3 dias antes, no vencimento, 1 e 3 dias após",
        "trigger_type": "due_date",
        "trigger_config": {
            "date_field": "due_date",
            "offsets": [-7, -3, 0, 1, 3],
        },
        "channel_config": {
            "channel_type": "internal",
            "destination_type": "owner_email",
        },
        "task_config": {
            "enabled": True,
            "mode": "per_run",
            "title_template": "Fatura {{invoice_number}}: {{contact_name}} - {{amount}} {{currency}}",
            "priority": "High",
        },
        "message_template": "Fatura {{invoice_number}} — {{contact_name}} — {{amount}} {{currency}} vence em {{due_date}}.",
        "approval_policy": "auto",
    },
    "invoice_overdue_email": {
        "name": "Cobrança por email",
        "description": "Envia email a cada 5 dias (max 8x) para faturas vencidas",
        "trigger_type": "recurring",
        "trigger_config": {
            "interval_days": 5,
            "max_runs": 8,
            "start_after": "due_date",
        },
        "channel_config": {
            "channel_type": "smtp_native",
            "destination_type": "contact_email",
        },
        "task_config": {"enabled": False},
        "message_template": "Olá {{contact_name}}, a fatura {{invoice_number}} no valor de {{amount}} {{currency}} está vencida desde {{due_date}}.",
        "approval_policy": "manual",
    },
}

# All presets indexed by module
ALL_PRESETS = {
    "financeiro": FINANCEIRO_PRESETS,
    "leads": LEADS_PRESETS,
    "opportunity": OPPORTUNITY_PRESETS,
    "cases": CASES_PRESETS,
    "tasks": TASKS_PRESETS,
    "invoices": INVOICES_PRESETS,
}


def get_presets_for_module(module_key):
    """Return available presets for a given module."""
    return ALL_PRESETS.get(module_key, {})
