from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Notification

User = get_user_model()


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", password="StrongPass123!"
        )
        self.other_user = User.objects.create_user(
            username="bob", password="StrongPass123!"
        )
        self.actor = User.objects.create_user(
            username="charlie", password="StrongPass123!"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_notification(self):
        response = self.client.post(
            reverse("notifications:notification-list"),
            {
                "recipient": self.user.id,
                "actor": self.actor.id,
                "verb": "sent you a message",
                "content": "Hello",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Notification.objects.count(), 1)

    def test_list_notifications_filters_by_recipient(self):
        Notification.objects.create(
            recipient=self.other_user, actor=self.actor, verb="hello"
        )
        Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="hi"
        )
        response = self.client.get(reverse("notifications:notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_notifications_ordered_by_created(self):
        n1 = Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="first"
        )
        n2 = Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="second"
        )
        response = self.client.get(reverse("notifications:notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["id"], n2.id)
        self.assertEqual(response.data["results"][1]["id"], n1.id)

    def test_unread_notifications_filter(self):
        Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="unread", read=False
        )
        Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="read", read=True
        )
        response = self.client.get(
            reverse("notifications:notification-list"), {"read": False}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["verb"], "unread")

    def test_mark_notification_as_read(self):
        notification = Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="hello", read=False
        )
        response = self.client.post(
            reverse(
                "notifications:notification-mark-read", args=[notification.id]
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["read"])

    def test_mark_all_notifications_as_read(self):
        Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="first", read=False
        )
        Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="second", read=False
        )
        response = self.client.post(
            reverse("notifications:notification-mark-all-read")
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.user, read=False
            ).count(),
            0,
        )

    def test_delete_notification(self):
        notification = Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="hello"
        )
        response = self.client.delete(
            reverse(
                "notifications:notification-detail", args=[notification.id]
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        notification.refresh_from_db()
        self.assertTrue(notification.is_deleted)

    def test_cannot_read_other_users_notification(self):
        notification = Notification.objects.create(
            recipient=self.other_user, actor=self.actor, verb="hello"
        )
        response = self.client.get(
            reverse(
                "notifications:notification-detail", args=[notification.id]
            )
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notification_count_unread(self):
        Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="unread1", read=False
        )
        Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="unread2", read=False
        )
        Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="read", read=True
        )
        response = self.client.get(
            reverse("notifications:notification-unread-count")
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 2)

    def test_notification_soft_delete(self):
        notification = Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="hello"
        )
        response = self.client.delete(
            reverse(
                "notifications:notification-detail", args=[notification.id]
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        list_response = self.client.get(
            reverse("notifications:notification-list")
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data["results"]), 0)

    def test_bulk_mark_as_read(self):
        n1 = Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="first", read=False
        )
        n2 = Notification.objects.create(
            recipient=self.user, actor=self.actor, verb="second", read=False
        )
        response = self.client.post(
            reverse("notifications:notification-bulk-mark-read"),
            {"ids": [n1.id, n2.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        n1.refresh_from_db()
        n2.refresh_from_db()
        self.assertTrue(n1.read)
        self.assertTrue(n2.read)

    def test_notification_pagination(self):
        for i in range(25):
            Notification.objects.create(
                recipient=self.user, actor=self.actor, verb=f"Notify {i}"
            )
        response = self.client.get(reverse("notifications:notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 20)
