from rest_framework.response import Response
from rest_framework.views import APIView


class BaseAPIView(APIView):
    """Base view with standard success/error response helpers."""

    def success(self, data=None, message='success', status=200):
        return Response(
            {'success': True, 'message': message, 'data': data},
            status=status,
        )

    def error(self, message='error', errors=None, status=400):
        return Response(
            {'success': False, 'message': message, 'errors': errors},
            status=status,
        )
