# Docker Configuration

Complete Docker configuration for running the StudyZone application with all required services.

## Services

- **web** - Django web application (Gunicorn in production, runserver in development)
- **db** - PostgreSQL 16 database with persistence
- **redis** - Redis 8.1.0 for Celery broker, Channels, and caching
- **celery-worker** - Celery worker for async task processing
- **celery-beat** - Celery beat scheduler for periodic tasks

## Quick Start

### Development

```bash
# Copy environment file and configure
cp .env.docker.example .env.docker

# Start all services
docker compose up

# Or run in background
docker compose up -d

# View logs
docker compose logs -f web
```

### Production

```bash
# Set required environment variables
export SECRET_KEY="your-production-secret-key"
export POSTGRES_PASSWORD="secure-db-password"
export REDIS_PASSWORD="secure-redis-password"
export ALLOWED_HOSTS="your-domain.com"

# Start production stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      studyzone_network                           │
│                    (172.28.0.0/16)                               │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │     web     │───▶│     db      │    │   celery-worker     │  │
│  │  (Django)   │    │ (PostgreSQL)│    │   (Task Runner)     │  │
│  │   :8000     │    │   :5432     │    │                     │  │
│  └──────┬──────┘    └─────────────┘    └──────────┬──────────┘  │
│         │                                          │             │
│         │          ┌─────────────┐                 │             │
│         └─────────▶│    redis    │◀────────────────┘             │
│                    │   :6379     │                               │
│                    └──────┬──────┘                               │
│                           │                                       │
│                    ┌──────▼──────┐                               │
│                    │ celery-beat │                               │
│                    │ (Scheduler) │                               │
│                    └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## Volume Persistence

| Volume | Purpose |
|--------|---------|
| `studyzone_postgres_data` | Database files |
| `studyzone_redis_data` | Redis AOF persistence |
| `studyzone_static_volume` | Collected static files |
| `studyzone_media_volume` | User uploaded files |
| `studyzone_log_volume` | Application logs |

## Environment Variables

See `.env.docker.example` for all available configuration options.

### Required for Production

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `REDIS_PASSWORD` | Redis password |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts |

## Useful Commands

```bash
# Rebuild containers after dependency changes
docker compose build --no-cache

# Run database migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# View container logs
docker compose logs -f celery-worker

# Scale celery workers
docker compose up -d --scale celery-worker=3

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: destroys data)
docker compose down -v
```

## Health Checks

All services include health checks:

- **web**: HTTP GET `/api/health/`
- **db**: `pg_isready` command
- **redis**: `redis-cli ping`
- **celery-worker**: `celery inspect ping`
- **celery-beat**: Process check with `pgrep`

## Multi-stage Dockerfile

The Dockerfile uses three stages:

1. **builder** - Compiles dependencies with uv
2. **production** - Optimized production image
3. **development** - Production + dev tools

Target is selected via `target: development` or `target: production` in compose files.
