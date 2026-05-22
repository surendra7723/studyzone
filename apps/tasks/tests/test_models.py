from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.pomodoro.models import PomodoroSession, TaskSession
from apps.tasks.models.tasks import Category, Task


class TasksModelTest(TestCase):
    """Unit tests for tasks models."""

    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="alice", password="password123"
        )
        self.other_user = self.User.objects.create_user(
            username="bob", password="password123"
        )

    def test_category_name_is_unique_per_user(self):
        Category.objects.create(user=self.user, name="Math")

        duplicate = Category(user=self.user, name="Math")

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_task_category_must_belong_to_same_user(self):
        foreign_category = Category.objects.create(user=self.other_user, name="Work")
        task = Task(user=self.user, category=foreign_category, title="Read chapter 1")

        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_task_session_requires_matching_user(self):
        task = Task.objects.create(user=self.user, title="Review notes")
        session = PomodoroSession.objects.create(user=self.other_user)
        task_session = TaskSession(
            task=task, pomodoro_session=session, duration_minutes=25
        )

        with self.assertRaises(ValidationError):
            task_session.full_clean()
