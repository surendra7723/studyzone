from rest_framework import serializers
from .models import PomodoroSession, TaskSession, Goal


class PomodoroSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PomodoroSession
        fields = (
            "id",
            "user",
            "session_type",
            "start_time",
            "end_time",
            "is_completed",
            "active_minutes",
            "break_minutes",
        )
        read_only_fields = ("id", "user", "start_time")


class TaskSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskSession
        fields = ("id", "task", "pomodoro_session", "duration_minutes")


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ("id", "user", "title", "description", "target_date", "is_completed")
