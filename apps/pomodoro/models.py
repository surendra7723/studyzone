from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from core.models.base import TimeStampedModel

# Use string reference for Task to avoid import-time circularities that
# can cause makemigrations to split model creation into multiple migrations.


class PomodoroSessionQuerySet(models.QuerySet):
    def completed(self):
        return self.filter(is_completed=True)

    def for_user(self, user):
        return self.filter(user=user)


class PomodoroSessionManager(models.Manager.from_queryset(PomodoroSessionQuerySet)):
    def get_user_summary(self, user):
        """Returns overall stats for a user"""
        return (
            self.for_user(user)
            .completed()
            .aggregate(
                total_active=Sum("active_minutes"),
                total_breaks=Sum("break_minutes"),
                session_count=Count("id"),
            )
        )
    def _get_truncated_summary(self, user, trunc_func):
        """Generic helper for truncated summaries"""
        return (
            self.for_user(user)
            .completed()
            .annotate(period=trunc_func("start_time"))
            .values("period")
            .annotate(
                total_active=Sum("active_minutes"),
                total_breaks=Sum("break_minutes"),
                session_count=Count("id"),
            )
            .order_by("-period")
        )

    def get_daily_summaries(self, user):
        return self._get_truncated_summary(user, TruncDay)

    def get_weekly_summaries(self, user):
        return self._get_truncated_summary(user, TruncWeek)

    def get_monthly_summaries(self, user):
        return self._get_truncated_summary(user, TruncMonth)

    def get_yearly_summaries(self, user):
        return self._get_truncated_summary(user, TruncYear)


from core.mixins import OwnedModel


class PomodoroSession(OwnedModel, TimeStampedModel):
    class SessionType(models.TextChoices):
        FOCUS = "focus", "Focus"
        SHORT_BREAK = "short_break", "Short Break"
        LONG_BREAK = "long_break", "Long Break"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pomodoro_sessions",
    )
    session_type = models.CharField(
        max_length=20,
        choices=SessionType.choices,
        default=SessionType.FOCUS,
        db_index=True,
    )
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    active_minutes = models.PositiveIntegerField(default=0)
    break_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["user", "is_completed", "start_time"]),
            models.Index(fields=["user", "session_type"]),
        ]

    objects = PomodoroSessionManager()

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValidationError(
                {"end_time": "End time cannot be earlier than start time."}
            )
        if self.is_completed and not self.end_time:
            raise ValidationError(
                {"end_time": "Completed sessions must have an end time."}
            )

    def __str__(self):
        return f"{self.get_session_type_display()} {self.id} — {self.user.username}"


class TaskSession(TimeStampedModel):
    task = models.ForeignKey(
        "tasks.Task", on_delete=models.CASCADE, related_name="task_sessions"
    )
    pomodoro_session = models.ForeignKey(
        PomodoroSession, on_delete=models.CASCADE, related_name="task_sessions"
    )
    duration_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.task_id and self.pomodoro_session_id:
            task_user_id = getattr(self.task, "user_id", None)
            session_user_id = getattr(self.pomodoro_session, "user_id", None)
            if task_user_id and session_user_id and task_user_id != session_user_id:
                raise ValidationError(
                    {"task": "Task must belong to the same user as the session."}
                )

    def __str__(self):
        return f"TaskSession {self.id} — Task {self.task.title}"


class Goal(OwnedModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    target_date = models.DateField()
    is_completed = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["target_date", "title"]
        indexes = [
            models.Index(fields=["user", "target_date"]),
            models.Index(fields=["user", "is_completed"]),
        ]

    def __str__(self):
        return self.title
