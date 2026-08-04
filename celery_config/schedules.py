from datetime import timedelta

CELERY_BEAT_SCHEDULE = {
    "cleanup-orphan-pomodoro-sessions": {
        "task": "apps.pomodoro.cleanup_orphan_pomodoro_sessions",
        "schedule": timedelta(hours=1),
    },
}
