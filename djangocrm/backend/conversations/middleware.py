"""JWT authentication middleware for Django Channels WebSocket connections."""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_and_org(token_str):
    """Validate JWT token and return (user, org_id) or (AnonymousUser, None)."""
    try:
        token = AccessToken(token_str)
        user_id = token.get("user_id")
        org_id = token.get("org_id")

        from common.models import User

        user = User.objects.get(id=user_id)
        return user, org_id
    except Exception:
        return AnonymousUser(), None


class JWTAuthMiddleware(BaseMiddleware):
    """
    Extract JWT from query string ?token=<jwt> and set scope["user"] and scope["org_id"].
    """

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_list = params.get("token", [])

        if token_list:
            user, org_id = await get_user_and_org(token_list[0])
            scope["user"] = user
            scope["org_id"] = org_id
        else:
            scope["user"] = AnonymousUser()
            scope["org_id"] = None

        return await super().__call__(scope, receive, send)
