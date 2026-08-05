import asyncio

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.social.middleware import JwtAuthMiddleware

User = get_user_model()


class JwtAuthMiddlewareTests(TransactionTestCase):
    def test_get_user_from_query_token(self):
        user = User.objects.create_user(username="alice", password="StrongPass123!")
        token = str(RefreshToken.for_user(user).access_token)
        middleware = JwtAuthMiddleware(lambda scope, receive, send: None)
        scope = {"query_string": f"token={token}".encode(), "headers": []}

        resolved_user = asyncio.run(middleware.get_user(scope))

        self.assertEqual(resolved_user.id, user.id)
