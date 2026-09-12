# StudyZone Backend

Engineered for low-latency real-time presence tracking via WebSockets (Django Channels) and asynchronous background scheduling with Celery/Redis.

Django REST API for a collaborative study platform with real-time friends/presence, pomodoro sessions, task management, and social auth.

## Features

- User registration with email/phone verification
- Social auth (Google, Facebook) with account linking
- Real-time friend requests and presence tracking via WebSocket
- Pomodoro sessions with task associations and daily/weekly/monthly stats
- Task, goal, and category management
- Notifications and push subscriptions
- Leaderboard, streak tracking, and milestones
- Ambience track catalog with public access
- Dictionary search history and saved word entries
- JWT authentication with token refresh
- OpenAPI schema + Swagger + ReDoc
- CORS support for frontend clients

**Tech**: Django 5.2.17, DRF 3.18.0, PostgreSQL, Redis 8.1.0, Celery 5.6.3, Channels 4.3.2, SimpleJWT 5.5.1

**Tests**: `uv run python manage.py test`
**Integration tests**: `pytest tests/integration/ -v`

### Integration coverage

- Auth and account verification flow
- Task and pomodoro lifecycle
- Social requests, friendships, and presence
- Notifications and push delivery
- Ambience catalog access
- Dictionary lookups and user history

### Recent additions

- Leaderboard and streak APIs with ranking, freezes, and milestones
- Browser push subscription support for notifications
- Dictionary lookup history and saved notes/bookmarks
- OpenAPI schema, Swagger, and Redoc docs
- CORS enabled for frontend integrations

## Quick Start

### Prerequisites
- Python 3.12+
- uv (https://docs.astral.sh/uv/)
- `.python-version` file (pins Python 3.12 for `uv` and `pyenv`)
- PostgreSQL 13+
- Redis 6+
- Mailpit (for local email testing, optional)

### Installation

1. Clone the repository
```bash
git clone <repo-url>
cd studyzone
```

2. Create virtual environment
    ```bash
    uv venv
    ```

3. Install dependencies
    ```bash
    uv pip install -r requirements.txt
    ```

4. Set up environment variables
    ```bash
    cp .env.example .env
    # Edit .env with your configuration
    ```

5. Run database migrations
    ```bash
    uv run python manage.py migrate
    ```

6. Create a superuser
    ```bash
    uv run python manage.py createsuperuser
    ```

7. Start Redis (required for Celery and Channels)
    ```bash
    redis-server
    ```

8. Start Celery worker (in another terminal)
    ```bash
    celery -A config worker -l info
    ```

9. Start Celery beat (in another terminal)
    ```bash
    celery -A config beat -l info
    ```

10. Start the development server (in another terminal)
     ```bash
     uv run python manage.py runserver
     ```

## Quick Install (one-liner)

```bash
# Clone and setup
git clone <repo-url> && cd studyzone
uv venv
uv pip install -r requirements.txt

# Database and migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Terminal 1: Redis
redis-server

# Terminal 2: Celery worker
celery -A config worker -l info

# Terminal 3: Celery beat
celery -A config beat -l info

# Terminal 4: Dev server
uv run python manage.py runserver
```

API: `http://localhost:8000`  
Docs: `http://localhost:8000/api/docs/swagger`

## API Overview

### Base URL
```
http://localhost:8000/api/
```

### Authentication
All endpoints except registration and social auth require a JWT access token. Include it in the Authorization header:
```
Authorization: Bearer <access-token>
```

### User & Auth Endpoints
```
POST   /api/users/                           # Register
GET    /api/users/                           # Get current user
POST   /api/users/verify-email/              # Verify email with token
POST   /api/users/verify-phone/              # Verify phone with token
POST   /api/users/resend-email-verification/ # Resend verification email
POST   /api/users/auth/google/               # Google OAuth sign-in
POST   /api/users/auth/facebook/             # Facebook OAuth sign-in
POST   /api/users/confirm-social-link/       # Confirm social account link
GET    /api/users/linked-accounts/           # List linked social accounts
POST   /api/users/linked-accounts/           # Link social account
DELETE /api/users/linked-accounts/<provider>/ # Unlink social account
```

### Social Endpoints
```
GET    /api/social/friends/                               # List friends
GET    /api/social/presence/                              # Presence snapshot
POST   /api/social/friend-requests/                       # Send friend request
GET    /api/social/friend-requests/                       # List all friend requests
GET    /api/social/friend-requests/incoming/              # Incoming requests
GET    /api/social/friend-requests/outgoing/              # Outgoing requests
POST   /api/social/friend-requests/<pk>/accept/           # Accept request
POST   /api/social/friend-requests/<pk>/decline/          # Decline request
POST   /api/social/friend-requests/<pk>/cancel/           # Cancel request
```

### Dictionary Endpoints
```
GET    /api/dictionary/lookup/<word>/     # Look up a word definition
GET    /api/dictionary/history/           # User search history
DELETE /api/dictionary/history/clear/     # Clear history
GET    /api/dictionary/words/             # User saved notes/bookmarks
POST   /api/dictionary/words/             # Save a word note/bookmark
POST   /api/dictionary/words/<id>/review/ # Mark a word entry as reviewed
```

### Notification Endpoints
```
GET    /api/notifications/notifications/      # List notifications
POST   /api/notifications/notifications/<id>/mark-read/
POST   /api/notifications/notifications/mark-all-read/
GET    /api/notifications/notifications/unread-count/
POST   /api/notifications/push-subscriptions/ # Register browser push subscription
DELETE /api/notifications/push-subscriptions/ # Remove push subscription
```

### Leaderboard & Streak Endpoints
```
GET    /api/leaderboard/leaderboard/      # Global/weekly/monthly leaderboard
GET    /api/leaderboard/leaderboard/rank/ # Current user's rank
GET    /api/leaderboard/leaderboard/nearby/
GET    /api/leaderboard/streak/           # Current streak info
POST   /api/leaderboard/streak/freeze/    # Use a streak freeze
GET    /api/leaderboard/streak/history/   # Streak activity history
PUT    /api/leaderboard/streak/timezone/  # Update user timezone
GET    /api/leaderboard/milestones/       # Milestones and progress
```

### JWT Endpoints
```
POST   /api/auth/token/           # Get JWT tokens
POST   /api/auth/token/refresh/   # Refresh JWT token
POST   /api/auth/token/verify/    # Verify JWT token
```

## Development

```bash
# Run project tests
uv run python manage.py test

# Run integration tests
pytest tests/integration/ -v

# Run specific app tests
uv run python manage.py test apps.social --keepdb

# Format code
black .

# Database operations
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## Project Structure

```
studyzone/
├── config/                          # Django project settings
│   ├── settings.py                  # Main settings
│   ├── urls.py                      # Root URL configuration
│   └── wsgi.py / asgi.py
├── apps/                            # Django apps
│   ├── user/                        # User management
│   ├── social/                      # Social authentication
│   ├── tasks/                       # Task management
│   ├── friends/                     # Friend relationships
│   ├── presence/                    # Real-time presence
│   ├── pomodoro/                    # Pomodoro sessions
│   ├── goals/                       # Goal management
│   ├── notifications/               # Notifications
│   ├── dictionary_app/              # Dictionary/vocabulary
│   ├── ambience/                    # Ambience audio tracks
│   └── core/                        # Core utilities
├── requirements/
│   ├── base.txt                     # Base dependencies
│   ├── dev.txt                      # Development dependencies
│   └── prod.txt                     # Production dependencies
├── media/                           # User-uploaded files
├── manage.py                        # Django management CLI
└── README.md                        # This file
```
