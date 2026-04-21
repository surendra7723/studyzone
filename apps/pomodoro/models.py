from django.db import models
from core.models.base import TimeStampedModel
from apps.tasks.models.tasks import Task 
from django.conf import settings
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear

class PomodoroSessionManager(models.Manager):
    def get_user_summary(self, user):
        """Returns overall stats for a user"""
        return self.filter(user=user, is_completed=True).aggregate(
            total_active=Sum('active_minutes'),
            total_breaks=Sum('break_minutes'),
            session_count=Count('id')
        )

    def _get_truncated_summary(self, user, trunc_func):
        """Generic helper for truncated summaries"""
        return self.filter(user=user, is_completed=True) \
            .annotate(period=trunc_func('start_time')) \
            .values('period') \
            .annotate(
                total_active=Sum('active_minutes'),
                total_breaks=Sum('break_minutes'),
                session_count=Count('id')
            ) \
            .order_by('-period')

    def get_daily_summaries(self, user):
        return self._get_truncated_summary(user, TruncDay)

    def get_weekly_summaries(self, user):
        return self._get_truncated_summary(user, TruncWeek)

    def get_monthly_summaries(self, user):
        return self._get_truncated_summary(user, TruncMonth)

    def get_yearly_summaries(self, user):
        return self._get_truncated_summary(user, TruncYear)

class PomodoroSession(TimeStampedModel):
    class SessionType(models.TextChoices):
        FOCUS = 'focus', 'Focus'
        SHORT_BREAK = 'short_break', 'Short Break'
        LONG_BREAK = 'long_break', 'Long Break'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pomodoro_sessions')
    session_type = models.CharField(max_length=20, choices=SessionType.choices, default=SessionType.FOCUS)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    active_minutes = models.IntegerField(default=0)
    break_minutes = models.IntegerField(default=0)
    
    objects = PomodoroSessionManager()
    
    def __str__(self):
        return f"{self.get_session_type_display()} Session {self.id} for {self.user.username}"


class TaskSession(TimeStampedModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='task_sessions')
    pomodoro_session = models.ForeignKey(PomodoroSession, on_delete=models.CASCADE, related_name='task_sessions')
    duration_minutes = models.IntegerField(default=0)
    
    def __str__(self):
        return f"TaskSession {self.id} for Task {self.task.title}"


class Goal(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    target_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    