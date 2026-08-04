from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.pomodoro.models import PomodoroSession, TaskSession
from apps.pomodoro.tasks import cleanup_orphan_pomodoro_sessions
from apps.tasks.models.tasks import Task


class PomodoroTaskCleanupTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="pass")
        self.task = Task.objects.create(
            user=self.user,
            title="Cleanup task",
            estimated_pomodoros=1,
        )

    def test_cleanup_deletes_old_orphan_sessions(self):
        session = PomodoroSession.objects.create(user=self.user)
        PomodoroSession.objects.filter(pk=session.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )

        deleted_count = cleanup_orphan_pomodoro_sessions(retention_hours=24)

        self.assertEqual(deleted_count, 1)
        self.assertFalse(PomodoroSession.objects.filter(pk=session.pk).exists())

    def test_cleanup_keeps_sessions_with_task_links(self):
        session = PomodoroSession.objects.create(user=self.user)
        TaskSession.objects.create(
            task=self.task,
            pomodoro_session=session,
            duration_minutes=25,
        )
        PomodoroSession.objects.filter(pk=session.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )

        deleted_count = cleanup_orphan_pomodoro_sessions(retention_hours=24)

        self.assertEqual(deleted_count, 0)
        self.assertTrue(PomodoroSession.objects.filter(pk=session.pk).exists())
