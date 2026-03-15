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

# All presets indexed by module
ALL_PRESETS = {
    "financeiro": FINANCEIRO_PRESETS,
}


def get_presets_for_module(module_key):
    """Return available presets for a given module."""
    return ALL_PRESETS.get(module_key, {})
