"""
Streak-based Leaderboard Models

This module contains all database models for tracking user streaks,
daily activities, and leaderboard rankings.

Key Features:
- User streak tracking with timezone support
- Daily activity logs for granular tracking
- Historical leaderboard snapshots
- Achievement badges for milestones
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Window
from django.db.models.functions import Rank
from django.utils import timezone
from core.models.base import TimeStampedModel


class UserStreak(TimeStampedModel):
    """
    Tracks the current streak status for each user.
    
    A streak is maintained when a user completes at least one activity
    (e.g., pomodoro session, task completion) within a 24-hour window
    based on their configured timezone.
    
    Concurrency Handling:
    - Uses select_for_update() in tasks to prevent race conditions
    - last_activity_date is used for streak calculation logic
    - timezone field ensures accurate day boundaries per user
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="streak"
    )
    
    # Current streak tracking
    current_streak = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Current consecutive days of activity"
    )
    longest_streak = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="All-time longest streak"
    )
    
    # Timestamps for streak calculation
    last_activity_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Date of last activity in user's timezone"
    )
    last_activity_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Precise timestamp of last activity for debugging"
    )
    streak_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when current streak began"
    )
    
    # User's timezone for accurate day boundary calculation
    user_timezone = models.CharField(
        max_length=50,
        default="UTC",
        help_text="User's timezone for streak calculation (e.g., 'America/New_York')"
    )
    
    # Frozen flag for special cases (vacation mode, etc.)
    is_frozen = models.BooleanField(
        default=False,
        help_text="If True, streak won't be broken due to inactivity"
    )
    frozen_until = models.DateField(
        null=True,
        blank=True,
        help_text="Date until which streak is frozen"
    )
    
    class Meta:
        ordering = ["-current_streak", "-longest_streak"]
        indexes = [
            models.Index(fields=["current_streak"]),
            models.Index(fields=["longest_streak"]),
            models.Index(fields=["last_activity_date"]),
            models.Index(fields=["user", "last_activity_date"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Current: {self.current_streak} days"
    
    def update_longest_streak(self):
        """Update longest_streak if current streak exceeds it."""
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
            self.save(update_fields=["longest_streak"])
    

    @property
    def is_streak_frozen(self):
        """Check if streak is currently frozen."""
        if not self.is_frozen:
            return False
        if self.frozen_until and self.frozen_until < timezone.now().date():
            self.is_frozen = False
            self.save(update_fields=["is_frozen"])
            return False
        return True


class DailyActivityLog(TimeStampedModel):
    """
    Records user activity for each day.
    
    This model serves as the source of truth for whether a user was
    active on a given day (in their timezone). It supports multiple
    activity types and aggregates activity metrics.
    """
    
    class ActivityType(models.TextChoices):
        POMODORO = "pomodoro", "Pomodoro Session"
        TASK_COMPLETED = "task_completed", "Task Completed"
        GOAL_ACHIEVED = "goal_achieved", "Goal Achieved"
        STUDY_TIME = "study_time", "Study Time"
        MANUAL = "manual", "Manual Check-in"
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_activities"
    )
    
    activity_date = models.DateField(
        db_index=True,
        help_text="Date of activity in user's timezone"
    )
    
    pomodoro_count = models.PositiveIntegerField(default=0)
    tasks_completed = models.PositiveIntegerField(default=0)
    goals_achieved = models.PositiveIntegerField(default=0)
    total_study_minutes = models.PositiveIntegerField(default=0)
    
    activity_types = models.JSONField(
        default=list,
        help_text="List of activity types logged for this day"
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ["-activity_date"]
        unique_together = ["user", "activity_date"]
        indexes = [
            models.Index(fields=["user", "activity_date"]),
            models.Index(fields=["activity_date"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_date}"
    
    def add_activity(self, activity_type: str, **kwargs):
        """Add an activity to this log."""
        if activity_type == self.ActivityType.POMODORO:
            self.pomodoro_count += 1
            if "duration_minutes" in kwargs:
                self.total_study_minutes += kwargs["duration_minutes"]
        elif activity_type == self.ActivityType.TASK_COMPLETED:
            self.tasks_completed += 1
        elif activity_type == self.ActivityType.GOAL_ACHIEVED:
            self.goals_achieved += 1
        elif activity_type == self.ActivityType.STUDY_TIME:
            if "duration_minutes" in kwargs:
                self.total_study_minutes += kwargs["duration_minutes"]
        
        if activity_type not in self.activity_types:
            self.activity_types.append(activity_type)
        
        if kwargs:
            self.metadata.update(kwargs)
        
        self.save()
    

    @property
    def is_active(self) -> bool:
        """Check if user was active on this day."""
        return bool(
            self.pomodoro_count > 0 or
            self.tasks_completed > 0 or
            self.goals_achieved > 0 or
            self.total_study_minutes > 0
        )


class LeaderboardEntry(TimeStampedModel):
    """
    Cached leaderboard entry for efficient retrieval.
    Updated periodically by Celery tasks.
    """
    
    class LeaderboardType(models.TextChoices):
        GLOBAL = "global", "Global Leaderboard"
        WEEKLY = "weekly", "Weekly Leaderboard"
        MONTHLY = "monthly", "Monthly Leaderboard"
        ALL_TIME = "all_time", "All-Time Leaderboard"
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leaderboard_entries"
    )
    
    leaderboard_type = models.CharField(
        max_length=20,
        choices=LeaderboardType.choices,
        db_index=True
    )
    
    rank = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Current rank in the leaderboard"
    )
    
    streak_score = models.PositiveIntegerField(default=0)
    activity_score = models.PositiveIntegerField(default=0)
    consistency_score = models.PositiveIntegerField(default=0)
    total_score = models.PositiveIntegerField(default=0, db_index=True)
    
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ["leaderboard_type", "rank"]
        unique_together = ["user", "leaderboard_type", "period_start"]
        indexes = [
            models.Index(fields=["leaderboard_type", "rank"]),
            models.Index(fields=["leaderboard_type", "total_score"]),
        ]
    
    def __str__(self):
        return f"#{self.rank} {self.user.username} ({self.get_leaderboard_type_display()})"
    
    def calculate_total_score(self):
        """Calculate and update total score."""
        self.total_score = self.streak_score + self.activity_score + self.consistency_score
        return self.total_score


class LeaderboardSnapshot(TimeStampedModel):
    """Historical snapshot of the leaderboard."""
    
    snapshot_date = models.DateField(db_index=True)
    leaderboard_type = models.CharField(
        max_length=20,
        choices=LeaderboardEntry.LeaderboardType.choices,
        db_index=True
    )
    
    top_entries = models.JSONField(default=list)
    total_participants = models.PositiveIntegerField(default=0)
    average_streak = models.FloatField(default=0.0)
    median_streak = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ["-snapshot_date"]
        unique_together = ["snapshot_date", "leaderboard_type"]
    
    def __str__(self):
        return f"Snapshot {self.snapshot_date} - {self.get_leaderboard_type_display()}"


class StreakMilestone(TimeStampedModel):
    """Defines streak milestones for achievements/badges."""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    required_streak = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    bonus_points = models.PositiveIntegerField(default=0)
    badge_icon = models.CharField(max_length=100, blank=True)
    badge_color = models.CharField(max_length=20, default="gold")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["required_streak"]
    
    def __str__(self):
        return f"{self.name} ({self.required_streak} days)"


class UserMilestone(TimeStampedModel):
    """Records when a user achieved a milestone."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="milestones"
    )
    milestone = models.ForeignKey(
        StreakMilestone,
        on_delete=models.CASCADE,
        related_name="achievers"
    )
    achieved_at = models.DateTimeField(auto_now_add=True)
    streak_at_achievement = models.PositiveIntegerField()
    
    class Meta:
        ordering = ["-achieved_at"]
        unique_together = ["user", "milestone"]
    
    def __str__(self):
        return f"{self.user.username} achieved {self.milestone.name}"


class StreakFreeze(TimeStampedModel):
    """Tracks streak freeze usage."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="streak_freezes"
    )
    used_for_date = models.DateField()
    
    FREEZE_LIMIT_PER_MONTH = 3
    
    class Meta:
        ordering = ["-used_for_date"]
        indexes = [
            models.Index(fields=["user", "used_for_date"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} freeze for {self.used_for_date}"
    
    @classmethod
    def get_remaining_freezes(cls, user) -> int:
        """Get number of remaining freezes for current month."""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        used_count = cls.objects.filter(
            user=user,
            used_for_date__gte=month_start
        ).count()
        
        return max(0, cls.FREEZE_LIMIT_PER_MONTH - used_count)

