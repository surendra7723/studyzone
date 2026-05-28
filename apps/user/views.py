from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .serializers import UserRegistrationSerializer, UserSerializer

User = get_user_model()


def _create_user_response(request):
	serializer = UserRegistrationSerializer(data=request.data)
	serializer.is_valid(raise_exception=True)
	user = serializer.save()
	return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
	"""Public user registration endpoint."""
	return _create_user_response(request)


class UserViewSet(viewsets.ViewSet):
	"""ViewSet for public registration and authenticated user operations."""

	permission_classes = [IsAuthenticated]

	def get_permissions(self):
		if self.action == "create":
			return [AllowAny()]
		return [IsAuthenticated()]

	def create(self, request):
		"""Create a new user account."""
		return _create_user_response(request)

	def list(self, request):
		"""Get current user profile."""
		serializer = UserSerializer(request.user)
		return Response(serializer.data)


class AdminUserViewSet(viewsets.ViewSet):
	"""Admin-only ViewSet to manage users (create users)."""

	permission_classes = [IsAdminUser]

	def create(self, request):
		serializer = UserRegistrationSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = serializer.save()
		return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
