from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.pomodoro.models import PomodoroSession


@shared_task(name="apps.pomodoro.cleanup_orphan_pomodoro_sessions")
def cleanup_orphan_pomodoro_sessions(retention_hours=None):
    """Delete Pomodoro sessions that never got a linked task session."""
    if retention_hours is None:
        retention_hours = getattr(
            settings, "POMODORO_SESSION_ORPHAN_TTL_HOURS", 24
        )

    cutoff = timezone.now() - timedelta(hours=retention_hours)
    queryset = PomodoroSession.objects.filter(
        task_sessions__isnull=True,
        created_at__lt=cutoff,
    )
    deleted_count, _ = queryset.delete()
    return deleted_count
