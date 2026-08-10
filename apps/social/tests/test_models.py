from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.social.models import Friendship

User = get_user_model()


class FriendshipModelTests(TestCase):
    def test_create_for_users_orders_pair(self):
        user_a = User.objects.create_user(username="alice", password="StrongPass123!")
        user_b = User.objects.create_user(username="bob", password="StrongPass123!")

        friendship = Friendship.create_for_users(user_b, user_a)

        self.assertEqual(friendship.user_low_id, min(user_a.id, user_b.id))
        self.assertEqual(friendship.user_high_id, max(user_a.id, user_b.id))
