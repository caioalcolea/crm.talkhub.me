"""
Chatwoot ActionCable WebSocket listener.

Celery task that maintains a persistent WebSocket connection to Chatwoot's
ActionCable endpoint for real-time events (typing indicators, presence).

This complements webhooks with low-latency events that webhooks don't cover.
"""

import json
import logging
import time

from celery import shared_task

logger = logging.getLogger(__name__)

# Exponential backoff config
INITIAL_BACKOFF = 1
MAX_BACKOFF = 30
MAX_CONSECUTIVE_FAILURES = 10


@shared_task(name="chatwoot.ws_listener", bind=True, max_retries=None, acks_late=True)
def chatwoot_ws_listener(self, org_id, connection_id):
    """
    Connect to Chatwoot's ActionCable WebSocket and relay typing/presence events
    to CRM agents via Django Channels.

    This is a long-running task that reconnects on failure with exponential backoff.
    """
    try:
        import websocket
    except ImportError:
        logger.error(
            "websocket-client not installed. Install with: pip install websocket-client"
        )
        return

    from integrations.models import IntegrationConnection

    consecutive_failures = 0
    backoff = INITIAL_BACKOFF

    while consecutive_failures < MAX_CONSECUTIVE_FAILURES:
        try:
            conn = IntegrationConnection.objects.get(
                id=connection_id, is_active=True, is_connected=True
            )
        except IntegrationConnection.DoesNotExist:
            logger.info(
                "Connection %s no longer active, stopping WS listener", connection_id
            )
            return

        config = conn.config_json or {}
        chatwoot_url = config.get("chatwoot_url", "").rstrip("/")
        pubsub_token = config.get("pubsub_token", "")
        account_id = config.get("account_id")

        if not chatwoot_url or not pubsub_token:
            logger.warning(
                "Missing chatwoot_url or pubsub_token for connection %s", connection_id
            )
            return

        # Build WebSocket URL
        ws_scheme = "wss" if chatwoot_url.startswith("https") else "ws"
        ws_host = chatwoot_url.replace("https://", "").replace("http://", "")
        ws_url = f"{ws_scheme}://{ws_host}/cable"

        logger.info("Connecting to Chatwoot ActionCable: %s (org=%s)", ws_url, org_id)

        try:
            ws = websocket.create_connection(ws_url, timeout=60)

            # Subscribe to RoomChannel
            subscribe_cmd = {
                "command": "subscribe",
                "identifier": json.dumps(
                    {
                        "channel": "RoomChannel",
                        "pubsub_token": pubsub_token,
                        "account_id": account_id,
                    }
                ),
            }
            ws.send(json.dumps(subscribe_cmd))

            # Reset backoff on successful connection
            consecutive_failures = 0
            backoff = INITIAL_BACKOFF

            logger.info("Subscribed to Chatwoot RoomChannel (org=%s)", org_id)

            # Message loop
            while True:
                try:
                    raw = ws.recv()
                    if not raw:
                        break

                    data = json.loads(raw)

                    # ActionCable ping — ignore
                    if data.get("type") in ("ping", "welcome", "confirm_subscription"):
                        continue

                    # Process message
                    message = data.get("message", {})
                    event_type = message.get("event")

                    if event_type == "typing_on":
                        _broadcast_typing(org_id, message, is_typing=True)
                    elif event_type == "typing_off":
                        _broadcast_typing(org_id, message, is_typing=False)

                except websocket.WebSocketTimeoutException:
                    # Send ping to keep connection alive
                    try:
                        ws.ping()
                    except Exception:
                        break
                except websocket.WebSocketConnectionClosedException:
                    break
                except json.JSONDecodeError:
                    continue

            ws.close()

        except Exception as e:
            logger.warning(
                "Chatwoot WS connection failed (org=%s): %s", org_id, e
            )
            consecutive_failures += 1
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)
            continue

    logger.error(
        "Chatwoot WS listener giving up after %d consecutive failures (org=%s)",
        MAX_CONSECUTIVE_FAILURES,
        org_id,
    )


def _broadcast_typing(org_id, message, is_typing):
    """Broadcast typing indicator to CRM agents via Channels."""
    try:
        from conversations.broadcast import _get_layer
        from asgiref.sync import async_to_sync

        layer = _get_layer()
        if not layer:
            return

        conversation_data = message.get("conversation", {})
        conv_id = conversation_data.get("id")
        if not conv_id:
            return

        # Find CRM conversation by chatwoot_conversation_id
        from conversations.models import Conversation

        crm_conv = Conversation.objects.filter(
            org_id=org_id,
            metadata_json__chatwoot_conversation_id=conv_id,
        ).first()
        if not crm_conv:
            return

        user_info = message.get("user", {})
        async_to_sync(layer.group_send)(
            f"conversation_{crm_conv.id}",
            {
                "type": "typing.indicator",
                "data": {
                    "conversation_id": str(crm_conv.id),
                    "is_typing": is_typing,
                    "user_name": user_info.get("name", ""),
                },
            },
        )
    except Exception as e:
        logger.debug("Failed to broadcast typing indicator: %s", e)
