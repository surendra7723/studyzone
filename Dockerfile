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
# Pinned by digest (tag can be moved by upstream; digest is immutable)
COPY --from=ghcr.io/astral-sh/uv:0.11.33@sha256:77280f2f771df71f90786c314fe1bbc1e023feac652969bbf139c280babf2eb7 /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests first for layer caching.
# Export the lockfile as hashed requirements and install into the system
# Python. --require-hashes enforces tamper detection on every artifact.
# On BuildKit hosts, enable the uv cache mount for faster rebuilds:
#   docker buildx build --buildkit .
COPY pyproject.toml uv.lock ./
RUN uv export --no-dev --format requirements-txt --output-file /tmp/requirements.txt && \
    uv pip install --system --require-hashes --no-cache -r /tmp/requirements.txt

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

# Install development dependencies from the same lockfile (dev group),
# overlaying the dev site-packages on top of the production set so the
# dev stage runs the full dependency set. On BuildKit hosts, enable the uv
# cache mount for faster rebuilds: docker buildx build --buildkit .
COPY pyproject.toml uv.lock ./
RUN uv export --dev --group dev --format requirements-txt --output-file /tmp/requirements-dev.txt && \
    uv pip install --system --require-hashes --no-cache -r /tmp/requirements-dev.txt

USER studyzone

# Override command for development
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]