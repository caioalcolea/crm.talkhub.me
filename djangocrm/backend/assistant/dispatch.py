"""
Unified dispatch service for sending messages through communication channels.

Uses ChannelProvider registry (channels/registry.py) when available,
with fallback to the legacy automations/router.py for channels without a provider.
"""

import logging

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


def dispatch_message(org_id, channel_type, destination, message_data, metadata=None):
    """
    Send a message through the specified channel.

    Tries ChannelProvider from the registry first. Falls back to the legacy
    automations.router.dispatch() for channels without a registered provider.

    Args:
        org_id: UUID of the organization
        channel_type: Channel type string (e.g., "smtp_native", "talkhub_omni", "internal")
        destination: Recipient address (email, phone, user_id)
        message_data: Dict with message payload (subject, body, template_id, etc.)
        metadata: Optional dict with additional context

    Returns:
        Dict with dispatch result: {"success": bool, "message_id": str, "error": str}
    """
    if channel_type == "internal":
        return _dispatch_internal(org_id, destination, message_data, metadata)

    # Check channel rate limit before dispatching
    allowed, limit = _check_channel_rate_limit(org_id, channel_type)
    if not allowed:
        logger.warning(
            "Channel rate limit exceeded: org=%s channel=%s limit=%s/hr",
            org_id, channel_type, limit,
        )
        return {
            "success": False,
            "message_id": "",
            "error": f"rate_limit_exceeded:{channel_type}:{limit}/hr",
        }

    try:
        from channels.registry import ChannelRegistry
        from channels.models import ChannelConfig

        provider_class = ChannelRegistry.get(channel_type)
        if provider_class:
            channel_config = ChannelConfig.objects.filter(
                org_id=org_id, channel_type=channel_type, is_active=True
            ).first()

            if not channel_config:
                logger.warning(
                    "No active ChannelConfig for type=%s org=%s, falling back to legacy",
                    channel_type, org_id,
                )
            else:
                provider = provider_class()
                result = provider.send_message(channel_config, destination, message_data)
                _increment_channel_rate(org_id, channel_type)
                return {
                    "success": True,
                    "message_id": getattr(result, "message_id", ""),
                    "error": "",
                }
    except Exception as e:
        logger.error(
            "ChannelProvider dispatch failed for %s: %s, falling back to legacy",
            channel_type, e,
        )

    # Fallback to legacy automations router
    try:
        from automations.router import dispatch
        body = message_data.get("body", "")
        result = dispatch(org_id, channel_type, destination, body, metadata or {})
        _increment_channel_rate(org_id, channel_type)
        return {
            "success": True,
            "message_id": str(result) if result else "",
            "error": "",
        }
    except Exception as e:
        logger.error("Legacy dispatch also failed for %s: %s", channel_type, e)
        return {
            "success": False,
            "message_id": "",
            "error": str(e),
        }


def _dispatch_internal(org_id, destination, message_data, metadata=None):
    """
    Internal notification dispatch — creates an in-app Notification.

    Args:
        org_id: UUID of the organization
        destination: Profile UUID (user_id) to notify
        message_data: Dict with subject, body
        metadata: Optional dict with additional context (link, type, etc.)
    """
    logger.info(
        "Internal dispatch: org=%s dest=%s subject=%s",
        org_id,
        destination,
        message_data.get("subject", "(no subject)"),
    )

    try:
        from assistant.models import Notification
        from common.models import Profile

        # destination is a user/profile ID
        profile = Profile.objects.filter(id=destination, org_id=org_id).first()
        if not profile:
            # Try interpreting destination as email
            profile = Profile.objects.filter(
                email=destination, org_id=org_id
            ).first()

        if profile:
            meta = metadata or {}
            Notification.objects.create(
                org_id=org_id,
                user=profile,
                type=meta.get("notification_type", "system"),
                title=message_data.get("subject", "Notificação")[:200],
                body=message_data.get("body", "")[:2000],
                link=meta.get("link", ""),
                metadata=meta,
            )
    except Exception as e:
        logger.error("Failed to create internal notification: %s", e)

    return {
        "success": True,
        "message_id": f"internal-{timezone.now().isoformat()}",
        "error": "",
    }


def _check_channel_rate_limit(org_id, channel_type):
    """
    Check if org has exceeded channel rate limit (Redis counter, 1hr window).

    Returns:
        Tuple of (allowed: bool, limit: int|None)
    """
    try:
        from common.models import Org
        org = Org.objects.get(id=org_id)
        limits = getattr(org, "channel_rate_limits", None) or {}
        limit = limits.get(channel_type)
        if not limit:
            return True, None  # No limit configured

        key = f"channel_rate:{org_id}:{channel_type}"
        current = cache.get(key, 0)
        if current >= limit:
            return False, limit
        return True, limit
    except Exception as e:
        logger.error("Error checking channel rate limit: %s", e)
        return True, None  # Allow on error


def _increment_channel_rate(org_id, channel_type):
    """Increment the channel rate counter after a successful dispatch."""
    try:
        key = f"channel_rate:{org_id}:{channel_type}"
        current = cache.get(key, 0)
        cache.set(key, current + 1, 3600)  # 1 hour TTL
    except Exception as e:
        logger.error("Error incrementing channel rate: %s", e)
