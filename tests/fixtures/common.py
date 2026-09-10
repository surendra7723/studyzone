"""Shared pytest fixtures for integration tests.

This module provides reusable fixtures for:
- User creation and authentication
- Model instances for all apps
- API client setup
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.user.models import UserProfile
from apps.tasks.models import Category, Task
from apps.pomodoro.models import PomodoroSession, TaskSession, Goal
from apps.social.models import FriendRequest, Friendship, UserPresenceState
from apps.notifications.models import Notification, PushSubscription
from apps.ambience.models import Category as AmbienceCategory, AmbienceTrack
from dictionary_app.models import SearchHistory, WordEntry

User = get_user_model()


# ============================================================================
# Client Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(user):
    """Authenticated API client for regular user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def admin_client(admin_user):
    """Authenticated API client for admin user."""
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def user():
    """Create a regular user with verified email."""
    return User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        password='StrongPass123!',
        is_email_verified=True
    )


@pytest.fixture
def user_with_profile(user):
    """Create a user with a complete profile."""
    UserProfile.objects.create(
        user=user,
        bio='Test user bio',
        location='Test City',
        preferred_focus_time=25
    )
    return user


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return User.objects.create_user(
        username='admin',
        email='admin@example.com',
        password='AdminPass123!',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def other_user():
    """Create a second user for testing interactions."""
    return User.objects.create_user(
        username='otheruser',
        email='otheruser@example.com',
        password='StrongPass123!',
        is_email_verified=True
    )


@pytest.fixture
def third_user():
    """Create a third user for testing multi-user scenarios."""
    return User.objects.create_user(
        username='thirduser',
        email='thirduser@example.com',
        password='StrongPass123!',
        is_email_verified=True
    )


@pytest.fixture
def soft_deleted_user(user):
    """Create a soft-deleted user."""
    user.is_deleted = True
    user.save()
    return user


# ============================================================================
# Task Fixtures
# ============================================================================

@pytest.fixture
def category(user):
    """Create a task category."""
    return Category.objects.create(user=user, name='Work', color='#3498db')


@pytest.fixture
def other_category(other_user):
    """Create a category for another user."""
    return Category.objects.create(user=other_user, name='Personal', color='#e74c3c')


@pytest.fixture
def task(user, category):
    """Create a task."""
    return Task.objects.create(
        user=user,
        category=category,
        title='Test Task',
        description='Task description',
        priority=Task.Priority.MEDIUM,
        estimated_pomodoros=4
    )


@pytest.fixture
def completed_task(user, category):
    """Create a completed task."""
    return Task.objects.create(
        user=user,
        category=category,
        title='Completed Task',
        is_completed=True
    )


@pytest.fixture
def multiple_tasks(user, category):
    """Create multiple tasks for testing bulk operations."""
    return [
        Task.objects.create(user=user, category=category, title=f'Task {i}')
        for i in range(5)
    ]


# ============================================================================
# Pomodoro Fixtures
# ============================================================================

@pytest.fixture
def pomodoro_session(user):
    """Create an active pomodoro session."""
    return PomodoroSession.objects.create(
        user=user,
        session_type=PomodoroSession.SessionType.FOCUS,
        is_completed=False
    )


@pytest.fixture
def completed_pomodoro_session(user):
    """Create a completed pomodoro session."""
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    return PomodoroSession.objects.create(
        user=user,
        session_type=PomodoroSession.SessionType.FOCUS,
        start_time=now - timedelta(minutes=25),
        end_time=now,
        is_completed=True,
        active_minutes=25
    )


@pytest.fixture
def task_session(task, pomodoro_session):
    """Create a task session linking a task to a pomodoro session."""
    return TaskSession.objects.create(
        task=task,
        pomodoro_session=pomodoro_session,
        duration_minutes=25
    )


@pytest.fixture
def goal(user):
    """Create a pomodoro goal."""
    from datetime import date, timedelta
    return Goal.objects.create(
        user=user,
        title='Complete project',
        description='Finish the study app project',
        target_date=date.today() + timedelta(days=30)
    )


# ============================================================================
# Social Fixtures
# ============================================================================

@pytest.fixture
def friend_request(user, other_user):
    """Create a pending friend request."""
    return FriendRequest.objects.create(
        sender=user,
        receiver=other_user,
        status='pending'
    )


@pytest.fixture
def friendship(user, other_user):
    """Create a friendship between two users."""
    return Friendship.create_for_users(user, other_user)


@pytest.fixture
def user_presence_state(user):
    """Create a user presence state."""
    state, _ = UserPresenceState.objects.get_or_create(
        user=user,
        defaults={'is_online': False}
    )
    return state


# ============================================================================
# Notification Fixtures
# ============================================================================

@pytest.fixture
def notification(user, other_user):
    """Create a notification."""
    return Notification.objects.create(
        recipient=user,
        actor=other_user,
        verb='friend.request.sent',
        content='sent you a friend request'
    )


@pytest.fixture
def push_subscription(user):
    """Create a push subscription."""
    return PushSubscription.objects.create(
        user=user,
        endpoint='https://fcm.googleapis.com/fcm/send/test-endpoint',
        p256dh='test-p256dh-key',
        auth='test-auth-key'
    )


@pytest.fixture
def multiple_notifications(user, other_user):
    """Create multiple notifications for bulk operations."""
    return [
        Notification.objects.create(
            recipient=user,
            actor=other_user,
            verb='test.verb',
            content=f'Test notification {i}'
        )
        for i in range(3)
    ]


# ============================================================================
# Ambience Fixtures
# ============================================================================

@pytest.fixture
def ambience_category():
    """Create an ambience category."""
    return AmbienceCategory.objects.create(name='Rain')


@pytest.fixture
def ambience_track(ambience_category):
    """Create an ambience track."""
    return AmbienceTrack.objects.create(
        name='Rain Sounds',
        category=ambience_category,
        duration_seconds=300,
        is_active=True
    )


# ============================================================================
# Dictionary Fixtures
# ============================================================================

@pytest.fixture
def search_history(user):
    """Create a search history entry."""
    return SearchHistory.objects.create(
        user=user,
        word='eloquent',
        definition_data={'word': 'eloquent', 'definitions': []}
    )


@pytest.fixture
def word_entry_note(user):
    """Create a word entry note."""
    return WordEntry.objects.create(
        user=user,
        word='serendipity',
        entry_type=WordEntry.EntryType.NOTE,
        custom_note='A happy coincidence'
    )


# ============================================================================
# Additional Fixtures for Complex Scenarios
# ============================================================================

@pytest.fixture
def multiple_pomodoro_sessions(user):
    """Create multiple pomodoro sessions for statistics testing."""
    from django.utils import timezone
    from datetime import timedelta
    
    sessions = []
    now = timezone.now()
    
    # Create sessions across different days
    for days_ago in range(7):
        for i in range(3):
            start = now - timedelta(days=days_ago, hours=i*2)
            sessions.append(PomodoroSession.objects.create(
                user=user,
                session_type=PomodoroSession.SessionType.FOCUS,
                start_time=start,
                end_time=start + timedelta(minutes=25),
                is_completed=True,
                active_minutes=25
            ))
    return sessions
