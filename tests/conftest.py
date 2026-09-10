"""Pytest configuration for integration tests.

This module provides:
- Fixture discovery across test modules
- Django setup configuration
- Custom markers registration
"""
import pytest
import os
import django


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests that test multiple components"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer to run"
    )
    config.addinivalue_line(
        "markers", "requires_redis: Tests that require Redis connection"
    )
    config.addinivalue_line(
        "markers", "requires_celery: Tests that require Celery worker"
    )


# Ensure Django is set up before tests run
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tests.fixtures.common import *  # noqa: F401,F403
