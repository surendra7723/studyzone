from django.contrib import admin
from .models import PomodoroSession, TaskSession, Goal


@admin.register(PomodoroSession)
class PomodoroSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "session_type",
        "start_time",
        "end_time",
        "is_completed",
        "active_minutes",
        "break_minutes",
    )
    list_filter = ("session_type", "is_completed", "user")
    search_fields = ("user__username",)


@admin.register(TaskSession)
class TaskSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "pomodoro_session", "duration_minutes")
    search_fields = ("task__title", "pomodoro_session__id")


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "target_date", "is_completed")
    list_filter = ("is_completed", "user")
    search_fields = ("title",)
