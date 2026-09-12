"""
API Views for Streak-Based Leaderboard System.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.leaderboard.models import UserStreak, LeaderboardEntry
from apps.leaderboard.services import LeaderboardService, StreakService, MilestoneService


@extend_schema(tags=['Leaderboard'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_leaderboard(request):
    """Get global leaderboard rankings."""
    leaderboard_type = request.query_params.get('type', 'global')
    limit = int(request.query_params.get('limit', 100))
    offset = int(request.query_params.get('offset', 0))
    
    valid_types = [t[0] for t in LeaderboardEntry.LeaderboardType.choices]
    if leaderboard_type not in valid_types:
        return Response({'error': f'Invalid type. Valid: {valid_types}'}, status=400)
    
    leaderboard = LeaderboardService.get_leaderboard(leaderboard_type, limit, offset)
    return Response({'leaderboard_type': leaderboard_type, 'entries': leaderboard})


@extend_schema(tags=['Leaderboard'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_rank(request):
    """Get current user's rank in the leaderboard."""
    leaderboard_type = request.query_params.get('type', 'global')
    rank_info = LeaderboardService.get_user_rank(request.user.id, leaderboard_type)
    return Response(rank_info or {'rank': None, 'message': 'Not ranked yet'})


@extend_schema(tags=['Leaderboard'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nearby_users(request):
    """Get users ranked around the current user."""
    leaderboard_type = request.query_params.get('type', 'global')
    nearby = LeaderboardService.get_users_around_user(
        request.user.id, leaderboard_type,
        int(request.query_params.get('above', 5)),
        int(request.query_params.get('below', 5))
    )
    return Response(nearby)


@extend_schema(tags=['Streak'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_streak_status(request):
    """Get current user's streak information."""
    streak_info = StreakService.get_streak_info(request.user.id)
    return Response(streak_info)


@extend_schema(tags=['Streak'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_streak_freeze(request):
    """Use a streak freeze to protect current streak."""
    result = StreakService.freeze_streak(request.user.id)
    return Response(result, status=200 if result['success'] else 400)


@extend_schema(tags=['Streak'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_streak_history(request):
    """Get streak activity history for current user."""
    days = int(request.query_params.get('days', 30))
    history = StreakService.get_streak_history(request.user.id, days)
    return Response({'days': days, 'history': history})


@extend_schema(tags=['Milestones'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_milestones(request):
    """Get all milestones and user's achievement status."""
    return Response({
        'milestones': MilestoneService.get_all_milestones(),
        'next_milestone': MilestoneService.get_next_milestone(request.user.id),
    })


@extend_schema(tags=['Streak'])
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_timezone(request):
    """Update user's timezone for streak calculation."""
    timezone_str = request.data.get('timezone')
    if not timezone_str:
        return Response({'error': 'Timezone required'}, status=400)
    
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(timezone_str)
    except Exception:
        return Response({'error': f'Invalid timezone: {timezone_str}'}, status=400)
    
    streak, _ = UserStreak.objects.get_or_create(user=request.user, defaults={'user_timezone': timezone_str})
    streak.user_timezone = timezone_str
    streak.save()
    
    return Response({'success': True, 'timezone': timezone_str})
