"""
Django signals for automatic activity tracking across CRM entities
and org-level initialization.

This module registers post_save and post_delete signals on all major CRM models
to automatically create Activity records when entities are created, updated, or deleted.
It also seeds default financial data (Centro de Custo, Formas de Pagamento) when a new
organization is created.
"""

import logging

from crum import get_current_request
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.models import Activity, Org

logger = logging.getLogger(__name__)


# =============================================================================
# Org creation — seed defaults
# =============================================================================


@receiver(post_save, sender=Org)
def seed_org_defaults_on_creation(sender, instance, created, **kwargs):
    """Auto-seed default Centro de Custo and Formas de Pagamento for new orgs."""
    if not created:
        return

    try:
        from common.management.commands.seed_org_defaults import seed_for_org
        seed_for_org(instance)
    except Exception as exc:
        # Don't break org creation if seeding fails
        logger.error("Failed to seed defaults for org %s: %s", instance.id, exc)


# =============================================================================
# Activity tracking
# =============================================================================


def get_entity_name(instance):
    """Get a display name for an entity instance"""
    # Try common name attributes
    if hasattr(instance, "name") and instance.name:
        return str(instance.name)
    if hasattr(instance, "title") and instance.title:
        return str(instance.title)
    if hasattr(instance, "first_name"):
        name = f"{instance.first_name or ''} {instance.last_name or ''}".strip()
        if name:
            return name
    if hasattr(instance, "email") and instance.email:
        return str(instance.email)
    if hasattr(instance, "subject") and instance.subject:
        return str(instance.subject)
    # Fallback to string representation
    return str(instance)[:100]


def create_activity(instance, action, entity_type):
    """Create an activity record for a model instance"""
    request = get_current_request()

    # Skip if no request context (e.g., management commands)
    if not request:
        return

    # Get profile from request
    profile = getattr(request, "profile", None)
    if not profile:
        return

    # Get org from instance or profile
    org = getattr(instance, "org", None)
    if not org:
        org = getattr(profile, "org", None)
    if not org:
        return

    # Create activity record
    Activity.objects.create(
        user=profile,
        action=action,
        entity_type=entity_type,
        entity_id=instance.id,
        entity_name=get_entity_name(instance),
        org=org,
    )


# Account signals
@receiver(post_save, sender="accounts.Account")
def account_post_save(sender, instance, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    create_activity(instance, action, "Account")


@receiver(post_delete, sender="accounts.Account")
def account_post_delete(sender, instance, **kwargs):
    create_activity(instance, "DELETE", "Account")


# Lead signals
@receiver(post_save, sender="leads.Lead")
def lead_post_save(sender, instance, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    create_activity(instance, action, "Lead")


@receiver(post_delete, sender="leads.Lead")
def lead_post_delete(sender, instance, **kwargs):
    create_activity(instance, "DELETE", "Lead")


# Contact signals
@receiver(post_save, sender="contacts.Contact")
def contact_post_save(sender, instance, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    create_activity(instance, action, "Contact")


@receiver(post_delete, sender="contacts.Contact")
def contact_post_delete(sender, instance, **kwargs):
    create_activity(instance, "DELETE", "Contact")


# Opportunity signals
@receiver(post_save, sender="opportunity.Opportunity")
def opportunity_post_save(sender, instance, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    create_activity(instance, action, "Opportunity")


@receiver(post_delete, sender="opportunity.Opportunity")
def opportunity_post_delete(sender, instance, **kwargs):
    create_activity(instance, "DELETE", "Opportunity")


# Case signals
@receiver(post_save, sender="cases.Case")
def case_post_save(sender, instance, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    create_activity(instance, action, "Case")


@receiver(post_delete, sender="cases.Case")
def case_post_delete(sender, instance, **kwargs):
    create_activity(instance, "DELETE", "Case")


# Task signals
@receiver(post_save, sender="tasks.Task")
def task_post_save(sender, instance, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    create_activity(instance, action, "Task")


@receiver(post_delete, sender="tasks.Task")
def task_post_delete(sender, instance, **kwargs):
    create_activity(instance, "DELETE", "Task")


# Invoice signals
@receiver(post_save, sender="invoices.Invoice")
def invoice_post_save(sender, instance, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    create_activity(instance, action, "Invoice")


@receiver(post_delete, sender="invoices.Invoice")
def invoice_post_delete(sender, instance, **kwargs):
    create_activity(instance, "DELETE", "Invoice")
