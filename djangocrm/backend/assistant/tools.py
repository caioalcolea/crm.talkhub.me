"""
Tool Registry for the AI Assistant.

Each tool is a thin wrapper around existing CRM actions, returning structured
results with risk classification and optional approval requirements.

Tools follow the pattern:
  fn(org, user, params) -> {result, warnings, requires_approval, diff, error}
"""

import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Tool implementations ──────────────────────────────────────────────


def create_reminder_policy(org, user, params):
    """Create a reminder policy as inactive draft."""
    from assistant.models import ReminderPolicy

    target_type = params.get("target_type", "")
    target_id = params.get("target_object_id")

    try:
        app_label, model = target_type.split(".")
        ct = ContentType.objects.get(app_label=app_label, model=model)
    except (ValueError, ContentType.DoesNotExist):
        return {"error": f"Tipo de entidade inválido: {target_type}"}

    policy = ReminderPolicy.objects.create(
        org=org,
        owner_user=user,
        name=params.get("name", "Novo lembrete"),
        description=params.get("description", ""),
        target_content_type=ct,
        target_object_id=target_id,
        module_key=params.get("module_key", app_label),
        is_active=False,  # Always create as draft
        trigger_type=params.get("trigger_type", "due_date"),
        trigger_config=params.get("trigger_config", {}),
        channel_config=params.get("channel_config", {}),
        task_config=params.get("task_config", {}),
        message_template=params.get("message_template", ""),
        approval_policy=params.get("approval_policy", "auto"),
    )

    return {
        "result": {
            "id": str(policy.id),
            "name": policy.name,
            "status": "inactive_draft",
        },
        "warnings": [],
    }


def preview_policy_schedule(org, user, params):
    """Preview next N executions of a policy (read-only)."""
    from assistant.engine import calculate_next_run
    from assistant.models import ReminderPolicy

    policy_id = params.get("policy_id")
    n = min(params.get("count", 5), 20)

    try:
        policy = ReminderPolicy.objects.get(pk=policy_id, org=org)
    except ReminderPolicy.DoesNotExist:
        return {"error": "Política não encontrada."}

    runs = []
    current = timezone.now()
    for _ in range(n):
        next_run = calculate_next_run(policy, after=current)
        if not next_run:
            break
        runs.append(next_run.isoformat())
        current = next_run + timedelta(seconds=1)

    return {
        "result": {
            "policy_name": policy.name,
            "next_runs": runs,
            "total_preview": len(runs),
        },
        "warnings": [],
    }


def activate_policy(org, user, params):
    """Activate a reminder policy."""
    from assistant.models import ReminderPolicy

    policy_id = params.get("policy_id")
    try:
        policy = ReminderPolicy.objects.get(pk=policy_id, org=org)
    except ReminderPolicy.DoesNotExist:
        return {"error": "Política não encontrada."}

    policy.is_active = True
    policy.save(update_fields=["is_active", "updated_at"])

    from assistant.tasks import recalculate_policy_schedules
    recalculate_policy_schedules.delay(str(policy.id))

    return {
        "result": {
            "id": str(policy.id),
            "name": policy.name,
            "status": "active",
        },
        "warnings": [],
    }


def deactivate_policy(org, user, params):
    """Deactivate a reminder policy."""
    from assistant.models import ReminderPolicy

    policy_id = params.get("policy_id")
    try:
        policy = ReminderPolicy.objects.get(pk=policy_id, org=org)
    except ReminderPolicy.DoesNotExist:
        return {"error": "Política não encontrada."}

    policy.is_active = False
    policy.save(update_fields=["is_active", "updated_at"])

    return {
        "result": {"id": str(policy.id), "name": policy.name, "status": "inactive"},
        "warnings": [],
    }


def cancel_job(org, user, params):
    """Cancel a pending scheduled job."""
    from assistant.models import ScheduledJob

    job_id = params.get("job_id")
    try:
        job = ScheduledJob.objects.get(pk=job_id, org=org)
    except ScheduledJob.DoesNotExist:
        return {"error": "Job não encontrado."}

    if job.status != "pending":
        return {"error": f"Job não pode ser cancelado (status: {job.status})."}

    job.status = "cancelled"
    job.save(update_fields=["status", "updated_at"])

    return {
        "result": {"id": str(job.id), "status": "cancelled"},
        "warnings": [],
    }


def retry_job(org, user, params):
    """Retry a failed scheduled job."""
    from assistant.models import ScheduledJob

    job_id = params.get("job_id")
    try:
        job = ScheduledJob.objects.get(pk=job_id, org=org)
    except ScheduledJob.DoesNotExist:
        return {"error": "Job não encontrado."}

    if job.status not in ("failed", "cancelled"):
        return {"error": f"Job não pode ser retentado (status: {job.status})."}

    job.status = "pending"
    job.last_error = ""
    job.save(update_fields=["status", "last_error", "updated_at"])

    return {
        "result": {"id": str(job.id), "status": "pending"},
        "warnings": [],
    }


def create_automation(org, user, params):
    """Create an automation rule."""
    from automations.models import Automation

    automation = Automation.objects.create(
        org=org,
        name=params.get("name", "Nova automação"),
        automation_type=params.get("automation_type", "logic_rule"),
        config_json=params.get("config_json", {}),
        is_active=False,  # Always create as draft
    )

    return {
        "result": {
            "id": str(automation.id),
            "name": automation.name,
            "status": "inactive_draft",
        },
        "warnings": [],
    }


def create_campaign_draft(org, user, params):
    """Create a campaign in draft status."""
    from campaigns.models import Campaign

    campaign = Campaign.objects.create(
        org=org,
        name=params.get("name", "Nova campanha"),
        campaign_type=params.get("campaign_type", "email_blast"),
        subject=params.get("subject", ""),
        body_template=params.get("body_template", ""),
        status="draft",
    )

    return {
        "result": {
            "id": str(campaign.id),
            "name": campaign.name,
            "status": "draft",
        },
        "warnings": [],
    }


def render_template_preview(org, user, params):
    """Render a message template with sample data (read-only)."""
    from assistant.template_engine import render_template

    template = params.get("template", "")
    module_key = params.get("module_key", "system")
    entity_id = params.get("entity_id")

    # Build context from entity if provided
    context = {}
    if entity_id:
        try:
            from assistant.tasks import _build_context_for_job

            # Try to resolve entity and build context using module-specific builders
            module_builders = {
                "financeiro": ("financeiro", "parcela"),
                "leads": ("leads", "lead"),
                "tasks": ("tasks", "task"),
                "opportunity": ("opportunity", "opportunity"),
                "cases": ("cases", "case"),
                "invoices": ("invoices", "invoice"),
            }
            if module_key in module_builders:
                app_label, model_name = module_builders[module_key]
                from django.contrib.contenttypes.models import ContentType

                ct = ContentType.objects.get(app_label=app_label, model=model_name)
                model_class = ct.model_class()
                if model_class:
                    entity = model_class.objects.filter(pk=entity_id, org=org).first()
                    if entity:
                        model_name_lower = model_class.__name__.lower()
                        if model_name_lower == "parcela":
                            from assistant.template_engine import build_context_for_parcela
                            context = build_context_for_parcela(entity)
                        elif model_name_lower == "lead":
                            from assistant.template_engine import build_context_for_lead
                            context = build_context_for_lead(entity)
                        elif model_name_lower == "task":
                            from assistant.template_engine import build_context_for_task
                            context = build_context_for_task(entity)
                        elif model_name_lower == "opportunity":
                            from assistant.template_engine import build_context_for_opportunity
                            context = build_context_for_opportunity(entity)
                        elif model_name_lower == "case":
                            from assistant.template_engine import build_context_for_case
                            context = build_context_for_case(entity)
                        elif model_name_lower == "invoice":
                            from assistant.template_engine import build_context_for_invoice
                            context = build_context_for_invoice(entity)
        except Exception:
            pass  # Render with empty context if entity resolution fails

    try:
        rendered = render_template(template, context, module_key)
        return {
            "result": {"rendered": rendered, "original": template},
            "warnings": [],
        }
    except Exception as e:
        return {"error": f"Erro ao renderizar template: {str(e)}"}


def list_entity_reminders(org, user, params):
    """List reminders for an entity (read-only)."""
    from assistant.models import ReminderPolicy

    target_type = params.get("target_type", "")
    target_id = params.get("target_id")

    try:
        app_label, model = target_type.split(".")
        ct = ContentType.objects.get(app_label=app_label, model=model)
    except (ValueError, ContentType.DoesNotExist):
        return {"error": f"Tipo de entidade inválido: {target_type}"}

    policies = ReminderPolicy.objects.filter(
        org=org, target_content_type=ct, target_object_id=target_id
    ).values("id", "name", "trigger_type", "is_active", "next_run_at")

    return {
        "result": {"reminders": list(policies), "count": len(policies)},
        "warnings": [],
    }


def search_contacts(org, user, params):
    """Search contacts by name, email or phone (read-only)."""
    from contacts.models import Contact

    query = params.get("query", "").strip()
    if not query or len(query) < 2:
        return {"error": "Busca requer ao menos 2 caracteres."}

    from django.db.models import Q

    contacts = (
        Contact.objects.filter(org=org)
        .filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
        .values("id", "first_name", "last_name", "email", "phone")[:20]
    )

    return {
        "result": {"contacts": list(contacts), "count": len(contacts)},
        "warnings": [],
    }


def search_lancamentos(org, user, params):
    """Search financial transactions (read-only)."""
    from financeiro.models import Lancamento

    filters = {"org": org}

    tipo = params.get("tipo")
    if tipo:
        filters["tipo"] = tipo

    status = params.get("status")
    if status:
        filters["parcelas__status"] = status

    vencendo_dias = params.get("vencendo_em_dias")
    if vencendo_dias:
        filters["parcelas__data_vencimento__lte"] = timezone.now().date() + timedelta(
            days=int(vencendo_dias)
        )
        filters["parcelas__data_vencimento__gte"] = timezone.now().date()

    lancamentos = (
        Lancamento.objects.filter(**filters)
        .distinct()
        .values("id", "descricao", "tipo", "valor_total", "status")[:20]
    )

    return {
        "result": {"lancamentos": list(lancamentos), "count": len(lancamentos)},
        "warnings": [],
    }


# ── Tool Registry ────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "create_reminder_policy": {
        "fn": create_reminder_policy,
        "risk": "low",
        "description": "Cria uma política de lembrete (rascunho inativo)",
        "requires_approval": False,
        "params_schema": {
            "target_type": "string (app_label.model)",
            "target_object_id": "uuid",
            "name": "string",
            "module_key": "string",
            "trigger_type": "due_date|recurring|cron",
            "trigger_config": "object",
            "channel_config": "object",
            "task_config": "object",
            "message_template": "string",
        },
    },
    "preview_policy_schedule": {
        "fn": preview_policy_schedule,
        "risk": "none",
        "description": "Mostra as próximas N execuções de uma policy (somente leitura)",
        "requires_approval": False,
        "params_schema": {"policy_id": "uuid", "count": "int (default 5)"},
    },
    "activate_policy": {
        "fn": activate_policy,
        "risk": "medium",
        "description": "Ativa uma política de lembrete — começa a gerar jobs",
        "requires_approval": False,
        "params_schema": {"policy_id": "uuid"},
    },
    "deactivate_policy": {
        "fn": deactivate_policy,
        "risk": "low",
        "description": "Desativa uma política de lembrete",
        "requires_approval": False,
        "params_schema": {"policy_id": "uuid"},
    },
    "cancel_job": {
        "fn": cancel_job,
        "risk": "low",
        "description": "Cancela um job pendente",
        "requires_approval": False,
        "params_schema": {"job_id": "uuid"},
    },
    "retry_job": {
        "fn": retry_job,
        "risk": "low",
        "description": "Retenta um job que falhou",
        "requires_approval": False,
        "params_schema": {"job_id": "uuid"},
    },
    "create_automation": {
        "fn": create_automation,
        "risk": "low",
        "description": "Cria uma regra de automação (rascunho inativo)",
        "requires_approval": False,
        "params_schema": {
            "name": "string",
            "automation_type": "logic_rule|routine|social",
            "config_json": "object",
        },
    },
    "create_campaign_draft": {
        "fn": create_campaign_draft,
        "risk": "medium",
        "description": "Cria uma campanha em rascunho",
        "requires_approval": True,
        "params_schema": {
            "name": "string",
            "campaign_type": "email_blast|whatsapp_broadcast|nurture_sequence",
            "subject": "string",
            "body_template": "string",
        },
    },
    "render_template_preview": {
        "fn": render_template_preview,
        "risk": "none",
        "description": "Renderiza preview de um template com variáveis reais",
        "requires_approval": False,
        "params_schema": {
            "template": "string",
            "module_key": "string",
            "entity_id": "uuid (optional)",
        },
    },
    "list_entity_reminders": {
        "fn": list_entity_reminders,
        "risk": "none",
        "description": "Lista lembretes de uma entidade (somente leitura)",
        "requires_approval": False,
        "params_schema": {"target_type": "string (app_label.model)", "target_id": "uuid"},
    },
    "search_contacts": {
        "fn": search_contacts,
        "risk": "none",
        "description": "Busca contatos por nome, email ou telefone",
        "requires_approval": False,
        "params_schema": {"query": "string (min 2 chars)"},
    },
    "search_lancamentos": {
        "fn": search_lancamentos,
        "risk": "none",
        "description": "Busca lançamentos financeiros",
        "requires_approval": False,
        "params_schema": {
            "tipo": "RECEBER|PAGAR (optional)",
            "status": "ABERTO|PAGO|CANCELADO (optional)",
            "vencendo_em_dias": "int (optional)",
        },
    },
}


def get_tool(name):
    """Get a tool definition by name. Returns None if not found."""
    return TOOL_REGISTRY.get(name)


def execute_tool(name, org, user, params):
    """Execute a registered tool safely."""
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return {"error": f"Ferramenta desconhecida: {name}"}

    try:
        result = tool["fn"](org, user, params)
        if "error" not in result:
            result.setdefault("warnings", [])
            result.setdefault("requires_approval", tool.get("requires_approval", False))
        return result
    except Exception as e:
        logger.exception("Tool execution error: %s", name)
        return {"error": f"Erro ao executar {name}: {str(e)}"}


def get_tools_for_llm():
    """Return tool descriptions formatted for the LLM system prompt."""
    tools = []
    for name, tool in TOOL_REGISTRY.items():
        tools.append({
            "name": name,
            "description": tool["description"],
            "risk": tool["risk"],
            "params": tool["params_schema"],
        })
    return tools
