from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.pomodoro.models import PomodoroSession, TaskSession
from apps.tasks.models.tasks import Task, Category


class PomodoroModelsTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="pass")
        self.category = Category.objects.create(user=self.user, name="Work")
        self.task = Task.objects.create(
            user=self.user, title="Test Task", estimated_pomodoros=1
        )

    def test_pomodoro_end_time_before_start_raises(self):
        start = timezone.now()
        end = start - timedelta(minutes=5)
        session = PomodoroSession(
            user=self.user, start_time=start, end_time=end, is_completed=True
        )
        with self.assertRaises(ValidationError):
            session.full_clean()

    def test_completed_without_end_time_raises(self):
        start = timezone.now()
        session = PomodoroSession(
            user=self.user, start_time=start, end_time=None, is_completed=True
        )
        with self.assertRaises(ValidationError):
            session.full_clean()

    def test_task_session_user_mismatch_raises(self):
        User = get_user_model()
        other = User.objects.create_user(username="other", password="p")
        other_task = Task.objects.create(
            user=other, title="Other", estimated_pomodoros=1
        )
        # create a valid session for self.user
        session = PomodoroSession.objects.create(
            user=self.user, is_completed=False, active_minutes=0
        )
        ts = TaskSession(task=other_task, pomodoro_session=session, duration_minutes=25)
        with self.assertRaises(ValidationError):
            ts.full_clean()

    def test_valid_pomodoro_and_task_session(self):
        start = timezone.now()
        end = start + timedelta(minutes=25)
        session = PomodoroSession(
            user=self.user,
            start_time=start,
            end_time=end,
            is_completed=True,
            active_minutes=25,
        )
        # should not raise when clean is valid
        session.full_clean()
        session.save()
        ts = TaskSession(task=self.task, pomodoro_session=session, duration_minutes=25)
        ts.full_clean()
        ts.save()
