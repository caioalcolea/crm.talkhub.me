"""
TalkHub Omni Sync Engine v2.

Motor de sincronização bidirecional entre TalkHub Omni e CRM.
Usa DataUnifier para normalização e enriquecimento de dados.

Módulos:
- Contacts (subscribers ↔ contacts)
- Tickets (ticket lists ↔ cases/leads)
- Tags (flow tags ↔ CRM tags)
- Team Members (team members → TalkHubTeamMember)
- Statistics (métricas → OmniStatisticsSnapshot)
"""

import logging

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from common.models import Org, Tags
from contacts.models import Contact
from integrations.data_unifier import DataUnifier

from .client import TalkHubAPIError, TalkHubClient
from .models import (
    OmniStatisticsSnapshot,
    TalkHubConnection,
    TalkHubSyncJob,
    TalkHubTeamMember,
    TalkHubTicketListMapping,
)

logger = logging.getLogger(__name__)

SYNC_LOCK_TTL = 5  # seconds


def _get_client(org) -> TalkHubClient:
    """Obter TalkHubClient configurado para a org."""
    conn = TalkHubConnection.objects.filter(org=org, is_connected=True).first()
    if not conn:
        raise TalkHubAPIError("TalkHub not connected for this organization")
    return TalkHubClient(api_key=conn.api_key, base_url=conn.workspace_url)


def _update_job(job, **kwargs):
    """Atualizar sync job com novos valores."""
    for k, v in kwargs.items():
        setattr(job, k, v)
    job.save(update_fields=list(kwargs.keys()) + ["updated_at"])


def run_sync(org, sync_type: str, job_id: str) -> dict:
    """Entry point para sync via connector. Delega para função específica."""
    job = TalkHubSyncJob.objects.get(id=job_id)

    dispatch = {
        "contacts": sync_contacts,
        "tickets": sync_tickets,
        "tags": lambda o, j: sync_tags(o),
        "team_members": lambda o, j: sync_team_members(o),
        "statistics": lambda o, j: sync_statistics(o),
        "all": _sync_all,
    }

    func = dispatch.get(sync_type)
    if not func:
        _update_job(job, status="FAILED", error_log=[{"error": f"Unknown sync type: {sync_type}"}])
        return {"error": f"Unknown sync type: {sync_type}"}

    try:
        func(org, job)
    except Exception as exc:
        logger.exception("Sync %s failed for org %s", sync_type, org.id)
        _update_job(
            job, status="FAILED",
            error_log=[{"error": str(exc)}],
            completed_at=timezone.now(),
        )

    return {
        "status": job.status,
        "imported": job.imported_count,
        "updated": job.updated_count,
        "errors": job.error_count,
    }


def _sync_all(org, job):
    """Executar todos os tipos de sync."""
    _update_job(job, status="IN_PROGRESS", started_at=timezone.now())
    errors = []

    for sync_fn, label in [
        (sync_contacts, "contacts"),
        (sync_tickets, "tickets"),
        (lambda o, j: sync_tags(o), "tags"),
        (lambda o, j: sync_team_members(o), "team_members"),
        (lambda o, j: sync_statistics(o), "statistics"),
    ]:
        try:
            sub_job = TalkHubSyncJob.objects.create(org=org, sync_type=label)
            sync_fn(org, sub_job)
        except Exception as exc:
            errors.append({"module": label, "error": str(exc)})

    _update_job(
        job, status="COMPLETED",
        error_count=len(errors), error_log=errors,
        completed_at=timezone.now(),
    )


# ═══════════════════════════════════════════════════════════════════════
# CONTACTS SYNC (6.10)
# ═══════════════════════════════════════════════════════════════════════


def sync_contacts(org, job):
    """Full sync: TalkHub subscribers → CRM Contacts via DataUnifier."""
    client = _get_client(org)
    unifier = DataUnifier(org, connector_slug="talkhub-omni")
    _update_job(job, status="IN_PROGRESS", started_at=timezone.now())

    imported = updated = skipped = 0
    errors = []
    page = 1

    try:
        while True:
            data = client.get_subscribers(page=page, limit=100)
            subscribers = data.get("subscribers") or data.get("data") or []
            if not subscribers:
                break

            _update_job(job, total_records=data.get("total", 0))

            for sub in subscribers:
                try:
                    user_ns = sub.get("user_ns") or sub.get("id")
                    if not user_ns:
                        skipped += 1
                        continue

                    # Mapear campos do subscriber
                    contact_data = _map_subscriber_to_contact(sub)

                    contact, created = unifier.upsert_contact(
                        contact_data,
                        source="talkhub_omni",
                        talkhub_subscriber_id=str(user_ns),
                    )

                    if contact is None:
                        skipped += 1
                    elif created:
                        imported += 1
                    else:
                        updated += 1

                except Exception as exc:
                    errors.append({"subscriber": sub.get("user_ns", "?"), "error": str(exc)})
                    logger.warning("Contact sync error: %s", exc)

            _update_job(
                job,
                imported_count=imported, updated_count=updated,
                skipped_count=skipped, error_count=len(errors),
            )

            if not data.get("next_page") and not data.get("has_more", False):
                break
            page += 1

    except TalkHubAPIError as exc:
        errors.append({"error": f"API error: {exc}"})

    _update_job(
        job, status="COMPLETED",
        imported_count=imported, updated_count=updated,
        skipped_count=skipped, error_count=len(errors),
        error_log=errors[:100], completed_at=timezone.now(),
    )
    return job


def _map_subscriber_to_contact(sub: dict) -> dict:
    """
    Mapear campos de subscriber TalkHub para formato DataUnifier.

    Usa o variable_registry para resolver aliases automaticamente,
    garantindo consistência com todos os caminhos de integração.
    """
    from integrations.variable_registry import resolve_to_crm_field

    contact_data = {}

    # Iterar sobre todos os campos do subscriber e resolver via registry
    for key, value in sub.items():
        if value is None or value == "":
            continue
        crm_field = resolve_to_crm_field("contact", key)
        if crm_field:
            contact_data[crm_field] = value

    # Fallback: se não resolveu first_name, tentar "name" como full_name
    if "first_name" not in contact_data and sub.get("name"):
        contact_data["full_name"] = sub["name"]

    return contact_data


def push_contact_to_talkhub(org, contact):
    """Propagar Contact CRM → TalkHub subscriber."""
    client = _get_client(org)

    # Set sync lock para anti-loop
    if contact.talkhub_subscriber_id:
        cache_key = f"sync_lock:contact:{contact.talkhub_subscriber_id}:{org.id}"
        cache.set(cache_key, True, timeout=SYNC_LOCK_TTL)

    data = {
        "first_name": contact.first_name,
        "last_name": contact.last_name or "",
    }
    if contact.email:
        data["email"] = contact.email
    if contact.phone:
        data["phone"] = contact.phone

    if contact.talkhub_subscriber_id:
        client.update_subscriber(contact.talkhub_subscriber_id, data)
        # Atualizar custom fields via set-user-fields
        custom_fields = {}
        if contact.organization:
            custom_fields["company"] = contact.organization
        if custom_fields:
            client.set_user_fields(contact.talkhub_subscriber_id, custom_fields)
        return "updated"
    else:
        result = client.create_subscriber(data)
        new_ns = result.get("user_ns") or result.get("id")
        if new_ns:
            contact.talkhub_subscriber_id = str(new_ns)
            contact.save(update_fields=["talkhub_subscriber_id", "updated_at"])
        return "created"


def enrich_contact(org, contact):
    """Enriquecer Contact com dados completos do subscriber."""
    if not contact.talkhub_subscriber_id:
        return

    client = _get_client(org)
    try:
        info = client.get_subscriber_info(contact.talkhub_subscriber_id)
    except TalkHubAPIError:
        return

    unifier = DataUnifier(org, connector_slug="talkhub-omni")
    contact_data = _map_subscriber_to_contact(info)
    unifier.upsert_contact(
        contact_data,
        source="talkhub_omni",
        talkhub_subscriber_id=contact.talkhub_subscriber_id,
    )


# ═══════════════════════════════════════════════════════════════════════
# TICKETS SYNC (6.11)
# ═══════════════════════════════════════════════════════════════════════


def sync_ticket_list_structure(org):
    """Sync estrutura de ticket lists → TalkHubTicketListMapping."""
    client = _get_client(org)

    try:
        data = client.get_ticket_lists()
        lists = data.get("lists") or data.get("data") or []
        if isinstance(data, list):
            lists = data
    except TalkHubAPIError as exc:
        logger.error("Ticket list structure sync failed: %s", exc)
        return

    for tl in lists:
        list_id = str(tl.get("id") or tl.get("ns", ""))
        list_name = tl.get("name") or tl.get("title", "Untitled")
        if not list_id:
            continue

        mapping, created = TalkHubTicketListMapping.objects.get_or_create(
            org=org, omni_list_id=list_id,
            defaults={"omni_list_name": list_name, "pipeline_type": "lead"},
        )
        if not created and mapping.omni_list_name != list_name:
            mapping.omni_list_name = list_name
            mapping.save(update_fields=["omni_list_name", "updated_at"])

    logger.info("Ticket list structure synced for org %s: %d lists", org.id, len(lists))


def sync_tickets(org, job):
    """Sync ticket items → Cases/Leads conforme TalkHubTicketListMapping."""
    client = _get_client(org)
    _update_job(job, status="IN_PROGRESS", started_at=timezone.now())

    imported = updated = skipped = 0
    errors = []

    mappings = TalkHubTicketListMapping.objects.filter(org=org)
    if not mappings.exists():
        sync_ticket_list_structure(org)
        mappings = TalkHubTicketListMapping.objects.filter(org=org)

    for mapping in mappings:
        try:
            data = client.get_ticket_list_items(mapping.omni_list_id)
            items = data.get("items") or data.get("data") or []
            if isinstance(data, list):
                items = data

            for item in items:
                try:
                    result = _upsert_ticket_item(org, mapping, item, client)
                    if result == "created":
                        imported += 1
                    elif result == "updated":
                        updated += 1
                    else:
                        skipped += 1
                except Exception as exc:
                    errors.append({
                        "list": mapping.omni_list_name,
                        "item": item.get("id", "?"),
                        "error": str(exc),
                    })

        except TalkHubAPIError as exc:
            errors.append({"list": mapping.omni_list_name, "error": str(exc)})

    _update_job(
        job, status="COMPLETED",
        imported_count=imported, updated_count=updated,
        skipped_count=skipped, error_count=len(errors),
        error_log=errors[:100], completed_at=timezone.now(),
    )
    return job


@transaction.atomic
def _upsert_ticket_item(org, mapping, item: dict, client) -> str:
    """Criar ou atualizar Case/Lead a partir de ticket item."""
    from cases.models import Case
    from leads.models import Lead

    item_id = str(item.get("id") or item.get("ns", ""))
    if not item_id:
        return "skipped"

    title = item.get("title") or "Ticket"

    # Buscar contact vinculado
    contact = None
    user_ns = item.get("user_ns") or item.get("subscriber_ns")
    if user_ns:
        contact = Contact.objects.filter(
            org=org, talkhub_subscriber_id=str(user_ns)
        ).first()
        if not contact:
            # Criar contact on-the-fly
            unifier = DataUnifier(org, connector_slug="talkhub-omni")
            contact, _ = unifier.upsert_contact(
                {"first_name": item.get("subscriber_name", "Unknown")},
                source="talkhub_omni",
                talkhub_subscriber_id=str(user_ns),
            )

    if mapping.pipeline_type == "case" and mapping.case_pipeline:
        return _upsert_case_from_ticket(org, mapping, item, item_id, title, contact)
    elif mapping.pipeline_type == "lead" and mapping.lead_pipeline:
        return _upsert_lead_from_ticket(org, mapping, item, item_id, title, contact)

    return "skipped"


def _upsert_case_from_ticket(org, mapping, item, item_id, title, contact) -> str:
    """Upsert Case a partir de ticket item."""
    from cases.models import Case

    case = Case.objects.filter(org=org, omni_ticket_item_id=item_id).first()

    if case:
        changed = False
        if title and case.name != title:
            case.name = title
            changed = True
        if changed:
            case.save()
        return "updated"

    first_stage = mapping.case_pipeline.stages.order_by("order").first()
    case = Case.objects.create(
        org=org,
        name=title,
        description=item.get("description", ""),
        omni_ticket_item_id=item_id,
        omni_ticket_list_id=mapping.omni_list_id,
        stage=first_stage,
        status="New",
    )
    if contact:
        case.contacts.add(contact)
    return "created"


def _upsert_lead_from_ticket(org, mapping, item, item_id, title, contact) -> str:
    """Upsert Lead a partir de ticket item."""
    from leads.models import Lead

    lead = Lead.objects.filter(org=org, omni_ticket_item_id=item_id).first()

    if lead:
        changed = False
        if title and lead.title != title:
            lead.title = title
            changed = True
        if changed:
            lead.save()
        return "updated"

    first_stage = mapping.lead_pipeline.stages.order_by("order").first()
    lead = Lead.objects.create(
        org=org,
        title=title,
        description=item.get("description", ""),
        omni_ticket_item_id=item_id,
        omni_ticket_list_id=mapping.omni_list_id,
        stage=first_stage,
        status="assigned",
    )
    if contact:
        lead.contacts.add(contact)
    return "created"


def push_case_to_omni(org, case):
    """Propagar mudança de Case → ticket no TalkHub Omni."""
    if not case.omni_ticket_item_id or not case.omni_ticket_list_id:
        return

    client = _get_client(org)
    cache_key = f"sync_lock:ticket:{case.omni_ticket_item_id}:{org.id}"
    cache.set(cache_key, True, timeout=SYNC_LOCK_TTL)

    data = {"title": case.name}
    if case.status:
        data["status"] = case.status

    try:
        client.update_ticket_item(
            case.omni_ticket_list_id, case.omni_ticket_item_id, data
        )
    except TalkHubAPIError as exc:
        logger.warning("Push case to Omni failed: %s", exc)


def push_lead_to_omni(org, lead):
    """Propagar mudança de Lead → ticket no TalkHub Omni."""
    if not lead.omni_ticket_item_id or not lead.omni_ticket_list_id:
        return

    client = _get_client(org)
    cache_key = f"sync_lock:ticket:{lead.omni_ticket_item_id}:{org.id}"
    cache.set(cache_key, True, timeout=SYNC_LOCK_TTL)

    data = {"title": lead.title}
    if lead.status:
        data["status"] = lead.status

    try:
        client.update_ticket_item(
            lead.omni_ticket_list_id, lead.omni_ticket_item_id, data
        )
    except TalkHubAPIError as exc:
        logger.warning("Push lead to Omni failed: %s", exc)


def sync_ticket_logs(org):
    """Sync ticket list activity logs para métricas."""
    client = _get_client(org)
    mappings = TalkHubTicketListMapping.objects.filter(org=org)

    for mapping in mappings:
        try:
            client.get_ticket_list_log(mapping.omni_list_id)
            # Logs são armazenados no OmniStatisticsSnapshot via sync_statistics
        except TalkHubAPIError as exc:
            logger.warning("Ticket log sync failed for list %s: %s", mapping.omni_list_id, exc)


# ═══════════════════════════════════════════════════════════════════════
# TAGS SYNC (6.13)
# ═══════════════════════════════════════════════════════════════════════


def sync_tags(org):
    """Sync TalkHub flow tags → CRM Tags."""
    client = _get_client(org)

    try:
        data = client.get_tags()
        tags_list = data.get("tags") or data.get("data") or []
        if isinstance(data, list):
            tags_list = data
    except TalkHubAPIError as exc:
        logger.error("Tag sync failed: %s", exc)
        return

    imported = updated = 0

    for tag_data in tags_list:
        tag_name = tag_data.get("name") or tag_data.get("tag", "")
        tag_ns = str(tag_data.get("ns") or tag_data.get("id", ""))
        if not tag_name:
            continue

        slug = slugify(tag_name)
        existing = Tags.objects.filter(org=org, slug=slug).first()
        if not existing and tag_ns:
            existing = Tags.objects.filter(org=org, talkhub_tag_ns=tag_ns).first()

        if existing:
            if tag_ns and existing.talkhub_tag_ns != tag_ns:
                existing.talkhub_tag_ns = tag_ns
                existing.save(update_fields=["talkhub_tag_ns", "updated_at"])
                updated += 1
        else:
            Tags.objects.create(
                org=org, name=tag_name, slug=slug,
                talkhub_tag_ns=tag_ns, color="blue",
            )
            imported += 1

    logger.info("Tags synced for org %s: imported=%d, updated=%d", org.id, imported, updated)


# ═══════════════════════════════════════════════════════════════════════
# TEAM MEMBERS SYNC (6.15)
# ═══════════════════════════════════════════════════════════════════════


def sync_team_members(org):
    """Sync TalkHub team members → TalkHubTeamMember (aditiva, sem exclusão)."""
    client = _get_client(org)

    try:
        data = client.get_team_members()
        members = data.get("members") or data.get("data") or []
        if isinstance(data, list):
            members = data
    except TalkHubAPIError as exc:
        logger.error("Team member sync failed: %s", exc)
        return

    imported = updated = 0

    for member in members:
        agent_id = str(member.get("id") or member.get("agent_id") or member.get("ns", ""))
        if not agent_id:
            continue

        name = member.get("name") or ""
        email = (member.get("email") or "").strip().lower()
        image = member.get("image") or member.get("avatar", "")
        th_role = (member.get("role") or member.get("type") or "agent").lower()

        # Mapear roles: owner/admin → admin, agent/member → agent
        role = "admin" if th_role in ("owner", "admin", "administrator") else "agent"
        is_online = member.get("is_online", False)

        existing = TalkHubTeamMember.objects.filter(
            org=org, omni_agent_id=agent_id
        ).first()

        if existing:
            changed = False
            for field, value in [
                ("name", name), ("email", email), ("image", image),
                ("role", role), ("is_online", is_online),
            ]:
                if value and getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                existing.save()
                updated += 1
        else:
            TalkHubTeamMember.objects.create(
                org=org, omni_agent_id=agent_id,
                name=name, email=email, image=image,
                role=role, is_online=is_online,
            )
            imported += 1

    logger.info(
        "Team members synced for org %s: imported=%d, updated=%d",
        org.id, imported, updated,
    )


# ═══════════════════════════════════════════════════════════════════════
# STATISTICS SYNC (6.17)
# ═══════════════════════════════════════════════════════════════════════


def sync_statistics(org):
    """Consolidar métricas do TalkHub Omni → OmniStatisticsSnapshot."""
    client = _get_client(org)
    raw_data = {}

    # Coletar dados de múltiplas APIs
    try:
        raw_data["flow_summary"] = client.get_flow_summary()
    except TalkHubAPIError:
        raw_data["flow_summary"] = {}

    try:
        raw_data["bot_users"] = client.get_bot_users_count()
    except TalkHubAPIError:
        raw_data["bot_users"] = {}

    try:
        raw_data["agent_summary"] = client.get_flow_agent_summary()
    except TalkHubAPIError:
        raw_data["agent_summary"] = {}

    try:
        raw_data["conversations"] = client.get_conversations_data()
    except TalkHubAPIError:
        raw_data["conversations"] = {}

    try:
        raw_data["team_info"] = client.get_team_info()
    except TalkHubAPIError:
        raw_data["team_info"] = {}

    # Extrair métricas consolidadas
    bot_users = raw_data.get("bot_users", {})
    flow_summary = raw_data.get("flow_summary", {})
    agent_summary = raw_data.get("agent_summary", {})

    bot_users_count = (
        bot_users.get("count") or bot_users.get("total") or 0
    )
    messages_count = (
        flow_summary.get("messages_count")
        or flow_summary.get("total_messages") or 0
    )
    avg_response = (
        flow_summary.get("avg_response_time")
        or flow_summary.get("avg_response_time_seconds") or 0.0
    )
    resolution_rate = (
        flow_summary.get("resolution_rate") or 0.0
    )

    # Produtividade por agente
    agent_productivity = {}
    agents_data = agent_summary.get("agents") or agent_summary.get("data") or []
    if isinstance(agents_data, list):
        for agent in agents_data:
            aid = str(agent.get("id") or agent.get("agent_id", ""))
            if aid:
                agent_productivity[aid] = {
                    "name": agent.get("name", ""),
                    "messages": agent.get("messages_count", 0),
                    "avg_time": agent.get("avg_response_time", 0),
                }

    agents_online = TalkHubTeamMember.objects.filter(
        org=org, is_online=True
    ).count()

    OmniStatisticsSnapshot.objects.create(
        org=org,
        period="hourly",
        bot_users_count=int(bot_users_count),
        messages_count=int(messages_count),
        avg_response_time_seconds=float(avg_response),
        resolution_rate=float(resolution_rate),
        agents_online=agents_online,
        agent_productivity=agent_productivity,
        raw_data=raw_data,
    )

    logger.info("Statistics snapshot created for org %s", org.id)
