"""
Unified dispatch service for sending messages through communication channels.

Uses ChannelProvider registry (channels/registry.py) when available,
with fallback to the legacy automations/router.py for channels without a provider.
"""

import logging

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
    Internal notification dispatch — creates a task or logs for internal consumption.

    For now, this is a no-op placeholder that logs the notification.
    Will be expanded when the internal notification system is built.
    """
    logger.info(
        "Internal dispatch: org=%s dest=%s subject=%s",
        org_id,
        destination,
        message_data.get("subject", "(no subject)"),
    )
    return {
        "success": True,
        "message_id": f"internal-{timezone.now().isoformat()}",
        "error": "",
    }
