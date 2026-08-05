# StudyZone Backend

Django REST API for a collaborative study platform with real-time friends/presence, pomodoro sessions, task management, and social auth.

## Features

- User registration with email/phone verification
- Social auth (Google, Facebook) with account linking
- Real-time friend requests and presence tracking via WebSocket
- Pomodoro sessions with task associations and daily/weekly/monthly stats
- Task and goal management
- JWT authentication with token refresh
- API docs (Swagger + ReDoc)

**Tech**: Django 6.0, DRF, PostgreSQL, Redis, Celery, Channels, SimpleJWT

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 13+
- Redis 6+
- Mailpit (for local email testing, optional)

### Installation

1. Clone the repository
```bash
git clone <repo-url>
cd studyzone
```

2. Create and activate virtual environment
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run database migrations
```bash
python manage.py migrate
```

6. Create a superuser
```bash
python manage.py createsuperuser
```

7. Start Redis (required for Celery and Channels)
```bash
redis-server
```

8. Start Celery worker (in another terminal)
```bash
celSetup

### Prerequisites
- Python 3.12+, PostgreSQL 13+, Redis 6+

### Installation

```bash
# Clone and setup
git clone <repo-url> && cd studyzone
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Database and migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Terminal 1: Redis
redis-server

# Terminal 2: Celery worker
celery -A config worker -l info

# Terminal 3: Celery beat
celery -A config beat -l info

# Terminal 4: Dev server
python manage.py runserver
```

API: `http://localhost:8000`  
Docs: `http://localhost:8000/api/docs/swaggerfig (queues, timeouts)
│   └── schedules.py              # Celery beat schedule
├── dictionary_app/               # Dictionary/vocabulary app
├── docs/                          # API documentation
│   └── social_auth.md            # Social auth frontend contract
├── requirements.txt              # Python dependencies
├── manage.py                      # Django management CLI
└── README.md                      # This file
```

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
POST   /users/                           # Register
GET    /users/                           # Get current user
POST   /users/verify-email/              # Verify email with token
POST   /users/verify-phone/              # Verify phone with token
POST   /users/resend-email-verification/ # Resend verification email
POST   /users/auth/google/               # Google OAuth sign-in
POST   /users/auth/facebook/             # Facebook OAuth sign-in
POST   /users/confirm-social-link/       # Confirm social account link
GET    /users/linked-accounts/           # List linked social accounts
DELKey Endpoints

### Auth & Users
```
POST   /api/users/                    # Register
GET    /api/users/                    # Get current user
POST   /api/users/verify-email/       # Verify email
POST   /api/auth/token/               # Get JWT tokens
POSDevelopment

```bash
# Run tests
python manage.py test

# Run specific app tests
python manage.py test apps.social --keepdb

# Format code
black .

# Database operations
python manage.py makemigrations
python manage.py migrate
```