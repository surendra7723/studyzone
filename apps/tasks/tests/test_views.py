from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.tasks.models.tasks import Category, Task

User = get_user_model()


class TaskBulkOperationsApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", password="StrongPass123!"
        )
        self.other_user = User.objects.create_user(
            username="bob", password="StrongPass123!"
        )
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(user=self.user, name="Work")

    def test_bulk_create_tasks(self):
        response = self.client.post(
            reverse("tasks:task-bulk-create"),
            [
                {
                    "title": "Task 1",
                    "category": self.category.id,
                    "priority": 1,
                },
                {
                    "title": "Task 2",
                    "category": self.category.id,
                    "priority": 2,
                },
            ],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(Task.objects.filter(user=self.user).count(), 2)

    def test_bulk_create_validates_each_task(self):
        response = self.client.post(
            reverse("tasks:task-bulk-create"),
            [
                {
                    "title": "Task 1",
                    "category": self.category.id,
                    "priority": 1,
                },
                {
                    "title": "",
                    "category": self.category.id,
                    "priority": 2,
                },
            ],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Task.objects.count(), 0)

    def test_bulk_create_assigns_user(self):
        response = self.client.post(
            reverse("tasks:task-bulk-create"),
            [{"title": "Task 1", "category": self.category.id, "priority": 1}],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.first().user, self.user)

    def test_bulk_update_tasks(self):
        task1 = Task.objects.create(
            user=self.user, category=self.category, title="Task 1", priority=1
        )
        task2 = Task.objects.create(
            user=self.user, category=self.category, title="Task 2", priority=2
        )
        response = self.client.patch(
            reverse("tasks:task-bulk-update"),
            [
                {"id": task1.id, "is_completed": True},
                {"id": task2.id, "is_completed": True},
            ],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        task1.refresh_from_db()
        task2.refresh_from_db()
        self.assertTrue(task1.is_completed)
        self.assertTrue(task2.is_completed)

    def test_bulk_update_validates_ownership(self):
        other_category = Category.objects.create(
            user=self.other_user, name="Other"
        )
        task = Task.objects.create(
            user=self.other_user, category=other_category, title="Other Task"
        )
        response = self.client.patch(
            reverse("tasks:task-bulk-update"),
            [{"id": task.id, "is_completed": True}],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_bulk_delete_tasks(self):
        task1 = Task.objects.create(
            user=self.user, category=self.category, title="Task 1"
        )
        task2 = Task.objects.create(
            user=self.user, category=self.category, title="Task 2"
        )
        response = self.client.delete(
            reverse("tasks:task-bulk-delete"),
            {"ids": [task1.id, task2.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Task.objects.count(), 0)

    def test_bulk_delete_validates_ownership(self):
        other_category = Category.objects.create(
            user=self.other_user, name="Other"
        )
        task = Task.objects.create(
            user=self.other_user, category=other_category, title="Other Task"
        )
        response = self.client.delete(
            reverse("tasks:task-bulk-delete"),
            {"ids": [task.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Task.objects.count(), 1)

    def test_bulk_update_does_not_change_user(self):
        task = Task.objects.create(
            user=self.user, category=self.category, title="Task 1"
        )
        response = self.client.patch(
            reverse("tasks:task-bulk-update"),
            [{"id": task.id, "user": self.other_user.id}],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.user, self.user)

    def test_bulk_operations_require_authentication(self):
        self.client.logout()
        response = self.client.post(
            reverse("tasks:task-bulk-create"), [], format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
