# Integration Test Suite

This directory contains comprehensive integration tests for the StudyZone application.

## Overview

Integration tests verify that multiple components work together correctly, testing the interaction between different modules, services, and external dependencies.

## Test Structure

```
tests/
├── conftest.py                    # Root pytest configuration
├── fixtures/
│   └── common.py                  # Shared fixtures for all tests
└── integration/
    ├── conftest.py                # Integration test configuration
    ├── test_user_auth_integration.py
    ├── test_tasks_pomodoro_integration.py
    ├── test_social_integration.py
    ├── test_notifications_integration.py
    ├── test_ambience_integration.py
    └── test_dictionary_integration.py
```

## Running Tests

### Run all integration tests
```bash
pytest tests/integration/ -v
```

### Run specific test file
```bash
pytest tests/integration/test_user_auth_integration.py -v
```

### Run with markers
```bash
# Skip slow tests
pytest tests/integration/ -v -m "not slow"

# Run only integration tests
pytest tests/integration/ -v -m integration

# Skip tests requiring external services
pytest tests/integration/ -v -m "not requires_redis"
```

### Run with coverage
```bash
pytest tests/integration/ -v --cov=apps --cov=dictionary_app --cov-report=html
```

## Features Tested

### 1. User Authentication (test_user_auth_integration.py)
- **Key Components**: User, VerificationToken, UserProfile, SocialAccount
- **Integration Touchpoints**:
  - User Model ↔ VerificationToken (email/phone verification)
  - User Model ↔ UserProfile (profile creation)
  - Authentication ↔ JWT Tokens
- **Test Cases**:
  - Registration creates user and verification token
  - Email verification completes flow
  - JWT authentication flow (login, refresh, verify)
  - Soft-deleted users cannot authenticate
  - User data isolation

### 2. Tasks & Pomodoro (test_tasks_pomodoro_integration.py)
- **Key Components**: Task, Category, PomodoroSession, TaskSession, Goal
- **Integration Touchpoints**:
  - Task ↔ Category (FK with user validation)
  - PomodoroSession ↔ TaskSession ↔ Task (time tracking chain)
  - User ↔ Task ↔ PomodoroSession (ownership cascade)
- **Test Cases**:
  - Category user isolation
  - Task creation with category validation
  - Category deletion nullifies tasks
  - Bulk operations (create, update, delete)
  - Pomodoro session linked to task
  - Task session validates user ownership
  - Goal management

### 3. Social Features (test_social_integration.py)
- **Key Components**: FriendRequest, Friendship, UserPresenceState
- **Integration Touchpoints**:
  - FriendRequest → Friendship (accept flow)
  - User ↔ UserPresenceState (online status)
  - FriendRequest → Notification (notification creation)
- **Test Cases**:
  - Send friend request
  - Accept request creates friendship
  - Reject request flow
  - Duplicate request prevention
  - Friendship listing and removal
  - User presence management

### 4. Notifications (test_notifications_integration.py)
- **Key Components**: Notification, PushSubscription
- **Integration Touchpoints**:
  - User ↔ Notification (recipient)
  - User ↔ PushSubscription (push notifications)
- **Test Cases**:
  - List notifications
  - Mark notification as read
  - Soft delete notification
  - User isolation for notifications
  - Push subscription management

### 5. Ambience (test_ambience_integration.py)
- **Key Components**: AmbienceTrack, Category
- **Integration Touchpoints**:
  - AmbienceTrack ↔ Category (filtering)
  - Public access (no authentication required)
- **Test Cases**:
  - List active tracks
  - Inactive tracks excluded
  - Filter by category
  - Public endpoint access

### 6. Dictionary (test_dictionary_integration.py)
- **Key Components**: SearchHistory, WordEntry
- **Integration Touchpoints**:
  - External Dictionary API ↔ SearchHistory (lookup caching)
  - User ↔ WordEntry (notes/bookmarks)
- **Test Cases**:
  - Word lookup with external API
  - Search history management
  - Word entry notes and bookmarks
  - Unique entry per type validation

## Test Coverage

| Feature | Components | Integration Points | Test Cases |
|---------|-----------|-------------------|------------|
| User Auth | User, VerificationToken, UserProfile | 5 | 10+ |
| Tasks/Pomodoro | Task, Category, PomodoroSession, Goal | 4 | 12+ |
| Social | FriendRequest, Friendship, Presence | 3 | 8+ |
| Notifications | Notification, PushSubscription | 2 | 6+ |
| Ambience | Track, Category | 2 | 4+ |
| Dictionary | SearchHistory, WordEntry | 2 | 6+ |

## Writing New Tests

### Using Fixtures

```python
import pytest
from tests.fixtures.common import *

@pytest.mark.integration
def test_my_feature(authenticated_client, user):
    """Test description."""
    response = authenticated_client.get('/api/endpoint/')
    assert response.status_code == 200
```

### Creating New Fixtures

Add fixtures to `tests/fixtures/common.py`:

```python
@pytest.fixture
def my_new_fixture(user):
    """Create a test fixture."""
    return MyModel.objects.create(user=user, name='Test')
```

## Best Practices

1. **Test real integration points**: Use actual database queries and API calls
2. **Mock external services**: Mock external APIs (dictionary, social auth)
3. **Test error scenarios**: Include both success and failure cases
4. **Use transactions**: Tests should clean up after themselves
5. **Isolate tests**: Each test should be independent

## Troubleshooting

### Redis Connection Errors
Tests marked with `@pytest.mark.requires_redis` require a running Redis instance.
```bash
# Skip Redis-dependent tests
pytest tests/integration/ -v -m "not requires_redis"
```

### Database Errors
Ensure test database is properly configured:
```bash
export DJANGO_SETTINGS_MODULE=config.settings
python manage.py test --settings=config.settings
```

### Import Errors
Make sure the virtual environment is activated and all dependencies are installed.
