"""
Services layer for leaderboard operations.
"""

from datetime import timedelta
from typing import List, Dict, Optional, Any
import redis
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.leaderboard.models import (
    UserStreak, DailyActivityLog, LeaderboardEntry,
    StreakMilestone, UserMilestone, StreakFreeze,
)
from apps.leaderboard.tasks import update_user_streak, update_redis_leaderboard, _get_period_dates

User = get_user_model()


class LeaderboardService:
    """Service class for leaderboard operations."""
    
    @staticmethod
    def get_redis_client():
        redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
        return redis.from_url(redis_url)
    
    @staticmethod
    def record_activity(user_id: int, activity_type: str, **kwargs) -> None:
        """Record user activity and trigger streak update."""
        update_user_streak.delay(user_id, activity_type, **kwargs)
    
    @staticmethod
    def get_leaderboard(leaderboard_type: str = 'global', limit: int = 100, offset: int = 0):
        """Get leaderboard entries."""
        today = timezone.now().date()
        period_start, _ = _get_period_dates(leaderboard_type, today)
        
        queryset = LeaderboardEntry.objects.filter(
            leaderboard_type=leaderboard_type,
        ).select_related('user').order_by('rank')
        
        if period_start:
            queryset = queryset.filter(period_start=period_start)
        else:
            queryset = queryset.filter(period_start__isnull=True)
        
        return [
            {
                'rank': entry.rank,
                'user_id': entry.user_id,
                'username': entry.user.username,
                'total_score': entry.total_score,
                'streak_score': entry.streak_score,
            }
            for entry in queryset[offset:offset+limit]
        ]
    
    @staticmethod
    def get_user_rank(user_id: int, leaderboard_type: str = 'global'):
        """Get user's rank in a specific leaderboard."""
        try:
            today = timezone.now().date()
            period_start, _ = _get_period_dates(leaderboard_type, today)
            
            queryset = LeaderboardEntry.objects.filter(
                user_id=user_id,
                leaderboard_type=leaderboard_type,
            )
            if period_start:
                queryset = queryset.filter(period_start=period_start)
            else:
                queryset = queryset.filter(period_start__isnull=True)
            
            entry = queryset.get()
            return {'rank': entry.rank, 'total_score': entry.total_score}
        except LeaderboardEntry.DoesNotExist:
            return None
    
    @staticmethod
    def get_users_around_user(user_id: int, leaderboard_type: str = 'global', above: int = 5, below: int = 5):
        """Get users ranked around a specific user."""
        try:
            today = timezone.now().date()
            period_start, _ = _get_period_dates(leaderboard_type, today)
            
            base_filter = {'leaderboard_type': leaderboard_type}
            if period_start:
                base_filter['period_start'] = period_start
            else:
                base_filter['period_start__isnull'] = True
            
            user_entry = LeaderboardEntry.objects.get(
                user_id=user_id,
                **base_filter
            )
            
            above_entries = LeaderboardEntry.objects.filter(
                **base_filter,
                rank__gte=user_entry.rank - above,
                rank__lt=user_entry.rank
            ).select_related('user').order_by('rank')
            
            below_entries = LeaderboardEntry.objects.filter(
                **base_filter,
                rank__gt=user_entry.rank,
                rank__lte=user_entry.rank + below
            ).select_related('user').order_by('rank')
            
            return {
                'user_rank': user_entry.rank,
                'user_score': user_entry.total_score,
                'above': [{'rank': e.rank, 'username': e.user.username, 'score': e.total_score} for e in above_entries],
                'below': [{'rank': e.rank, 'username': e.user.username, 'score': e.total_score} for e in below_entries],
            }
        except LeaderboardEntry.DoesNotExist:
            return {'user_rank': None, 'above': [], 'below': []}


class StreakService:
    """Service class for streak operations."""
    
    @staticmethod
    def get_streak_info(user_id: int) -> Dict[str, Any]:
        """Get comprehensive streak information for a user."""
        try:
            streak = UserStreak.objects.get(user_id=user_id)
            return {
                'current_streak': streak.current_streak,
                'longest_streak': streak.longest_streak,
                'last_activity_date': streak.last_activity_date,
                'streak_start_date': streak.streak_start_date,
                'is_frozen': streak.is_streak_frozen,
                'remaining_freezes': StreakFreeze.get_remaining_freezes(User.objects.get(id=user_id)),
            }
        except UserStreak.DoesNotExist:
            return {
                'current_streak': 0, 'longest_streak': 0,
                'last_activity_date': None, 'streak_start_date': None,
                'is_frozen': False, 'remaining_freezes': StreakFreeze.FREEZE_LIMIT_PER_MONTH,
            }
    
    @staticmethod
    def freeze_streak(user_id: int):
        """Use a streak freeze for the user."""
        user = User.objects.get(id=user_id)
        remaining = StreakFreeze.get_remaining_freezes(user)
        
        if remaining <= 0:
            return {'success': False, 'message': 'No streak freezes available this month'}
        
        yesterday = timezone.now().date() - timedelta(days=1)
        freeze, created = StreakFreeze.objects.get_or_create(user=user, used_for_date=yesterday)
        
        if not created:
            return {'success': False, 'message': 'Streak freeze already used for this date'}
        
        return {'success': True, 'remaining_freezes': remaining - 1}
    
    @staticmethod
    def get_streak_history(user_id: int, days: int = 30):
        """Get streak activity history for a user."""
        start_date = timezone.now().date() - timedelta(days=days)
        activities = DailyActivityLog.objects.filter(
            user_id=user_id, activity_date__gte=start_date
        ).order_by('-activity_date')
        
        return [
            {
                'date': activity.activity_date,
                'pomodoro_count': activity.pomodoro_count,
                'tasks_completed': activity.tasks_completed,
                'total_study_minutes': activity.total_study_minutes,
                'is_active': activity.is_active,
            }
            for activity in activities
        ]


class MilestoneService:
    """Service class for milestone operations."""
    
    @staticmethod
    def get_all_milestones():
        return list(StreakMilestone.objects.filter(is_active=True).values(
            'id', 'name', 'required_streak', 'bonus_points', 'badge_icon'
        ))
    
    @staticmethod
    def get_next_milestone(user_id: int):
        """Get next milestone for user to achieve."""
        try:
            streak = UserStreak.objects.get(user_id=user_id)
            next_milestone = StreakMilestone.objects.filter(
                required_streak__gt=streak.current_streak, is_active=True
            ).exclude(achievers__user_id=user_id).order_by('required_streak').first()
            
            if next_milestone:
                return {
                    'name': next_milestone.name,
                    'required_streak': next_milestone.required_streak,
                    'days_remaining': next_milestone.required_streak - streak.current_streak,
                }
        except UserStreak.DoesNotExist:
            pass
        return None

