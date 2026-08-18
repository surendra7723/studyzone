from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
)
class ServerHealthApiTests(APITestCase):
    def test_live_endpoint_returns_200(self):
        response = self.client.get(reverse("server:live"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "live")
        self.assertIn("timestamp", response.data)

    def test_live_endpoint_does_not_check_dependencies(self):
        with patch(
            "apps.server.views.base.ServerBaseView.check_database_connection"
        ) as mock_db, patch(
            "apps.server.views.base.ServerBaseView.check_cache_connection"
        ) as mock_cache:
            self.client.get(reverse("server:live"))
            mock_db.assert_not_called()
            mock_cache.assert_not_called()

    def test_ready_endpoint_returns_200_when_healthy(self):
        with patch(
            "apps.server.views.base.ServerBaseView.check_database_connection",
            return_value=(True, None),
        ), patch(
            "apps.server.views.base.ServerBaseView.check_cache_connection",
            return_value=(True, None),
        ):
            response = self.client.get(reverse("server:ready"))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["status"], "ready")
            self.assertIn("timestamp", response.data)

    def test_ready_endpoint_returns_503_when_db_down(self):
        with patch(
            "apps.server.views.base.ServerBaseView.check_database_connection",
            return_value=(False, "DB error"),
        ), patch(
            "apps.server.views.base.ServerBaseView.check_cache_connection",
            return_value=(True, None),
        ):
            response = self.client.get(reverse("server:ready"))
            self.assertEqual(
                response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE
            )
            self.assertEqual(response.data["status"], "not ready")

    def test_ready_endpoint_returns_503_when_cache_down(self):
        with patch(
            "apps.server.views.base.ServerBaseView.check_database_connection",
            return_value=(True, None),
        ), patch(
            "apps.server.views.base.ServerBaseView.check_cache_connection",
            return_value=(False, "Cache error"),
        ):
            response = self.client.get(reverse("server:ready"))
            self.assertEqual(
                response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE
            )
            self.assertEqual(response.data["status"], "not ready")

    def test_health_endpoints_are_unauthenticated(self):
        response_live = self.client.get(reverse("server:live"))
        response_ready = self.client.get(reverse("server:ready"))
        self.assertNotEqual(
            response_live.status_code, status.HTTP_401_UNAUTHORIZED
        )
        self.assertNotEqual(
            response_ready.status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_server_urls_are_mounted(self):
        self.assertEqual(reverse("server:live"), "/api/server/live/")
        self.assertEqual(reverse("server:ready"), "/api/server/ready/")
