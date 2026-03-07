"""
TalkHub Omni Webhook Handlers.

Processa eventos recebidos via webhook do TalkHub Omni:
- subscriber.created / subscriber.updated → upsert Contact
- ticket.created / ticket.updated → criar/atualizar Case ou Lead
- message.received → criar Conversation + Message
- tag.applied / tag.removed → aplicar/remover tag do Contact

Anti-loop: verifica sync_lock no Redis antes de processar.
"""

import logging

from django.core.cache import cache
from django.utils import timezone

from channels.base import ChannelType
from integrations.data_unifier import DataUnifier

logger = logging.getLogger(__name__)

SYNC_LOCK_TTL = 5  # seconds


def route_webhook(org, payload: dict) -> dict | None:
    """Rotear webhook por tipo de evento."""
    event_type = payload.get("event")
    data = payload.get("data", {})

    handlers = {
        "subscriber.created": handle_subscriber_created,
        "subscriber.updated": handle_subscriber_updated,
        "ticket.created": handle_ticket_created,
        "ticket.updated": handle_ticket_updated,
        "message.received": handle_message_received,
        "tag.applied": handle_tag_applied,
        "tag.removed": handle_tag_removed,
    }

    handler = handlers.get(event_type)
    if handler:
        result = handler(org, data)
        # Disparar SocialAutomations se houver
        _trigger_social_automations(org, event_type, data)
        return result

    logger.warning("Unhandled TalkHub webhook event: %s", event_type)
    return None


# Mapeamento de eventos webhook → social_event para automações
_WEBHOOK_TO_SOCIAL_EVENT = {
    "message.received": "message_received",
    "subscriber.created": "contact_started",
}


def _trigger_social_automations(org, event_type, data):
    """Disparar SocialAutomations ativas para o evento webhook."""
    social_event = _WEBHOOK_TO_SOCIAL_EVENT.get(event_type)
    if not social_event:
        return

    try:
        from automations.engine import process_social_event

        # Determinar channel_type a partir dos dados do webhook
        channel_type = data.get("channel", "whatsapp")
        process_social_event(social_event, channel_type, str(org.id), data)
    except Exception:
        logger.exception("Error triggering social automations for %s", event_type)


def _is_sync_locked(org_id, entity_key: str) -> bool:
    """Verificar se entidade está em sync_lock (anti-loop)."""
    cache_key = f"sync_lock:{entity_key}:{org_id}"
    return bool(cache.get(cache_key))


def _set_sync_lock(org_id, entity_key: str):
    """Setar sync_lock para anti-loop."""
    cache_key = f"sync_lock:{entity_key}:{org_id}"
    cache.set(cache_key, True, timeout=SYNC_LOCK_TTL)


def _upsert_contact_from_subscriber(org, data: dict):
    """
    Helper: criar/atualizar Contact a partir de dados de subscriber.

    Usa variable_registry para resolver aliases e DataUnifier para
    normalização e enriquecimento — garantindo consistência com todos
    os caminhos de integração (sync, webhook, CSV, etc.).
    """
    from integrations.variable_registry import resolve_to_crm_field

    user_ns = data.get("user_ns") or data.get("id")
    if not user_ns:
        return None

    unifier = DataUnifier(org, connector_slug="talkhub-omni")

    # Resolver campos via variable_registry (aliases automáticos)
    contact_data = {}
    for key, value in data.items():
        if value is None or value == "":
            continue
        crm_field = resolve_to_crm_field("contact", key)
        if crm_field:
            contact_data[crm_field] = value

    # Fallback: se não resolveu first_name, tentar "name" como full_name
    if "first_name" not in contact_data and data.get("name"):
        contact_data["full_name"] = data["name"]

    contact, created = unifier.upsert_contact(
        contact_data,
        source="talkhub_omni",
        talkhub_subscriber_id=str(user_ns),
    )

    if contact:
        # Garantir que omni_user_ns está preenchido
        update_fields = []
        if not contact.omni_user_ns:
            contact.omni_user_ns = str(user_ns)
            update_fields.append("omni_user_ns")

        # Atualizar opt-in flags se presentes
        if "sms_opt_in" in data and contact.sms_opt_in != data["sms_opt_in"]:
            contact.sms_opt_in = data["sms_opt_in"]
            update_fields.append("sms_opt_in")
        if "email_opt_in" in data and contact.email_opt_in != data["email_opt_in"]:
            contact.email_opt_in = data["email_opt_in"]
            update_fields.append("email_opt_in")

        if update_fields:
            contact.save(update_fields=update_fields + ["updated_at"])

    return contact


# ─── Event Handlers ──────────────────────────────────────────────────


def handle_subscriber_created(org, data: dict) -> dict:
    """Criar Contact a partir de subscriber webhook."""
    user_ns = data.get("user_ns") or data.get("id")
    if not user_ns:
        return {"skipped": True, "reason": "no_user_ns"}

    if _is_sync_locked(str(org.id), f"contact:{user_ns}"):
        return {"skipped": True, "reason": "sync_lock"}

    contact = _upsert_contact_from_subscriber(org, data)
    if not contact:
        return {"skipped": True, "reason": "upsert_failed"}

    _log_integration("create", "in", "contact", str(contact.id), org)
    return {"contact_id": str(contact.id), "created": True}


def handle_subscriber_updated(org, data: dict) -> dict:
    """Atualizar Contact a partir de subscriber webhook."""
    user_ns = data.get("user_ns") or data.get("id")
    if not user_ns:
        return {"skipped": True, "reason": "no_user_ns"}

    if _is_sync_locked(str(org.id), f"contact:{user_ns}"):
        return {"skipped": True, "reason": "sync_lock"}

    contact = _upsert_contact_from_subscriber(org, data)
    if not contact:
        return {"skipped": True, "reason": "upsert_failed"}

    _log_integration("update", "in", "contact", str(contact.id), org)
    return {"contact_id": str(contact.id), "updated": True}


def handle_ticket_created(org, data: dict) -> dict:
    """Criar Case ou Lead conforme TalkHubTicketListMapping."""
    from cases.models import Case
    from leads.models import Lead

    from .models import TalkHubTicketListMapping

    list_id = str(data.get("list_id") or data.get("ticket_list_id", ""))
    item_id = str(data.get("id") or data.get("item_id", ""))
    if not list_id or not item_id:
        return {"skipped": True, "reason": "missing_ids"}

    mapping = TalkHubTicketListMapping.objects.filter(
        org=org, omni_list_id=list_id
    ).first()
    if not mapping:
        return {"skipped": True, "reason": "no_mapping"}

    # Upsert contact se subscriber info presente
    contact = None
    subscriber_data = data.get("subscriber") or {}
    user_ns = subscriber_data.get("user_ns") or data.get("user_ns")
    if user_ns:
        contact = _upsert_contact_from_subscriber(org, subscriber_data or {"user_ns": user_ns})

    title = data.get("title") or "Ticket from TalkHub"

    if mapping.pipeline_type == "case" and mapping.case_pipeline:
        first_stage = mapping.case_pipeline.stages.order_by("order").first()
        case = Case.objects.create(
            org=org,
            name=title,
            description=data.get("description", ""),
            omni_ticket_item_id=item_id,
            omni_ticket_list_id=list_id,
            stage=first_stage,
            status="New",
        )
        if contact:
            case.contacts.add(contact)
        _log_integration("create", "in", "case", str(case.id), org)
        return {"case_id": str(case.id)}

    elif mapping.pipeline_type == "lead" and mapping.lead_pipeline:
        first_stage = mapping.lead_pipeline.stages.order_by("order").first()
        lead = Lead.objects.create(
            org=org,
            title=title,
            description=data.get("description", ""),
            omni_ticket_item_id=item_id,
            omni_ticket_list_id=list_id,
            stage=first_stage,
            status="assigned",
        )
        if contact:
            lead.contacts.add(contact)
        _log_integration("create", "in", "lead", str(lead.id), org)
        return {"lead_id": str(lead.id)}

    return {"skipped": True, "reason": "invalid_mapping"}


def handle_ticket_updated(org, data: dict) -> dict:
    """Atualizar status de Case/Lead a partir de ticket update."""
    from cases.models import Case
    from leads.models import Lead

    item_id = str(data.get("id") or data.get("item_id", ""))
    if not item_id:
        return {"skipped": True, "reason": "no_item_id"}

    if _is_sync_locked(str(org.id), f"ticket:{item_id}"):
        return {"skipped": True, "reason": "sync_lock"}

    # Tentar encontrar Case
    case = Case.objects.filter(org=org, omni_ticket_item_id=item_id).first()
    if case:
        if data.get("title"):
            case.name = data["title"]
        if data.get("status"):
            case.status = data["status"]
        case.save()
        _log_integration("update", "in", "case", str(case.id), org)
        return {"case_id": str(case.id), "updated": True}

    # Tentar encontrar Lead
    lead = Lead.objects.filter(org=org, omni_ticket_item_id=item_id).first()
    if lead:
        if data.get("title"):
            lead.title = data["title"]
        lead.save()
        _log_integration("update", "in", "lead", str(lead.id), org)
        return {"lead_id": str(lead.id), "updated": True}

    return {"skipped": True, "reason": "entity_not_found"}


def handle_message_received(org, data: dict) -> dict:
    """Criar/atualizar Conversation e Message a partir de mensagem recebida."""
    from contacts.models import Contact
    from conversations.models import Conversation, Message

    user_ns = data.get("user_ns")
    if not user_ns:
        return {"skipped": True, "reason": "no_user_ns"}

    # Buscar ou criar contact
    contact = Contact.objects.filter(
        org=org, talkhub_subscriber_id=str(user_ns)
    ).first()
    if not contact:
        subscriber_data = data.get("subscriber") or {"user_ns": user_ns}
        contact = _upsert_contact_from_subscriber(org, subscriber_data)
        if not contact:
            return {"skipped": True, "reason": "contact_upsert_failed"}

    # Buscar ou criar conversation
    conversation, conv_created = Conversation.objects.get_or_create(
        org=org,
        contact=contact,
        channel=ChannelType.TALKHUB_OMNI.value,
        defaults={
            "status": "open",
        },
    )
    conversation.last_message_at = timezone.now()
    conversation.save(update_fields=["last_message_at", "updated_at"])

    # Criar message
    message = Message.objects.create(
        org=org,
        conversation=conversation,
        direction="in",
        msg_type=data.get("type", "text"),
        content=data.get("text", ""),
        media_url=data.get("media_url", ""),
        sender_type="contact",
        sender_name=contact.first_name or "",
        sender_id=str(user_ns),
        timestamp=data.get("timestamp") or timezone.now(),
    )

    return {
        "conversation_id": str(conversation.id),
        "message_id": str(message.id),
        "new_conversation": conv_created,
    }


def handle_tag_applied(org, data: dict) -> dict:
    """Aplicar tag ao Contact."""
    from common.models import Tags
    from contacts.models import Contact

    user_ns = data.get("user_ns")
    tag_name = data.get("tag") or data.get("tag_name")
    if not user_ns or not tag_name:
        return {"skipped": True, "reason": "missing_data"}

    contact = Contact.objects.filter(
        org=org, talkhub_subscriber_id=str(user_ns)
    ).first()
    if not contact:
        return {"skipped": True, "reason": "contact_not_found"}

    tag, _ = Tags.objects.get_or_create(
        org=org, name=tag_name,
        defaults={"slug": tag_name.lower().replace(" ", "-"), "color": "blue"},
    )

    if not contact.tags.filter(id=tag.id).exists():
        contact.tags.add(tag)

    return {"contact_id": str(contact.id), "tag": tag_name, "applied": True}


def handle_tag_removed(org, data: dict) -> dict:
    """Remover tag do Contact."""
    from common.models import Tags
    from contacts.models import Contact

    user_ns = data.get("user_ns")
    tag_name = data.get("tag") or data.get("tag_name")
    if not user_ns or not tag_name:
        return {"skipped": True, "reason": "missing_data"}

    contact = Contact.objects.filter(
        org=org, talkhub_subscriber_id=str(user_ns)
    ).first()
    if not contact:
        return {"skipped": True, "reason": "contact_not_found"}

    tag = Tags.objects.filter(org=org, name=tag_name).first()
    if tag:
        contact.tags.remove(tag)

    return {"contact_id": str(contact.id), "tag": tag_name, "removed": True}


# ─── Helpers ──────────────────────────────────────────────────────────


def _log_integration(operation, direction, entity_type, entity_id, org):
    """Registrar log de integração."""
    try:
        from integrations.models import IntegrationLog

        IntegrationLog.objects.create(
            org=org,
            connector_slug="talkhub-omni",
            operation=operation,
            direction=direction,
            entity_type=entity_type,
            entity_id=entity_id,
            status="success",
        )
    except Exception as exc:
        logger.warning("Failed to log integration: %s", exc)
