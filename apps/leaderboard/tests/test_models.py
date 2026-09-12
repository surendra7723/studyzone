"""Tests for Leaderboard models."""

from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.leaderboard.models import (
    UserStreak,
    DailyActivityLog,
    StreakFreeze,
    StreakMilestone,
    UserMilestone,
    LeaderboardEntry,
    LeaderboardSnapshot,
)

User = get_user_model()


class UserStreakModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")
        # Signal creates a UserStreak; fetch it instead of creating another
        self.streak = UserStreak.objects.get(user=self.user)

    def test_streak_created_with_defaults(self):
        self.assertEqual(self.streak.current_streak, 0)
        self.assertEqual(self.streak.longest_streak, 0)
        self.assertEqual(self.streak.user_timezone, "UTC")

    def test_update_longest_streak(self):
        self.streak.current_streak = 5
        self.streak.save()
        self.streak.update_longest_streak()
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.longest_streak, 5)

    def test_is_streak_frozen_true(self):
        self.streak.is_frozen = True
        self.streak.frozen_until = timezone.now().date() + timedelta(days=1)
        self.streak.save()
        self.assertTrue(self.streak.is_streak_frozen)

    def test_is_streak_frozen_expired(self):
        self.streak.is_frozen = True
        self.streak.frozen_until = timezone.now().date() - timedelta(days=1)
        self.streak.save()
        self.assertFalse(self.streak.is_streak_frozen)
        self.streak.refresh_from_db()
        self.assertFalse(self.streak.is_frozen)


class DailyActivityLogModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")

    def test_add_pomodoro_activity(self):
        log = DailyActivityLog.objects.create(user=self.user, activity_date=timezone.now().date())
        log.add_activity(DailyActivityLog.ActivityType.POMODORO, duration_minutes=25)
        self.assertEqual(log.pomodoro_count, 1)
        self.assertEqual(log.total_study_minutes, 25)
        self.assertTrue(log.is_active)

    def test_is_active_true(self):
        log = DailyActivityLog.objects.create(
            user=self.user,
            activity_date=timezone.now().date(),
            pomodoro_count=1,
        )
        self.assertTrue(log.is_active)

    def test_is_active_false(self):
        log = DailyActivityLog.objects.create(user=self.user, activity_date=timezone.now().date())
        self.assertFalse(log.is_active)


class StreakFreezeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")

    def test_get_remaining_freezes(self):
        self.assertEqual(StreakFreeze.get_remaining_freezes(self.user), 3)

    def test_use_freeze(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        StreakFreeze.objects.create(user=self.user, used_for_date=yesterday)
        self.assertEqual(StreakFreeze.get_remaining_freezes(self.user), 2)


class StreakMilestoneModelTests(TestCase):
    def test_create_milestone(self):
        milestone = StreakMilestone.objects.create(
            name="Week Warrior", required_streak=7, bonus_points=100
        )
        self.assertEqual(str(milestone), "Week Warrior (7 days)")


class LeaderboardEntryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")

    def test_calculate_total_score(self):
        entry = LeaderboardEntry.objects.create(
            user=self.user,
            leaderboard_type=LeaderboardEntry.LeaderboardType.GLOBAL,
            rank=1,
            streak_score=70,
            activity_score=50,
            consistency_score=10,
        )
        entry.calculate_total_score()
        self.assertEqual(entry.total_score, 130)


class LeaderboardSnapshotModelTests(TestCase):
    def test_create_snapshot(self):
        snapshot = LeaderboardSnapshot.objects.create(
            snapshot_date=timezone.now().date(),
            leaderboard_type=LeaderboardEntry.LeaderboardType.GLOBAL,
            top_entries=[],
            total_participants=10,
            average_streak=5.5,
            median_streak=3,
        )
        self.assertIn("Snapshot", str(snapshot))
