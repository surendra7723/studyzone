from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.tasks.models.tasks import Category, Task

User = get_user_model()


class UserSoftDeleteApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", password="StrongPass123!"
        )
        self.other_user = User.objects.create_user(
            username="bob", password="StrongPass123!"
        )
        self.client.force_authenticate(user=self.user)

    def test_soft_deleted_user_excluded_from_list(self):
        self.user.is_deleted = True
        self.user.save()
        response = self.client.get(reverse("users-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_soft_deleted_user_cannot_login(self):
        self.user.is_deleted = True
        self.user.save()
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "alice", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_list_soft_deleted_users(self):
        admin = User.objects.create_user(
            username="admin", password="StrongPass123!", is_staff=True
        )
        self.user.is_deleted = True
        self.user.save()
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("admin-users-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_admin_can_restore_soft_deleted_user(self):
        admin = User.objects.create_user(
            username="admin", password="StrongPass123!", is_staff=True
        )
        self.user.is_deleted = True
        self.user.save()
        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse("admin-users-restore", args=[self.user.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_deleted)

    def test_soft_delete_does_not_break_foreign_keys(self):
        category = Category.objects.create(user=self.user, name="Work")
        Task.objects.create(
            user=self.user, category=category, title="Task"
        )
        self.user.is_deleted = True
        self.user.save()
        category.refresh_from_db()
        self.assertEqual(category.user, self.user)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Category.objects.count(), 1)

    def test_hard_delete_removes_user(self):
        admin = User.objects.create_user(
            username="admin", password="StrongPass123!", is_staff=True
        )
        self.user.is_deleted = True
        self.user.save()
        category = Category.objects.create(user=self.user, name="Work")
        Task.objects.create(
            user=self.user, category=category, title="Task"
        )
        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse("admin-users-restore", args=[self.user.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_deleted)
