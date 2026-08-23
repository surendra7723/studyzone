
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework import status

from apps.notifications.models import Notification
from apps.user.serializers import UserSerializer
from apps.user.models import UserProfile
from apps.social.models import Friendship, UserPresenceState
from apps.tasks.models.tasks import Category, Task
from apps.pomodoro.models import PomodoroSession, Goal

from core.mixins import OwnedModel
from core.permissions import IsAuthenticatedAndActive, IsFriendOrSelf, IsNotDeleted, IsOwner, IsOwnerOrReadOnly
from core.serializers import FieldRestrictedSerializer


User = get_user_model()


class IsNotDeletedTests(TestCase):
    def test_rejects_deleted_user(self):
        user = User.objects.create_user(username="deleted", password="pass")
        user.is_deleted = True
        user.save()

        request = APIRequestFactory().get("/")
        request.user = user
        perm = IsNotDeleted()
        self.assertFalse(perm.has_permission(request, None))

    def test_allows_active_user(self):
        user = User.objects.create_user(username="active", password="pass")
        request = APIRequestFactory().get("/")
        request.user = user
        perm = IsNotDeleted()
        self.assertTrue(perm.has_permission(request, None))


class IsAuthenticatedAndActiveTests(TestCase):
    def test_rejects_anonymous(self):
        request = APIRequestFactory().get("/")
        request.user = None
        perm = IsAuthenticatedAndActive()
        self.assertFalse(perm.has_permission(request, None))

    def test_rejects_deleted(self):
        user = User.objects.create_user(username="del", password="pass")
        user.is_deleted = True
        user.save()
        request = APIRequestFactory().get("/")
        request.user = user
        perm = IsAuthenticatedAndActive()
        self.assertFalse(perm.has_permission(request, None))

    def test_allows_active(self):
        user = User.objects.create_user(username="active", password="pass")
        request = APIRequestFactory().get("/")
        request.user = user
        perm = IsAuthenticatedAndActive()
        self.assertTrue(perm.has_permission(request, None))


class IsOwnerTests(TestCase):
    def test_allows_owner(self):
        user = User.objects.create_user(username="owner", password="pass")
        other = User.objects.create_user(username="other", password="pass")
        task = Task.objects.create(user=user, title="T1")

        request = APIRequestFactory().get("/")
        request.user = user
        perm = IsOwner()
        self.assertTrue(perm.has_object_permission(request, None, task))

    def test_denies_non_owner(self):
        user = User.objects.create_user(username="owner", password="pass")
        other = User.objects.create_user(username="other", password="pass")
        task = Task.objects.create(user=user, title="T1")

        request = APIRequestFactory().get("/")
        request.user = other
        perm = IsOwner()
        self.assertFalse(perm.has_object_permission(request, None, task))

    def test_notification_recipient(self):
        user = User.objects.create_user(username="owner", password="pass")
        other = User.objects.create_user(username="other", password="pass")
        notif = Notification.objects.create(recipient=user, verb="test")

        request = APIRequestFactory().get("/")
        request.user = other
        perm = IsOwner()
        self.assertFalse(perm.has_object_permission(request, None, notif))

        request.user = user
        self.assertTrue(perm.has_object_permission(request, None, notif))


class IsOwnerOrReadOnlyTests(TestCase):
    def test_safe_methods_allowed(self):
        user = User.objects.create_user(username="owner", password="pass")
        other = User.objects.create_user(username="other", password="pass")
        task = Task.objects.create(user=user, title="T1")

        request = APIRequestFactory().get("/")
        request.user = other
        perm = IsOwnerOrReadOnly()
        self.assertTrue(perm.has_object_permission(request, None, task))

    def test_write_denied_for_non_owner(self):
        user = User.objects.create_user(username="owner", password="pass")
        other = User.objects.create_user(username="other", password="pass")
        task = Task.objects.create(user=user, title="T1")

        request = APIRequestFactory().patch("/")
        request.user = other
        perm = IsOwnerOrReadOnly()
        self.assertFalse(perm.has_object_permission(request, None, task))

    def test_write_allowed_for_owner(self):
        user = User.objects.create_user(username="owner", password="pass")
        task = Task.objects.create(user=user, title="T1")

        request = APIRequestFactory().patch("/")
        request.user = user
        perm = IsOwnerOrReadOnly()
        self.assertTrue(perm.has_object_permission(request, None, task))


class IsFriendOrSelfCachingTests(TestCase):
    def test_self_access_allowed(self):
        user = User.objects.create_user(username="u1", password="pass")
        state = UserPresenceState.objects.create(user=user, is_online=True)

        request = APIRequestFactory().get("/")
        request.user = user
        perm = IsFriendOrSelf()
        self.assertTrue(perm.has_object_permission(request, None, state))

    def test_friend_access_cached(self):
        u1 = User.objects.create_user(username="u1", password="pass")
        u2 = User.objects.create_user(username="u2", password="pass")
        Friendship.objects.create(user_low=u1, user_high=u2)
        state = UserPresenceState.objects.create(user=u2, is_online=True)

        request = APIRequestFactory().get("/")
        request.user = u1
        perm = IsFriendOrSelf()
        self.assertTrue(perm.has_object_permission(request, None, state))
        self.assertIn((min(u1.id, u2.id), max(u1.id, u2.id)), request._friend_cache)

    def test_stranger_denied(self):
        u1 = User.objects.create_user(username="u1", password="pass")
        u2 = User.objects.create_user(username="u2", password="pass")
        state = UserPresenceState.objects.create(user=u2, is_online=True)

        request = APIRequestFactory().get("/")
        request.user = u1
        perm = IsFriendOrSelf()
        self.assertFalse(perm.has_object_permission(request, None, state))


class BulkOperationsPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="StrongPass123!")
        self.other_user = User.objects.create_user(username="bob", password="StrongPass123!")
        self.category = Category.objects.create(user=self.user, name="Work")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_bulk_update_enforces_permissions(self):
        task = Task.objects.create(
            user=self.other_user, category=self.category, title="Other Task"
        )
        response = self.client.patch(
            reverse("tasks:task-bulk-update"),
            [{"id": task.id, "is_completed": True}],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
        task.refresh_from_db()
        self.assertFalse(task.is_completed)

    def test_bulk_delete_enforces_permissions(self):
        task = Task.objects.create(
            user=self.other_user, category=self.category, title="Other Task"
        )
        response = self.client.delete(
            reverse("tasks:task-bulk-delete"),
            {"ids": [task.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Task.objects.count(), 1)


class FieldRestrictedSerializerTests(TestCase):
    def test_self_read_shows_restricted_fields(self):
        user = User.objects.create_user(username="alice", password="pass")
        request = APIRequestFactory().get("/")
        request.user = user
        serializer = UserSerializer(user, context={"request": request})
        data = serializer.data
        self.assertIn("is_staff", data)
        self.assertIn("is_email_verified", data)
        self.assertIn("is_phone_verified", data)
        self.assertIn("phone_number", data)

    def test_other_read_hides_restricted_fields(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        request = APIRequestFactory().get("/")
        request.user = bob
        serializer = UserSerializer(alice, context={"request": request})
        data = serializer.data
        self.assertNotIn("is_staff", data)
        self.assertNotIn("is_email_verified", data)
        self.assertNotIn("is_phone_verified", data)
        self.assertNotIn("phone_number", data)

    def test_admin_read_shows_restricted_fields(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass", is_staff=True)
        request = APIRequestFactory().get("/")
        request.user = bob
        serializer = UserSerializer(alice, context={"request": request})
        data = serializer.data
        self.assertIn("is_staff", data)
        self.assertIn("is_email_verified", data)
