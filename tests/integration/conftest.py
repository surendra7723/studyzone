"""Pytest configuration for integration tests."""
import pytest
import os
import django


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "requires_redis: Tests requiring Redis")
    config.addinivalue_line("markers", "requires_celery: Tests requiring Celery")


def pytest_collection_modifyitems(config, items):
    """Auto-apply django_db mark to all integration tests."""
    for item in items:
        if "integration" in item.keywords:
            item.add_marker("django_db")


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
