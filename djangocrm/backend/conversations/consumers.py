"""WebSocket consumer for real-time conversation updates."""

import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for conversation real-time updates.

    Groups:
      - conversations_{org_id}: All conversation updates for an org
      - conversation_{conversation_id}: Messages for a specific conversation

    Client messages:
      - {"type": "watch", "conversation_id": "<uuid>"}: Join conversation group
      - {"type": "unwatch", "conversation_id": "<uuid>"}: Leave conversation group
      - {"type": "refresh_token", "token": "<jwt>"}: Re-authenticate with new JWT
    """

    async def connect(self):
        self.user = self.scope.get("user", AnonymousUser())
        self.org_id = self.scope.get("org_id")
        self.watched_conversations = set()

        if isinstance(self.user, AnonymousUser) or not self.org_id:
            await self.close(code=4401)
            return

        self.org_group = f"conversations_{self.org_id}"
        await self.channel_layer.group_add(self.org_group, self.channel_name)
        await self.accept()
        logger.info("WS connected: user=%s org=%s", self.user.id, self.org_id)

    async def disconnect(self, close_code):
        if hasattr(self, "org_group"):
            await self.channel_layer.group_discard(self.org_group, self.channel_name)

        for conv_id in self.watched_conversations:
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}", self.channel_name
            )
        self.watched_conversations.clear()

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")

        if msg_type == "watch":
            conv_id = content.get("conversation_id")
            if conv_id and conv_id not in self.watched_conversations:
                await self.channel_layer.group_add(
                    f"conversation_{conv_id}", self.channel_name
                )
                self.watched_conversations.add(conv_id)

        elif msg_type == "unwatch":
            conv_id = content.get("conversation_id")
            if conv_id and conv_id in self.watched_conversations:
                await self.channel_layer.group_discard(
                    f"conversation_{conv_id}", self.channel_name
                )
                self.watched_conversations.discard(conv_id)

        elif msg_type == "refresh_token":
            token_str = content.get("token", "")
            user, org_id = await self._validate_token(token_str)
            if isinstance(user, AnonymousUser) or not org_id:
                await self.close(code=4401)
                return
            # Update scope with refreshed auth
            self.user = user
            if str(org_id) != str(self.org_id):
                # Org changed — rejoin correct group
                await self.channel_layer.group_discard(
                    self.org_group, self.channel_name
                )
                self.org_id = org_id
                self.org_group = f"conversations_{self.org_id}"
                await self.channel_layer.group_add(
                    self.org_group, self.channel_name
                )

    # --- Group message handlers ---

    async def conversation_update(self, event):
        """Push conversation update to client."""
        await self.send_json(
            {"type": "conversation_update", "data": event.get("data", {})}
        )

    async def new_message(self, event):
        """Push new message to client."""
        await self.send_json(
            {"type": "new_message", "data": event.get("data", {})}
        )

    async def typing_indicator(self, event):
        """Forward typing indicator to client."""
        await self.send_json(
            {"type": "typing", "data": event.get("data", {})}
        )

    # --- Helpers ---

    @database_sync_to_async
    def _validate_token(self, token_str):
        try:
            token = AccessToken(token_str)
            user_id = token.get("user_id")
            org_id = token.get("org_id")
            from common.models import User

            user = User.objects.get(id=user_id)
            return user, org_id
        except Exception:
            return AnonymousUser(), None
