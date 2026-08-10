from django.db.utils import OperationalError


class ServerCheckerMixin:
    """Mixin to provide server health check methods."""
    def check_database_connection(self) -> bool:
        """Check if the database connection is healthy."""
        from django.db import connections
        try:
            connections['default'].cursor()
            with connections['default'].cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            return True, None
        except OperationalError as e:
            return False, f"Database connection error: {str(e)}"

    def check_cache_connection(self) -> bool:
        """Check if the cache connection is healthy."""
        from django.core.cache import cache
        try:
            cache.has_key("_health_check__ping_")
            return True, None
        except Exception as e:
            return False, f"Cache connection error: {str(e)}"
        