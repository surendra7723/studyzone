"""
Django Admin Configuration for Leaderboard Models.
"""

from django.contrib import admin
from apps.leaderboard.models import (
    UserStreak,
    DailyActivityLog,
    LeaderboardEntry,
    LeaderboardSnapshot,
    StreakMilestone,
    UserMilestone,
    StreakFreeze,
)


@admin.register(UserStreak)
class UserStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_streak', 'longest_streak', 'last_activity_date', 'is_frozen']
    list_filter = ['is_frozen', 'user_timezone']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-current_streak']


@admin.register(DailyActivityLog)
class DailyActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_date', 'pomodoro_count', 'tasks_completed', 'is_active']
    list_filter = ['activity_date']
    search_fields = ['user__username']
    date_hierarchy = 'activity_date'


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'leaderboard_type', 'rank', 'total_score', 'period_start']
    list_filter = ['leaderboard_type']
    search_fields = ['user__username']
    ordering = ['leaderboard_type', 'rank']


@admin.register(LeaderboardSnapshot)
class LeaderboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ['snapshot_date', 'leaderboard_type', 'total_participants', 'average_streak']
    list_filter = ['leaderboard_type', 'snapshot_date']
    readonly_fields = ['top_entries']


@admin.register(StreakMilestone)
class StreakMilestoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'required_streak', 'bonus_points', 'badge_color', 'is_active']
    list_filter = ['is_active', 'badge_color']
    ordering = ['required_streak']


@admin.register(UserMilestone)
class UserMilestoneAdmin(admin.ModelAdmin):
    list_display = ['user', 'milestone', 'streak_at_achievement', 'achieved_at']
    list_filter = ['milestone', 'achieved_at']
    search_fields = ['user__username']
    date_hierarchy = 'achieved_at'


@admin.register(StreakFreeze)
class StreakFreezeAdmin(admin.ModelAdmin):
    list_display = ['user', 'used_for_date', 'created_at']
    list_filter = ['used_for_date']
    search_fields = ['user__username']
