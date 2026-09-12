"""Tests for Leaderboard Celery tasks."""

from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.leaderboard.models import (
    UserStreak,
    DailyActivityLog,
    StreakFreeze,
    LeaderboardEntry,
    StreakMilestone,
    UserMilestone,
    LeaderboardSnapshot,
)
from apps.leaderboard.tasks import (
    update_user_streak,
    daily_streak_reset,
    calculate_leaderboard,
    update_redis_leaderboard,
    check_milestones,
    create_leaderboard_snapshot,
    sync_all_leaderboards,
    cleanup_old_snapshots,
)

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class TimezoneServiceTests(TestCase):
    def test_get_user_local_date(self):
        from apps.leaderboard.tasks import TimezoneService
        user = User.objects.create_user(username="tzuser", password="StrongPass123!")
        streak = UserStreak.objects.get(user=user)
        local_date = TimezoneService.get_user_local_date(streak)
        self.assertEqual(local_date, timezone.now().date())

    def test_get_previous_day_in_timezone(self):
        from apps.leaderboard.tasks import TimezoneService
        user_tz = "America/New_York"
        prev_day = TimezoneService.get_previous_day_in_timezone(user_tz)
        self.assertEqual(prev_day, timezone.now().date() - timedelta(days=1))


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class UpdateUserStreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")
        # Signal creates a UserStreak; get it instead of creating another
        self.streak = UserStreak.objects.get(user=self.user)
        # Patch Celery task delays to avoid broker connection during tests
        self.redis_patcher = patch("apps.leaderboard.tasks.update_redis_leaderboard.delay")
        self.milestone_patcher = patch("apps.leaderboard.tasks.check_milestones.delay")
        self.mock_redis = self.redis_patcher.start()
        self.mock_milestone = self.milestone_patcher.start()

    def tearDown(self):
        self.redis_patcher.stop()
        self.milestone_patcher.stop()

    def test_update_streak_first_activity(self):
        # Ensure no previous activity
        self.streak.current_streak = 0
        self.streak.last_activity_date = None
        self.streak.save()
        
        update_user_streak(self.user.id, DailyActivityLog.ActivityType.POMODORO)
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 1)
        self.assertEqual(self.streak.streak_start_date, timezone.now().date())
        self.mock_milestone.assert_called_once()
        self.mock_redis.assert_called_once()

    def test_update_streak_same_day(self):
        self.streak.current_streak = 1
        self.streak.last_activity_date = timezone.now().date()
        self.streak.save()
        
        update_user_streak(self.user.id, DailyActivityLog.ActivityType.TASK_COMPLETED)
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 1)

    def test_update_streak_consecutive_day(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        self.streak.current_streak = 1
        self.streak.last_activity_date = yesterday
        self.streak.save()
        
        update_user_streak(self.user.id, DailyActivityLog.ActivityType.POMODORO)
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 2)

    def test_update_streak_break_without_freeze(self):
        two_days_ago = timezone.now().date() - timedelta(days=2)
        self.streak.current_streak = 3
        self.streak.last_activity_date = two_days_ago
        self.streak.save()
        
        update_user_streak(self.user.id, DailyActivityLog.ActivityType.POMODORO)
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 1)


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class DailyStreakResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")
        self.streak = UserStreak.objects.get(user=self.user)

    def test_reset_inactive_streak(self):
        three_days_ago = timezone.now().date() - timedelta(days=3)
        self.streak.current_streak = 5
        self.streak.last_activity_date = three_days_ago
        self.streak.save()
        
        daily_streak_reset()
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 0)
        self.assertIsNone(self.streak.streak_start_date)

    def test_use_freeze_for_missed_day(self):
        two_days_ago = timezone.now().date() - timedelta(days=2)
        self.streak.current_streak = 5
        self.streak.last_activity_date = two_days_ago
        self.streak.save()
        
        daily_streak_reset()
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 5)
        self.assertTrue(StreakFreeze.objects.filter(user=self.user).exists())


class CalculateLeaderboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")
        UserStreak.objects.update_or_create(user=self.user, defaults={"current_streak": 5})

    @patch("apps.leaderboard.tasks.create_leaderboard_snapshot.delay")
    def test_calculate_global_leaderboard(self, mock_snapshot):
        result = calculate_leaderboard("global")
        self.assertIn("entries_count", result)
        self.assertEqual(LeaderboardEntry.objects.filter(leaderboard_type="global").count(), 1)


class RedisLeaderboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")
        UserStreak.objects.update_or_create(user=self.user, defaults={"current_streak": 5})

    @patch("apps.leaderboard.tasks.get_redis_client")
    def test_update_redis_leaderboard(self, mock_redis_client):
        mock_client = MagicMock()
        mock_redis_client.return_value = mock_client
        update_redis_leaderboard(self.user.id)
        self.assertEqual(mock_client.zadd.call_count, 2)


class MilestoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPass123!")
        UserStreak.objects.update_or_create(user=self.user, defaults={"current_streak": 7})
        StreakMilestone.objects.create(name="Week Warrior", required_streak=7, bonus_points=100)

    @patch("apps.leaderboard.tasks.update_redis_leaderboard.delay")
    def test_check_milestones(self, mock_update_redis):
        check_milestones(self.user.id, 7)
        self.assertTrue(
            UserMilestone.objects.filter(user=self.user, milestone__required_streak=7).exists()
        )


class CleanupOldSnapshotsTests(TestCase):
    def test_cleanup_old_snapshots(self):
        old_date = timezone.now().date() - timedelta(days=100)
        LeaderboardSnapshot.objects.create(
            snapshot_date=old_date,
            leaderboard_type=LeaderboardEntry.LeaderboardType.GLOBAL,
            top_entries=[],
        )
        deleted = cleanup_old_snapshots(days_to_keep=90)
        self.assertEqual(deleted, 1)
