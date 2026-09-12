"""
Serializers for Leaderboard app.
"""

from rest_framework import serializers

from apps.leaderboard.models import (
    UserStreak,
    DailyActivityLog,
    LeaderboardEntry,
    StreakMilestone,
    StreakFreeze,
    LeaderboardSnapshot,
)


class UserStreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStreak
        fields = [
            "id",
            "user",
            "current_streak",
            "longest_streak",
            "last_activity_date",
            "streak_start_date",
            "user_timezone",
            "is_frozen",
            "frozen_until",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DailyActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyActivityLog
        fields = [
            "id",
            "user",
            "activity_date",
            "pomodoro_count",
            "tasks_completed",
            "goals_achieved",
            "total_study_minutes",
            "activity_types",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaderboardEntrySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = LeaderboardEntry
        fields = [
            "id",
            "user",
            "username",
            "leaderboard_type",
            "rank",
            "streak_score",
            "activity_score",
            "consistency_score",
            "total_score",
            "period_start",
            "period_end",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StreakMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreakMilestone
        fields = [
            "id",
            "name",
            "description",
            "required_streak",
            "bonus_points",
            "badge_icon",
            "badge_color",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StreakFreezeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreakFreeze
        fields = [
            "id",
            "user",
            "used_for_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaderboardSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaderboardSnapshot
        fields = [
            "id",
            "snapshot_date",
            "leaderboard_type",
            "top_entries",
            "total_participants",
            "average_streak",
            "median_streak",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
