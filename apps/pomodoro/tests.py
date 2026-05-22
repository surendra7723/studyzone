from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.pomodoro.models import PomodoroSession


class PomodoroModelTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="alice", password="password123"
        )

    def test_completed_session_requires_end_time(self):
        session = PomodoroSession(
            user=self.user, start_time=timezone.now(), is_completed=True
        )

        with self.assertRaises(ValidationError):
            session.full_clean()

    def test_end_time_cannot_be_before_start_time(self):
        started_at = timezone.now()
        session = PomodoroSession(
            user=self.user,
            start_time=started_at,
            end_time=started_at - timedelta(minutes=5),
            is_completed=True,
        )

        with self.assertRaises(ValidationError):
            session.full_clean()
