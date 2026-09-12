"""
Signals for automatic streak updates.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from apps.leaderboard.models import UserStreak, DailyActivityLog
from apps.leaderboard.services import LeaderboardService


User = get_user_model()


@receiver(post_save, sender=User)
def create_user_streak(sender, instance, created, **kwargs):
    """Create UserStreak when a new user is created."""
    if created:
        UserStreak.objects.get_or_create(
            user=instance,
            defaults={'user_timezone': 'UTC'}
        )
