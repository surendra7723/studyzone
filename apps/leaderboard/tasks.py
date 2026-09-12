"""
Celery Tasks for Streak-Based Leaderboard System

This module contains all async tasks for:
- Daily streak updates and resets
- Leaderboard calculation and caching
- Milestone achievement processing
- Redis leaderboard synchronization
"""

import logging
from datetime import timedelta, date
from typing import List, Dict, Any

import redis
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import F, Window, Avg, Count
from django.db.models.functions import Rank
from django.utils import timezone
from zoneinfo import ZoneInfo

from apps.leaderboard.models import (
    UserStreak,
    DailyActivityLog,
    LeaderboardEntry,
    LeaderboardSnapshot,
    StreakMilestone,
    UserMilestone,
    StreakFreeze,
)

logger = logging.getLogger(__name__)


def get_redis_client():
    """Get Redis client for leaderboard operations."""
    redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
    return redis.from_url(redis_url)


class TimezoneService:
    """Handles timezone conversions for streak calculations."""
    
    @staticmethod
    def get_user_local_date(user_streak: UserStreak) -> 'date':
        """Get current date in user's timezone."""
        user_tz = ZoneInfo(user_streak.user_timezone)
        return timezone.now().astimezone(user_tz).date()
    
    @staticmethod
    def get_previous_day_in_timezone(timezone_str: str) -> 'date':
        """Get yesterday's date in the specified timezone."""
        user_tz = ZoneInfo(timezone_str)
        return (timezone.now().astimezone(user_tz) - timedelta(days=1)).date()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def update_user_streak(self, user_id: int, activity_type: str, **kwargs):
    """
    Update user streak after an activity.
    Uses select_for_update() to prevent race conditions.
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        with transaction.atomic():
            user = User.objects.select_for_update().get(id=user_id)
            
            user_streak, created = UserStreak.objects.select_for_update().get_or_create(
                user=user,
                defaults={'user_timezone': 'UTC'}
            )
            
            tz_service = TimezoneService()
            activity_date = tz_service.get_user_local_date(user_streak)
            
            activity_log, log_created = DailyActivityLog.objects.select_for_update().get_or_create(
                user=user,
                activity_date=activity_date,
                defaults={'activity_types': []}
            )
            
            activity_log.add_activity(activity_type, **kwargs)
            
            previous_activity_date = user_streak.last_activity_date
            
            if previous_activity_date is None:
                user_streak.current_streak = 1
                user_streak.streak_start_date = activity_date
            elif activity_date == previous_activity_date:
                pass  # Same day - no streak change
            elif activity_date == previous_activity_date + timedelta(days=1):
                user_streak.current_streak = F('current_streak') + 1
            elif activity_date > previous_activity_date + timedelta(days=1):
                # Streak broken - check for freeze
                if user_streak.is_streak_frozen or StreakFreeze.objects.filter(
                    user=user,
                    used_for_date=previous_activity_date + timedelta(days=1)
                ).exists():
                    user_streak.current_streak = F('current_streak') + 1
                else:
                    user_streak.current_streak = 1
                    user_streak.streak_start_date = activity_date
            
            user_streak.last_activity_date = activity_date
            user_streak.last_activity_timestamp = timezone.now()
            user_streak.save()
            
            user_streak.refresh_from_db()
            user_streak.update_longest_streak()
            
            check_milestones.delay(user_id, user_streak.current_streak)
            update_redis_leaderboard.delay(user_id)
            
            logger.info(f"Updated streak for user {user_id}: current={user_streak.current_streak}")
            
    except User.DoesNotExist:
        logger.error(f"User {user_id} does not exist")
    except Exception as e:
        logger.exception(f"Error updating streak for user {user_id}: {e}")
        self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def daily_streak_reset(self):
    """
    Daily task to check and reset streaks for inactive users.
    Runs at configured time after all timezones have passed midnight.
    """
    logger.info("Starting daily streak reset task")
    
    tz_service = TimezoneService()
    reset_count = 0
    freeze_used_count = 0
    
    for user_streak in UserStreak.objects.filter(is_frozen=False).select_related('user').select_for_update():
        user_local_date = tz_service.get_user_local_date(user_streak)
        expected_last_activity = user_local_date - timedelta(days=1)
        
        if user_streak.last_activity_date is None:
            continue
        
        days_since_activity = (user_local_date - user_streak.last_activity_date).days
        
        if days_since_activity <= 1:
            # Active today or yesterday, streak continues
            continue
        elif days_since_activity == 2:
            # Missed 1 day, use freeze if available
            remaining_freezes = StreakFreeze.get_remaining_freezes(user_streak.user)
            
            if remaining_freezes > 0:
                StreakFreeze.objects.create(
                    user=user_streak.user,
                    used_for_date=expected_last_activity
                )
                freeze_used_count += 1
            else:
                user_streak.current_streak = 0
                user_streak.streak_start_date = None
                user_streak.save()
                reset_count += 1
        else:
            # Missed 2+ days, reset streak
            user_streak.current_streak = 0
            user_streak.streak_start_date = None
            user_streak.save()
            reset_count += 1
    
    logger.info(f"Daily streak reset: {reset_count} resets, {freeze_used_count} freezes used")
    return {'reset_count': reset_count, 'freeze_used_count': freeze_used_count}


@shared_task(bind=True, max_retries=2)
def calculate_leaderboard(self, leaderboard_type: str = 'global'):
    """Calculate and cache leaderboard rankings."""
    logger.info(f"Calculating {leaderboard_type} leaderboard")
    
    today = timezone.now().date()
    period_start, period_end = _get_period_dates(leaderboard_type, today)
    user_scores = _calculate_user_scores(leaderboard_type, period_start, period_end)
    
    LeaderboardEntry.objects.filter(
        leaderboard_type=leaderboard_type,
        period_start=period_start
    ).delete()
    
    entries = []
    for rank, (user_id, scores) in enumerate(user_scores, start=1):
        entry = LeaderboardEntry(
            user_id=user_id,
            leaderboard_type=leaderboard_type,
            rank=rank,
            streak_score=scores['streak_score'],
            activity_score=scores['activity_score'],
            consistency_score=scores['consistency_score'],
            total_score=scores['total_score'],
            period_start=period_start,
            period_end=period_end,
        )
        entries.append(entry)
    
    LeaderboardEntry.objects.bulk_create(entries, batch_size=100)
    create_leaderboard_snapshot.delay(leaderboard_type, today)
    
    logger.info(f"Leaderboard {leaderboard_type} calculated: {len(entries)} entries")
    return {'leaderboard_type': leaderboard_type, 'entries_count': len(entries)}


def _get_period_dates(leaderboard_type: str, today):
    """Get period start and end dates for leaderboard type."""
    if leaderboard_type == 'weekly':
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=6)
    elif leaderboard_type == 'monthly':
        period_start = today.replace(day=1)
        if today.month == 12:
            period_end = today.replace(day=31)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
            period_end = next_month - timedelta(days=1)
    else:
        period_start = None
        period_end = None
        return period_start, period_end


def _calculate_user_scores(leaderboard_type: str, period_start, period_end):
    """Calculate scores for all users. Returns sorted list of (user_id, scores)."""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    users_with_streaks = User.objects.filter(streak__isnull=False).select_related('streak')
    
    activity_query = DailyActivityLog.objects.all()
    if period_start:
        activity_query = activity_query.filter(
            activity_date__gte=period_start,
            activity_date__lte=period_end
        )
    
    scores_list = []
    
    for user in users_with_streaks:
        streak = user.streak
        streak_score = streak.current_streak * 10
        
        user_activities = activity_query.filter(user=user)
        activity_score = sum(
            log.pomodoro_count * 5 + log.tasks_completed * 10 +
            log.goals_achieved * 25 + log.total_study_minutes // 10
            for log in user_activities
        )
        
        consistency_score = 0
        if streak.current_streak >= 7:
            consistency_score += 10
        if streak.current_streak >= 30:
            consistency_score += 25
        if streak.current_streak >= 100:
            consistency_score += 50
        
        total_score = streak_score + activity_score + consistency_score
        
        if total_score > 0:
            scores_list.append((user.id, {
                'streak_score': streak_score,
                'activity_score': activity_score,
                'consistency_score': consistency_score,
                'total_score': total_score,
            }))
    
    scores_list.sort(key=lambda x: x[1]['total_score'], reverse=True)
    return scores_list


@shared_task(bind=True)
def update_redis_leaderboard(self, user_id: int):
    """Update Redis sorted set for real-time leaderboard."""
    try:
        user_streak = UserStreak.objects.get(user_id=user_id)
        redis_client = get_redis_client()
        
        total_score = user_streak.current_streak * 10
        
        redis_client.zadd('leaderboard:global', {str(user_id): total_score})
        
        today = timezone.now().date()
        week_key = f"leaderboard:weekly:{today.isocalendar()[1]}"
        redis_client.zadd(week_key, {str(user_id): total_score})
        redis_client.expire(week_key, 60 * 60 * 24 * 7)
        
        logger.debug(f"Updated Redis leaderboard for user {user_id}")
        
    except UserStreak.DoesNotExist:
        logger.warning(f"No streak found for user {user_id}")


@shared_task(bind=True)
def create_leaderboard_snapshot(self, leaderboard_type: str, snapshot_date):
    """Create historical snapshot of leaderboard."""
    period_start, _ = _get_period_dates(leaderboard_type, snapshot_date)
    
    queryset = LeaderboardEntry.objects.filter(
        leaderboard_type=leaderboard_type,
    ).select_related('user')
    if period_start:
        queryset = queryset.filter(period_start=period_start)
    else:
        queryset = queryset.filter(period_start__isnull=True)
    
    entries = queryset[:100]
    
    top_entries = [
        {
            'rank': entry.rank,
            'user_id': entry.user_id,
            'username': entry.user.username,
            'total_score': entry.total_score,
            'streak_score': entry.streak_score,
        }
        for entry in entries
    ]
    
    stats = LeaderboardEntry.objects.filter(
        leaderboard_type=leaderboard_type
    ).aggregate(total=Count('id'), avg_streak=Avg('streak_score'))
    
    snapshot, created = LeaderboardSnapshot.objects.update_or_create(
        snapshot_date=snapshot_date,
        leaderboard_type=leaderboard_type,
        defaults={
            'top_entries': top_entries,
            'total_participants': stats['total'] or 0,
            'average_streak': stats['avg_streak'] or 0.0,
        }
    )
    
    logger.info(f"Created snapshot for {leaderboard_type} on {snapshot_date}")
    return snapshot.id


@shared_task(bind=True)
def check_milestones(self, user_id: int, current_streak: int):
    """Check and award milestone achievements."""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        
        milestones = StreakMilestone.objects.filter(
            required_streak__lte=current_streak,
            is_active=True
        ).exclude(achievers__user=user)
        
        for milestone in milestones:
            UserMilestone.objects.create(
                user=user,
                milestone=milestone,
                streak_at_achievement=current_streak
            )
            logger.info(f"User {user_id} achieved milestone: {milestone.name}")
            
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for milestone check")


@shared_task(bind=True)
def sync_all_leaderboards(self):
    """Sync all leaderboard types. Called periodically."""
    for lb_type in LeaderboardEntry.LeaderboardType.values:
        calculate_leaderboard.delay(lb_type)
    
    logger.info("Initiated sync for all leaderboard types")


@shared_task(bind=True)
def cleanup_old_snapshots(self, days_to_keep: int = 90):
    """Remove snapshots older than specified days."""
    cutoff_date = timezone.now().date() - timedelta(days=days_to_keep)
    
    deleted, _ = LeaderboardSnapshot.objects.filter(
        snapshot_date__lt=cutoff_date
    ).delete()
    
    logger.info(f"Cleaned up {deleted} old snapshots")
    return deleted


