# ============================================
# Multi-stage Dockerfile for StudyZone Backend
# ============================================

# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy requirements files first for better layer caching
COPY requirements/base.txt requirements/prod.txt ./requirements/

# Install Python dependencies using uv
RUN uv pip install --system -r requirements/prod.txt

# ============================================
# Stage 2: Production image
# ============================================
FROM python:3.12-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=config.settings

# Create non-root user for security
RUN groupadd -r studyzone && useradd -r -g studyzone studyzone

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R studyzone:studyzone /app

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=studyzone:studyzone . .

# Copy entrypoint script
COPY --chown=studyzone:studyzone docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh

# Switch to non-root user
USER studyzone

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

# Entrypoint and command
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "config.wsgi:application"]

# ============================================
# Stage 3: Development image (optional)
# ============================================
FROM production AS development

USER root

# Install development dependencies
COPY requirements/dev.txt ./requirements/
RUN uv pip install --system -r requirements/dev.txt

USER studyzone

# Override command for development
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
