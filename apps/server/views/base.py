from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from django.utils.timezone import now
from core.views import BaseAPIView
from ..mixins.checker  import ServerCheckerMixin


class ServerBaseView(BaseAPIView, ServerCheckerMixin):
    """Base view for server with standard response helpers."""

    def live(self, request, *args, **kwargs) -> Response:
        """Liveness Probe endpoint to check if the server is running."""
        return Response(
            {
                "status": "live",
                "timestamp": now(),

            },
            status=status.HTTP_200_OK
        )
    
    def ready(self, request: Request, *args, **kwargs) -> Response:
        """Readiness Probe endpoint to check if the server is ready to accept requests."""
        #TODO: Implement readiness checks for database, cache (basically health checks for all dependencies)
        is_db_ok = self.check_database_connection()
        is_cache_ok = self.check_cache_connection()

        if not is_db_ok or not is_cache_ok:
            return Response(
                {
                    "status": "not ready",
                    "timestamp": now(),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(
            {
                "status": "ready",
                "timestamp": now(),
            },
            status=status.HTTP_200_OK
        )
    

