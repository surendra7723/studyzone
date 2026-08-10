from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.settings import api_settings

User = get_user_model()


@database_sync_to_async
def _get_user(user_id):
    try:
        return User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        close_old_connections()
        user = await self.get_user(scope)
        scope["user"] = user
        return await self.inner(scope, receive, send)

    async def get_user(self, scope):
        query_string = parse_qs(scope.get("query_string", b"").decode())
        raw_token = None
        if query_string.get("token"):
            raw_token = query_string["token"][0]
        else:
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization")
            if auth_header:
                auth_value = auth_header.decode()
                if auth_value.lower().startswith("bearer "):
                    raw_token = auth_value.split(" ", 1)[1].strip()

        if not raw_token:
            return AnonymousUser()

        try:
            token = AccessToken(raw_token)
            user_id = token[api_settings.USER_ID_CLAIM]
        except Exception:
            return AnonymousUser()

        if not user_id:
            return AnonymousUser()
        return await _get_user(user_id)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
