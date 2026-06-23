from django.contrib.auth import get_user_model
from requests import request
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.response import Response

from .serializers import (
	ConfirmSocialLinkSerializer,
	FacebookAuthSerializer,
	GoogleAuthSerializer,
	LinkSocialAccountSerializer,
	ResendEmailVerificationSerializer,
	SocialAccountSerializer,
	UnlinkSocialAccountSerializer,
	UserRegistrationSerializer,
	UserSerializer,
	VerifyEmailSerializer,
	VerifyPhoneSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ViewSet):
	"""ViewSet for user registration and authenticated user operations."""

	permission_classes = [IsAuthenticated]
	serializer_class = UserRegistrationSerializer

	def get_permissions(self):
		if self.action in {
			"create",
			"verify_email",
			"resend_email_verification",
			"auth_google",
			"auth_facebook",
			"confirm_social_link",
		}:
			return [AllowAny()]
		return [IsAuthenticated()]

	def create(self, request):
     
		"""Create a new user account. Either email or phone_number is required."""
		serializer = UserRegistrationSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = serializer.save()
		return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

	def list(self, request):
		"""Get current user profile."""
		serializer = UserSerializer(request.user)
		return Response(serializer.data)

	@action(detail=False, methods=["get", "post"], permission_classes=[AllowAny], url_path="verify-email")
	def verify_email(self, request):		
		token = request.data.get("token") if request.method == "POST" else request.query_params.get("token")
		serializer = VerifyEmailSerializer(data={"token": token})
		serializer.is_valid(raise_exception=True)
		user = serializer.save()
		return Response(
			{
				"detail": "Email verified successfully.",
				"user": UserSerializer(user).data,
			},
			status=status.HTTP_200_OK,
		)

	@action(detail=False,methods=["get", "post"], permission_classes=[AllowAny], url_path="verify-phone")
	def verify_phone(self, request):

		token = request.data.get("token") if request.method == "POST" else request.query_params.get("token")
		ser = VerifyPhoneSerializer(data={"token": token})
		ser.is_valid(raise_exception=True)
		user = ser.save()
		return Response(
			{
				"detail": "Phone verified successfully.",
				"user": UserSerializer(user).data,
			},
			status=status.HTTP_200_OK,
		)
	
	@action(
		detail=False,
		methods=["post"],
		permission_classes=[AllowAny],
		url_path="resend-email-verification",
	)
	def resend_email_verification(self, request):
		serializer = ResendEmailVerificationSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(
			{"detail": "If an unverified account exists, a verification email has been sent."},
			status=status.HTTP_200_OK,
		)
  

	@extend_schema(
		request=GoogleAuthSerializer,
		examples=[
			OpenApiExample(
				"Google token",
				value={"id_token": "<google-id-token>"},
				request_only=True,
			),
		],
	)
	@action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="auth/google")
	def auth_google(self, request):
		serializer = GoogleAuthSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		return Response(serializer.save(), status=status.HTTP_200_OK)

	@extend_schema(
		request=FacebookAuthSerializer,
		examples=[
			OpenApiExample(
				"Facebook token",
				value={"access_token": "<fb-access-token>"},
				request_only=True,
			),
		],
	)
	@action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="auth/facebook")
	def auth_facebook(self, request):
		serializer = FacebookAuthSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		return Response(serializer.save(), status=status.HTTP_200_OK)

	@extend_schema(
		request=ConfirmSocialLinkSerializer,
		examples=[
			OpenApiExample(
				"Confirm social link",
				value={"token": "<confirmation-token>"},
				request_only=True,
			),
		],
	)
	@action(
		detail=False,
		methods=["get", "post"],
		permission_classes=[AllowAny],
		url_path="confirm-social-link",
	)
	def confirm_social_link(self, request):
		token = request.data.get("token") if request.method == "POST" else request.query_params.get("token")
		serializer = ConfirmSocialLinkSerializer(data={"token": token})
		serializer.is_valid(raise_exception=True)
		result = serializer.save()
		return Response(result, status=status.HTTP_200_OK)

	@action(detail=False, methods=["get", "post"], url_path="linked-accounts")
	def linked_accounts(self, request):
		if request.method == "GET":
			accounts = request.user.social_accounts.order_by("provider")
			return Response(SocialAccountSerializer(accounts, many=True).data, status=status.HTTP_200_OK)

		serializer = LinkSocialAccountSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		social_account = serializer.save(user=request.user)
		return Response(SocialAccountSerializer(social_account).data, status=status.HTTP_200_OK)

	@action(
		detail=False,
		methods=["delete"],
		url_path=r"linked-accounts/(?P<provider>[^/.]+)",
	)
	def unlink_linked_account(self, request, provider=None):
		serializer = UnlinkSocialAccountSerializer(data={"provider": provider})
		serializer.is_valid(raise_exception=True)
		serializer.save(user=request.user)
		return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserViewSet(viewsets.ViewSet):
	"""Admin-only ViewSet to manage users (create users)."""

	permission_classes = [IsAdminUser]

	def create(self, request):
		serializer = UserRegistrationSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = serializer.save()
		return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
