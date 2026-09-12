from datetime import timedelta
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "cleanup-orphan-pomodoro-sessions": {
        "task": "apps.pomodoro.cleanup_orphan_pomodoro_sessions",
        "schedule": timedelta(hours=1),
    },
    "cleanup-stale-presence": {
        "task": "apps.social.cleanup_stale_presence",
        "schedule": timedelta(minutes=2),
    },
    # Leaderboard tasks
    "daily-streak-reset": {
        "task": "apps.leaderboard.tasks.daily_streak_reset",
        "schedule": crontab(hour=0, minute=5),  # Run at 00:05 UTC
    },
    "calculate-global-leaderboard": {
        "task": "apps.leaderboard.tasks.calculate_leaderboard",
        "schedule": crontab(hour="*/1"),  # Run hourly
        "args": ("global",),
    },
    "calculate-weekly-leaderboard": {
        "task": "apps.leaderboard.tasks.calculate_leaderboard",
        "schedule": crontab(hour=1, minute=0),  # Run daily at 01:00 UTC
        "args": ("weekly",),
    },
    "calculate-monthly-leaderboard": {
        "task": "apps.leaderboard.tasks.calculate_leaderboard",
        "schedule": crontab(hour=2, minute=0),  # Run daily at 02:00 UTC
        "args": ("monthly",),
    },
    "sync-all-leaderboards": {
        "task": "apps.leaderboard.tasks.sync_all_leaderboards",
        "schedule": crontab(hour=3, minute=0),  # Run daily at 03:00 UTC
    },
    "cleanup-old-snapshots": {
        "task": "apps.leaderboard.tasks.cleanup_old_snapshots",
        "schedule": crontab(hour=4, minute=0, day_of_week=1),  # Weekly on Monday
        "args": (90,),  # Keep 90 days
    },
}

