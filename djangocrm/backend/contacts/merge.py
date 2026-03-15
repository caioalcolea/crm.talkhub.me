"""
Contact Merge Service.

Merges two contacts into one, reassigning all related entities
(conversations, leads, invoices, etc.) from the secondary to the primary.
"""

import logging
import re

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from contacts.models import Contact

logger = logging.getLogger(__name__)

# Scalar fields that can be inherited from secondary when primary is empty
_SCALAR_FIELDS = [
    "email", "phone", "organization", "title", "department",
    "linkedin_url", "instagram", "facebook", "tiktok", "telegram",
    "address_line", "city", "state", "postcode", "country",
    "source", "talkhub_channel_type", "talkhub_channel_id",
    "talkhub_subscriber_id", "omni_user_ns", "account_id",
]

# Boolean fields merged with OR logic
_BOOL_OR_FIELDS = ["do_not_call", "sms_opt_in", "email_opt_in", "is_active"]


def merge_contacts(org, primary_id, secondary_id, user_email="system"):
    """
    Merge secondary contact into primary contact.

    - Primary keeps its data; empty fields are filled from secondary.
    - All FK/M2M references are moved from secondary to primary.
    - Secondary is deleted.

    Returns:
        tuple: (primary_contact, stats_dict)
    """
    with transaction.atomic():
        primary = (
            Contact.objects.select_for_update()
            .get(id=primary_id, org=org)
        )
        secondary = (
            Contact.objects.select_for_update()
            .get(id=secondary_id, org=org)
        )

        if primary.id == secondary.id:
            raise ValueError("Cannot merge a contact with itself")

        stats = {}

        # --- 1. Fill empty scalar fields ---
        for field in _SCALAR_FIELDS:
            primary_val = getattr(primary, field, None)
            secondary_val = getattr(secondary, field, None)
            if not primary_val and secondary_val:
                setattr(primary, field, secondary_val)

        # --- 1b. Preserve conflicting email/phone/address as extra entries ---
        from contacts.models import ContactAddress, ContactEmail, ContactPhone

        # If both have emails and they're different, save secondary's as extra
        if (
            primary.email
            and secondary.email
            and primary.email.lower() != secondary.email.lower()
        ):
            ContactEmail.objects.get_or_create(
                contact=primary,
                email=secondary.email,
                defaults={"label": "other"},
            )

        # If both have phones and they're different, save secondary's as extra
        if (
            primary.phone
            and secondary.phone
            and primary.phone != secondary.phone
        ):
            ContactPhone.objects.get_or_create(
                contact=primary,
                phone=secondary.phone,
                defaults={"label": "other"},
            )

        # If both have addresses and they're different, save secondary's as extra
        if (
            primary.address_line
            and secondary.address_line
            and primary.address_line != secondary.address_line
        ):
            ContactAddress.objects.get_or_create(
                contact=primary,
                address_line=secondary.address_line,
                defaults={
                    "label": "other",
                    "city": secondary.city or "",
                    "state": secondary.state or "",
                    "postcode": secondary.postcode or "",
                    "country": secondary.country or "",
                },
            )

        # Move secondary's extra_emails/phones/addresses to primary
        secondary.extra_emails.update(contact=primary)
        secondary.extra_phones.update(contact=primary)
        secondary.extra_addresses.update(contact=primary)

        # --- 2. Boolean OR ---
        for field in _BOOL_OR_FIELDS:
            if getattr(secondary, field, False):
                setattr(primary, field, True)

        # --- 3. Concatenate description (preserves chatwoot_ids) ---
        sec_desc = (secondary.description or "").strip()
        if sec_desc:
            pri_desc = (primary.description or "").strip()
            if pri_desc:
                primary.description = f"{pri_desc}\n---\n{sec_desc}"
            else:
                primary.description = sec_desc

        primary.save()

        # --- 4. Move FK references ---
        from conversations.models import Conversation
        stats["conversations"] = Conversation.objects.filter(
            contact=secondary, org=org
        ).update(contact=primary)

        from invoices.models import Estimate, Invoice, RecurringInvoice
        stats["invoices"] = Invoice.objects.filter(
            contact=secondary, org=org
        ).update(contact=primary)
        stats["estimates"] = Estimate.objects.filter(
            contact=secondary, org=org
        ).update(contact=primary)
        stats["recurring_invoices"] = RecurringInvoice.objects.filter(
            contact=secondary, org=org
        ).update(contact=primary)

        from orders.models import Order
        stats["orders"] = Order.objects.filter(
            contact=secondary, org=org
        ).update(contact=primary)

        from financeiro.models import Lancamento
        stats["lancamentos"] = Lancamento.objects.filter(
            contact=secondary, org=org
        ).update(contact=primary)

        # PaymentTransaction (financeiro) also has contact FK
        from financeiro.models import PaymentTransaction
        PaymentTransaction.objects.filter(
            contact=secondary, org=org
        ).update(contact=primary)

        from campaigns.models import CampaignRecipient
        stats["campaign_recipients"] = CampaignRecipient.objects.filter(
            contact=secondary
        ).update(contact=primary)

        # accounts.AccountEmailLog
        from accounts.models import AccountEmailLog
        AccountEmailLog.objects.filter(contact=secondary).update(contact=primary)

        # tasks.BoardTask (contact FK)
        from tasks.models import BoardTask
        BoardTask.objects.filter(
            contact=secondary, org=org
        ).update(contact=primary)

        # --- 5. Move M2M references ---
        _move_m2m("leads.Lead", "contacts", secondary, primary, stats, "leads")
        _move_m2m("opportunity.Opportunity", "contacts", secondary, primary, stats, "opportunities")
        _move_m2m("cases.Case", "contacts", secondary, primary, stats, "cases")
        _move_m2m("tasks.Task", "contacts", secondary, primary, stats, "tasks")
        _move_m2m("accounts.Account", "contacts", secondary, primary, stats, "accounts")

        # accounts.AccountEmail recipients M2M
        from accounts.models import AccountEmail
        for em in AccountEmail.objects.filter(recipients=secondary):
            em.recipients.add(primary)
            em.recipients.remove(secondary)

        # --- 6. Union contact's own M2M ---
        primary.tags.add(*secondary.tags.all())
        primary.assigned_to.add(*secondary.assigned_to.all())
        primary.teams.add(*secondary.teams.all())

        # --- 7. Move Comments and Attachments (generic FK) ---
        from common.models import Attachments, Comment
        contact_ct = ContentType.objects.get_for_model(Contact)

        stats["comments"] = Comment.objects.filter(
            content_type=contact_ct, object_id=secondary.id
        ).update(object_id=primary.id)

        stats["attachments"] = Attachments.objects.filter(
            content_type=contact_ct, object_id=secondary.id
        ).update(object_id=primary.id)

        # --- 8. Audit trail ---
        sec_name = f"{secondary.first_name} {secondary.last_name}".strip()
        sec_info = []
        if secondary.email:
            sec_info.append(secondary.email)
        if secondary.phone:
            sec_info.append(secondary.phone)
        sec_extra = f" ({', '.join(sec_info)})" if sec_info else ""

        moved_parts = []
        for key, count in stats.items():
            if count and count > 0:
                moved_parts.append(f"{count} {key}")
        moved_str = ", ".join(moved_parts) if moved_parts else "nenhuma entidade"

        audit_comment = (
            f"Contato mesclado: {sec_name}{sec_extra} foi absorvido por este contato.\n"
            f"Por: {user_email} em {timezone.now().strftime('%d/%m/%Y %H:%M')}.\n"
            f"Movido: {moved_str}."
        )

        Comment.objects.create(
            content_type=contact_ct,
            object_id=primary.id,
            comment=audit_comment,
            org=org,
        )

        # --- 9. Delete secondary ---
        secondary.delete()

    primary.refresh_from_db()
    return primary, stats


def get_merge_preview(org, primary_id, secondary_id):
    """
    Generate a preview of what a merge would look like.

    Returns dict with field-by-field preview and entity counts.
    """
    primary = Contact.objects.get(id=primary_id, org=org)
    secondary = Contact.objects.get(id=secondary_id, org=org)

    if primary.id == secondary.id:
        raise ValueError("Cannot merge a contact with itself")

    # Field-by-field preview
    merged_fields = {}
    for field in _SCALAR_FIELDS + ["first_name", "last_name"]:
        p_val = getattr(primary, field, None)
        s_val = getattr(secondary, field, None)
        if field in ("first_name", "last_name"):
            merged_fields[field] = {
                "value": p_val or "",
                "source": "primary",
            }
        elif p_val:
            merged_fields[field] = {"value": str(p_val), "source": "primary"}
        elif s_val:
            merged_fields[field] = {
                "value": str(s_val),
                "source": "secondary",
                "action": "preenchido",
            }
        else:
            merged_fields[field] = {"value": None, "source": "none"}

    # Description concatenation preview
    p_desc = (primary.description or "").strip()
    s_desc = (secondary.description or "").strip()
    if p_desc and s_desc:
        merged_fields["description"] = {
            "value": f"{p_desc}\n---\n{s_desc}",
            "source": "concatenado",
            "action": "mesclado",
        }
    elif s_desc:
        merged_fields["description"] = {
            "value": s_desc, "source": "secondary", "action": "preenchido",
        }
    else:
        merged_fields["description"] = {
            "value": p_desc or None, "source": "primary",
        }

    # Entity counts
    from conversations.models import Conversation
    from invoices.models import Estimate, Invoice
    from orders.models import Order

    entities = {
        "conversations": Conversation.objects.filter(contact=secondary, org=org).count(),
        "invoices": Invoice.objects.filter(contact=secondary, org=org).count(),
        "estimates": Estimate.objects.filter(contact=secondary, org=org).count(),
        "orders": Order.objects.filter(contact=secondary, org=org).count(),
        "leads": secondary.lead_contacts.count(),
        "opportunities": secondary.opportunity_contacts.count(),
        "cases": secondary.case_contacts.count(),
        "tasks": secondary.task_contacts.count(),
    }

    # Channels present
    channels = set()
    for conv in Conversation.objects.filter(
        contact__in=[primary, secondary], org=org
    ).values_list("channel", flat=True).distinct():
        channels.add(conv)

    # Integration IDs preserved
    integration_ids = {}
    chatwoot_ids = set()
    for desc in [primary.description or "", secondary.description or ""]:
        chatwoot_ids.update(re.findall(r"chatwoot_id:(\d+)", desc))
    if chatwoot_ids:
        integration_ids["chatwoot_ids"] = sorted(chatwoot_ids)
    if primary.talkhub_subscriber_id or secondary.talkhub_subscriber_id:
        integration_ids["talkhub_subscriber_id"] = (
            primary.talkhub_subscriber_id or secondary.talkhub_subscriber_id
        )
    if primary.omni_user_ns or secondary.omni_user_ns:
        integration_ids["omni_user_ns"] = (
            primary.omni_user_ns or secondary.omni_user_ns
        )

    return {
        "merged_preview": merged_fields,
        "entities_to_move": entities,
        "channels_unified": sorted(channels),
        "integration_ids_preserved": integration_ids,
    }


def _move_m2m(model_label, field_name, secondary, primary, stats, stat_key):
    """Move M2M references from secondary to primary."""
    from django.apps import apps
    Model = apps.get_model(model_label)
    qs = Model.objects.filter(**{field_name: secondary})
    count = qs.count()
    for obj in qs:
        m2m = getattr(obj, field_name)
        m2m.add(primary)
        m2m.remove(secondary)
    stats[stat_key] = count
