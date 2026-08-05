from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.social.models import FriendRequest, Friendship, UserPresenceState

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class SocialFriendRequestApiTests(APITestCase):
    def setUp(self):
        self.sender = User.objects.create_user(username="alice", password="StrongPass123!")
        self.receiver = User.objects.create_user(username="bob", password="StrongPass123!")
        self.client.force_authenticate(user=self.sender)

    @patch("apps.social.views.broadcast_friend_request_event")
    def test_create_friend_request(self, mock_broadcast):
        response = self.client.post(
            reverse("social-friend-requests"),
            {"receiver_username": "bob"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FriendRequest.objects.count(), 1)
        self.assertEqual(FriendRequest.objects.first().sender, self.sender)
        mock_broadcast.assert_called_once()

    @patch("apps.social.services.broadcast_friend_request_event")
    def test_accept_friend_request(self, mock_broadcast):
        friend_request = FriendRequest.objects.create(sender=self.sender, receiver=self.receiver)
        self.client.force_authenticate(user=self.receiver)

        response = self.client.post(reverse("social-friend-request-accept", args=[friend_request.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Friendship.objects.count(), 1)
        self.assertEqual(FriendRequest.objects.get(pk=friend_request.pk).status, "accepted")
        mock_broadcast.assert_called()

    def test_reject_self_friend_request(self):
        response = self.client.post(
            reverse("social-friend-requests"),
            {"receiver_id": self.sender.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class SocialPresenceApiTests(APITestCase):
    def test_presence_snapshot_returns_friends(self):
        user = User.objects.create_user(username="alice", password="StrongPass123!")
        friend = User.objects.create_user(username="bob", password="StrongPass123!")
        Friendship.create_for_users(user, friend)
        UserPresenceState.objects.create(user=friend, is_online=True)
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("social-presence"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"]["username"], "bob")
        self.assertTrue(response.data[0]["is_online"])
