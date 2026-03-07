"""
Django signals para sync bidirecional TalkHub Omni ↔ CRM.

Signals:
- Contact post_save → push_contact_to_omni (se talkhub_subscriber_id preenchido)
- Case post_save → push_case_to_omni (se omni_ticket_item_id preenchido)
- Lead post_save → push_lead_to_omni (se omni_ticket_item_id preenchido)
- Tag post_save → criar tag no Omni
- Tag post_delete → excluir tag no Omni

Anti-loop: cada signal verifica sync_lock no Redis (TTL=5s).
"""

import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

SYNC_LOCK_TTL = 5  # seconds


def _is_locked(cache_key: str) -> bool:
    return bool(cache.get(cache_key))


def _set_lock(cache_key: str):
    cache.set(cache_key, True, timeout=SYNC_LOCK_TTL)


@receiver(post_save, sender="contacts.Contact")
def contact_post_save(sender, instance, **kwargs):
    """Propagar Contact → TalkHub Omni se subscriber_id preenchido."""
    if not instance.talkhub_subscriber_id:
        return
    if not instance.org_id:
        return

    cache_key = f"sync_lock:contact:{instance.talkhub_subscriber_id}:{instance.org_id}"
    if _is_locked(cache_key):
        return

    _set_lock(cache_key)

    try:
        from .tasks import push_contact_to_omni
        push_contact_to_omni.delay(str(instance.org_id), str(instance.id))
    except Exception as exc:
        logger.warning("Failed to enqueue push_contact_to_omni: %s", exc)


@receiver(post_save, sender="cases.Case")
def case_post_save(sender, instance, **kwargs):
    """Propagar Case → TalkHub Omni ticket se omni_ticket_item_id preenchido."""
    if not getattr(instance, "omni_ticket_item_id", None):
        return
    if not instance.org_id:
        return

    cache_key = f"sync_lock:ticket:{instance.omni_ticket_item_id}:{instance.org_id}"
    if _is_locked(cache_key):
        return

    _set_lock(cache_key)

    try:
        from .tasks import push_case_to_omni_task
        push_case_to_omni_task.delay(str(instance.org_id), str(instance.id))
    except Exception as exc:
        logger.warning("Failed to enqueue push_case_to_omni: %s", exc)


@receiver(post_save, sender="leads.Lead")
def lead_post_save(sender, instance, **kwargs):
    """Propagar Lead → TalkHub Omni ticket se omni_ticket_item_id preenchido."""
    if not getattr(instance, "omni_ticket_item_id", None):
        return
    if not instance.org_id:
        return

    cache_key = f"sync_lock:ticket:{instance.omni_ticket_item_id}:{instance.org_id}"
    if _is_locked(cache_key):
        return

    _set_lock(cache_key)

    try:
        from .tasks import push_lead_to_omni_task
        push_lead_to_omni_task.delay(str(instance.org_id), str(instance.id))
    except Exception as exc:
        logger.warning("Failed to enqueue push_lead_to_omni: %s", exc)


@receiver(post_save, sender="common.Tags")
def tag_post_save(sender, instance, created, **kwargs):
    """Criar tag no TalkHub Omni quando criada no CRM."""
    if not created:
        return
    if not instance.org_id:
        return

    try:
        from .tasks import sync_tag_to_omni
        sync_tag_to_omni.delay(str(instance.org_id), instance.name)
    except Exception as exc:
        logger.warning("Failed to enqueue sync_tag_to_omni: %s", exc)


@receiver(post_delete, sender="common.Tags")
def tag_post_delete(sender, instance, **kwargs):
    """Excluir tag no TalkHub Omni quando excluída no CRM."""
    if not instance.org_id:
        return
    tag_ns = getattr(instance, "talkhub_tag_ns", None)
    if not tag_ns:
        return

    try:
        from .tasks import delete_tag_from_omni
        delete_tag_from_omni.delay(str(instance.org_id), tag_ns)
    except Exception as exc:
        logger.warning("Failed to enqueue delete_tag_from_omni: %s", exc)
