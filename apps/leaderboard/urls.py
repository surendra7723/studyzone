"""
URL Configuration for Streak-Based Leaderboard System.
"""

from django.urls import path
from apps.leaderboard import views

app_name = "leaderboard"

urlpatterns = [
    # Leaderboard endpoints
    path('leaderboard/', views.get_leaderboard, name='get-leaderboard'),
    path('leaderboard/rank/', views.get_user_rank, name='get-user-rank'),
    path('leaderboard/nearby/', views.get_nearby_users, name='get-nearby-users'),
    
    # Streak endpoints
    path('streak/', views.get_streak_status, name='get-streak-status'),
    path('streak/freeze/', views.use_streak_freeze, name='use-streak-freeze'),
    path('streak/history/', views.get_streak_history, name='get-streak-history'),
    path('streak/timezone/', views.update_user_timezone, name='update-user-timezone'),
    
    # Milestones
    path('milestones/', views.get_milestones, name='get-milestones'),
]
