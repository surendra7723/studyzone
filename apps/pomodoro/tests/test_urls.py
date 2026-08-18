from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class PomodoroUrlResolutionTests(APITestCase):
    def test_pomodoro_urls_mounted(self):
        self.assertEqual(
            reverse("pomodoro:pomodoro-session-list"),
            "/api/pomodoro/sessions/",
        )

    def test_pomodoro_list_endpoint_accessible(self):
        user = User.objects.create_user(
            username="pomo_user", password="StrongPass123!"
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(reverse("pomodoro:pomodoro-session-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pomodoro_create_endpoint_accessible(self):
        user = User.objects.create_user(
            username="pomo_user", password="StrongPass123!"
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            reverse("pomodoro:pomodoro-session-list"),
            {
                "session_type": "focus",
                "active_minutes": 25,
                "break_minutes": 5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_pomodoro_detail_endpoint_accessible(self):
        user = User.objects.create_user(
            username="pomo_user", password="StrongPass123!"
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            reverse("pomodoro:pomodoro-session-list"),
            {
                "session_type": "focus",
                "active_minutes": 25,
                "break_minutes": 5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.data["id"]
        detail_response = self.client.get(
            reverse("pomodoro:pomodoro-session-detail", args=[session_id])
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_request_returns_401(self):
        response = self.client.get(reverse("pomodoro:pomodoro-session-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
