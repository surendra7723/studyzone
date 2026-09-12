"""Tests for Leaderboard views."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.leaderboard.models import UserStreak, LeaderboardEntry

User = get_user_model()


class LeaderboardApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_get_leaderboard(self):
        url = reverse('leaderboard:get-leaderboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('entries', response.data)

    def test_get_user_rank(self):
        url = reverse('leaderboard:get-user-rank')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_nearby_users(self):
        url = reverse('leaderboard:get-nearby-users')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_streak_status(self):
        url = reverse('leaderboard:get-streak-status')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_streak', response.data)

    def test_use_streak_freeze(self):
        url = reverse('leaderboard:use-streak-freeze')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_get_streak_history(self):
        url = reverse('leaderboard:get-streak-history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_milestones(self):
        url = reverse('leaderboard:get-milestones')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('milestones', response.data)

    def test_update_user_timezone(self):
        url = reverse('leaderboard:update-user-timezone')
        response = self.client.put(url, {'timezone': 'America/New_York'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['timezone'], 'America/New_York')


class LeaderboardUnauthenticatedTests(TestCase):
    def test_get_leaderboard_requires_auth(self):
        url = reverse('leaderboard:get-leaderboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
