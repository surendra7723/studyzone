# ============================================
# Docker Entrypoint Script for StudyZone
# ============================================
#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== StudyZone Docker Entrypoint ===${NC}"

# Function to wait for database
wait_for_db() {
    echo -e "${YELLOW}Waiting for database connection...${NC}"
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import psycopg
import os
try:
    conn = psycopg.connect(
        host=os.getenv('DB_HOST', 'db'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'studyzone'),
        user=os.getenv('DB_USER', 'studyzone'),
        password=os.getenv('DB_PASSWORD', 'studyzone')
    )
    conn.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; then
            echo -e "${GREEN}Database is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Attempt $attempt/$max_attempts: Database not ready, waiting...${NC}"
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}ERROR: Database connection failed after $max_attempts attempts${NC}"
    return 1
}

# Function to wait for Redis
wait_for_redis() {
    echo -e "${YELLOW}Waiting for Redis connection...${NC}"
    local max_attempts=30
    local attempt=1
    
    # Extract password from CELERY_BROKER_URL if present
    local redis_password=""
    if [ -n "$REDIS_PASSWORD" ]; then
        redis_password="$REDIS_PASSWORD"
    elif [ -n "$CELERY_BROKER_URL" ]; then
        redis_password=$(echo "$CELERY_BROKER_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    fi
    
    while [ $attempt -le $max_attempts ]; do
        if [ -n "$redis_password" ]; then
            if redis-cli -h redis -a "$redis_password" --no-auth-warning ping 2>/dev/null | grep -q PONG; then
                echo -e "${GREEN}Redis is ready!${NC}"
                return 0
            fi
        else
            if redis-cli -h redis ping 2>/dev/null | grep -q PONG; then
                echo -e "${GREEN}Redis is ready!${NC}"
                return 0
            fi
        fi
        
        echo -e "${YELLOW}Attempt $attempt/$max_attempts: Redis not ready, waiting...${NC}"
        sleep 1
        ((attempt++))
    done
    
    echo -e "${RED}ERROR: Redis connection failed after $max_attempts attempts${NC}"
    return 1
}

# Function to run migrations
run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"
    python manage.py migrate --noinput
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Migrations completed successfully!${NC}"
    else
        echo -e "${RED}ERROR: Migration failed${NC}"
        return 1
    fi
}

# Function to collect static files
collect_static() {
    echo -e "${YELLOW}Collecting static files...${NC}"
    python manage.py collectstatic --noinput
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Static files collected successfully!${NC}"
    else
        echo -e "${YELLOW}WARNING: Static file collection failed (may not be needed in dev)${NC}"
    fi
}

# Function to create superuser (only if environment variables are set)
create_superuser() {
    if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
        echo -e "${YELLOW}Creating superuser if not exists...${NC}"
        python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
email = os.getenv('DJANGO_SUPERUSER_EMAIL')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD')
username = os.getenv('DJANGO_SUPERUSER_USERNAME', email)
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Created superuser: {email}')
else:
    print(f'Superuser already exists: {email}')
"
    fi
}

# Function to run initial setup tasks
setup_celery_beat() {
    echo -e "${YELLOW}Setting up Celery Beat tables...${NC}"
    python manage.py migrate django_celery_beat --noinput 2>/dev/null || true
}

# Main execution
main() {
    echo -e "${GREEN}Starting initialization...${NC}"
    
    # Wait for database (only for web and celery services)
    if [[ "$@" != *"celery"* ]] || [[ "$@" == *"beat"* ]]; then
        wait_for_db || exit 1
    fi
    
    # Wait for Redis (only for web and celery services)
    if [[ "$@" != *"migrate"* ]]; then
        wait_for_redis || exit 1
    fi
    
    # Run setup tasks only for web service
    if [[ "$@" == *"gunicorn"* ]] || [[ "$@" == *"runserver"* ]]; then
        run_migrations
        collect_static
        create_superuser
        setup_celery_beat
    fi
    
    echo -e "${GREEN}Initialization complete!${NC}"
    echo -e "${GREEN}Starting application: $@${NC}"
    
    # Execute the CMD
    exec "$@"
}

# Handle signals for graceful shutdown
trap 'echo -e "${YELLOW}Received shutdown signal...${NC}"; exit 0' SIGTERM SIGINT

# Run main function with all arguments
main "$@"
