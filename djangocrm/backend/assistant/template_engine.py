"""
Template engine for variable interpolation in reminder/automation messages.

Uses a whitelist per module to prevent injection of sensitive data.
Variables are referenced as {{variable_name}} in templates.
"""

import re
from datetime import date

# Allowed variables per module (whitelist)
ALLOWED_VARIABLES = {
    "financeiro": [
        "account_name",
        "contact_name",
        "invoice_number",
        "amount",
        "currency",
        "due_date",
        "days_until_due",
        "days_overdue",
        "payment_link",
        "parcela_number",
        "lancamento_descricao",
    ],
    "leads": [
        "lead_name",
        "lead_status",
        "lead_source",
        "assigned_to",
        "lead_email",
        "lead_phone",
    ],
    "cases": [
        "case_name",
        "case_status",
        "case_priority",
        "assigned_to",
        "sla_deadline",
    ],
    "tasks": [
        "task_title",
        "task_status",
        "task_priority",
        "assigned_to",
        "due_date",
    ],
    "invoices": [
        "invoice_number",
        "invoice_status",
        "amount",
        "currency",
        "due_date",
        "contact_name",
        "account_name",
    ],
    "orders": [
        "order_number",
        "order_status",
        "amount",
        "currency",
        "contact_name",
        "account_name",
    ],
    "opportunity": [
        "opportunity_name",
        "opportunity_stage",
        "amount",
        "currency",
        "assigned_to",
        "close_date",
    ],
    "system": [
        "org_name",
        "current_date",
        "channel_name",
    ],
}

# Regex for {{variable}} pattern
_VAR_PATTERN = re.compile(r"\{\{(\s*\w+\s*)\}\}")


def render_template(template_str, context, module_key):
    """
    Interpolate {{var}} placeholders with whitelisted variables per module.

    Non-allowed or missing variables are left as-is in the output.

    Args:
        template_str: Template string with {{variable}} placeholders
        context: Dict of variable values
        module_key: Module key for whitelist lookup

    Returns:
        Rendered string with interpolated variables
    """
    if not template_str:
        return ""

    allowed = set(
        ALLOWED_VARIABLES.get(module_key, []) + ALLOWED_VARIABLES["system"]
    )

    def replacer(match):
        key = match.group(1).strip()
        if key in allowed and key in context:
            return str(context[key])
        return match.group(0)

    return _VAR_PATTERN.sub(replacer, template_str)


def build_context_for_parcela(parcela):
    """
    Build template variable context from a Parcela instance.

    Args:
        parcela: financeiro.Parcela instance

    Returns:
        Dict of template variables
    """
    lancamento = parcela.lancamento
    account = getattr(lancamento, "account", None)
    contact = getattr(lancamento, "contact", None)
    invoice = getattr(lancamento, "invoice", None)

    contact_name = ""
    if contact:
        first = getattr(contact, "first_name", "") or ""
        last = getattr(contact, "last_name", "") or ""
        contact_name = f"{first} {last}".strip()

    context = {
        "account_name": getattr(account, "name", "") if account else "",
        "contact_name": contact_name,
        "invoice_number": getattr(invoice, "invoice_number", "") if invoice else "",
        "amount": str(parcela.valor_parcela),
        "currency": parcela.currency or lancamento.currency,
        "due_date": str(parcela.data_vencimento),
        "days_overdue": str(parcela.dias_atraso),
        "parcela_number": str(parcela.numero),
        "lancamento_descricao": lancamento.descricao,
        "org_name": lancamento.org.name,
        "current_date": str(date.today()),
    }

    # days_until_due: positive = days remaining, negative = overdue
    if hasattr(parcela, "data_vencimento") and parcela.data_vencimento:
        delta = (parcela.data_vencimento - date.today()).days
        context["days_until_due"] = str(delta)

    # payment_link: placeholder until PIX/boleto link generation is implemented
    context["payment_link"] = ""

    return context


def build_context_for_lead(lead):
    """Build template variable context from a Lead instance."""
    assigned = lead.assigned_to.first() if hasattr(lead.assigned_to, "first") else None
    return {
        "lead_name": str(lead),
        "lead_status": getattr(lead, "status", ""),
        "lead_source": getattr(lead, "source", ""),
        "assigned_to": str(assigned) if assigned else "",
        "lead_email": getattr(lead, "email", ""),
        "lead_phone": getattr(lead, "phone", ""),
        "org_name": lead.org.name,
        "current_date": str(date.today()),
    }


def build_context_for_task(task):
    """Build template variable context from a Task instance."""
    assigned = task.assigned_to.first() if hasattr(task.assigned_to, "first") else None
    return {
        "task_title": task.title,
        "task_status": getattr(task, "status", ""),
        "task_priority": getattr(task, "priority", ""),
        "assigned_to": str(assigned) if assigned else "",
        "due_date": str(task.due_date) if task.due_date else "",
        "org_name": task.org.name,
        "current_date": str(date.today()),
    }


def build_context_for_opportunity(opportunity):
    """Build template variable context from an Opportunity instance."""
    assigned = (
        opportunity.assigned_to.first()
        if hasattr(opportunity.assigned_to, "first")
        else None
    )
    return {
        "opportunity_name": str(opportunity),
        "opportunity_stage": getattr(opportunity, "stage", "") or "",
        "amount": str(opportunity.amount) if getattr(opportunity, "amount", None) else "",
        "currency": getattr(opportunity, "currency", ""),
        "assigned_to": str(assigned) if assigned else "",
        "close_date": str(opportunity.closed_on) if getattr(opportunity, "closed_on", None) else "",
        "org_name": opportunity.org.name,
        "current_date": str(date.today()),
    }


def build_context_for_case(case):
    """Build template variable context from a Case instance."""
    from datetime import timedelta

    assigned = case.assigned_to.first() if hasattr(case.assigned_to, "first") else None

    # Calculate SLA deadline from created_at + sla_resolution_hours
    sla_deadline = ""
    if hasattr(case, "sla_resolution_hours") and case.created_at:
        deadline = case.created_at + timedelta(hours=case.sla_resolution_hours)
        sla_deadline = str(deadline)

    return {
        "case_name": case.name,
        "case_status": getattr(case, "status", ""),
        "case_priority": getattr(case, "priority", ""),
        "assigned_to": str(assigned) if assigned else "",
        "sla_deadline": sla_deadline,
        "org_name": case.org.name,
        "current_date": str(date.today()),
    }


def build_context_for_invoice(invoice):
    """Build template variable context from an Invoice instance."""
    contact = getattr(invoice, "contact", None)
    account = getattr(invoice, "account", None)

    contact_name = ""
    if contact:
        first = getattr(contact, "first_name", "") or ""
        last = getattr(contact, "last_name", "") or ""
        contact_name = f"{first} {last}".strip()

    return {
        "invoice_number": getattr(invoice, "invoice_number", ""),
        "invoice_status": getattr(invoice, "status", ""),
        "amount": str(invoice.total_amount) if hasattr(invoice, "total_amount") else "",
        "currency": getattr(invoice, "currency", ""),
        "due_date": str(invoice.due_date) if getattr(invoice, "due_date", None) else "",
        "contact_name": contact_name,
        "account_name": getattr(account, "name", "") if account else "",
        "org_name": invoice.org.name,
        "current_date": str(date.today()),
    }
