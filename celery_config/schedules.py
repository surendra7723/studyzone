from datetime import timedelta

CELERY_BEAT_SCHEDULE = {
    "cleanup-orphan-pomodoro-sessions": {
        "task": "apps.pomodoro.cleanup_orphan_pomodoro_sessions",
        "schedule": timedelta(hours=1),
    },
    "cleanup-stale-presence": {
        "task": "apps.social.cleanup_stale_presence",
        "schedule": timedelta(minutes=2),
    },
}
