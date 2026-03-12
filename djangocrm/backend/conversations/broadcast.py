"""Broadcast helpers for pushing real-time updates via Django Channels."""

import logging

from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def _get_layer():
    try:
        from channels.layers import get_channel_layer

        return get_channel_layer()
    except Exception:
        return None


def broadcast_conversation_update(org_id, conversation_data):
    """Push conversation update to all agents in the org."""
    layer = _get_layer()
    if not layer:
        return
    try:
        async_to_sync(layer.group_send)(
            f"conversations_{org_id}",
            {"type": "conversation.update", "data": conversation_data},
        )
    except Exception as e:
        logger.warning("Failed to broadcast conversation update: %s", e)


def broadcast_new_message(org_id, conversation_id, message_data):
    """Push new message to agents watching this conversation."""
    layer = _get_layer()
    if not layer:
        return
    try:
        # Send to conversation-specific group
        async_to_sync(layer.group_send)(
            f"conversation_{conversation_id}",
            {"type": "new.message", "data": message_data},
        )
        # Also notify the org group (for list reordering)
        async_to_sync(layer.group_send)(
            f"conversations_{org_id}",
            {
                "type": "conversation.update",
                "data": {
                    "conversation_id": str(conversation_id),
                    "has_new_message": True,
                },
            },
        )
    except Exception as e:
        logger.warning("Failed to broadcast new message: %s", e)
