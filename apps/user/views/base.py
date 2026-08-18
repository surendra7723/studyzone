"""User management views - Phase 4 Refactored."""
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from core.mixins import SoftDeleteMixin
from core.permissions import IsOwnerOrReadOnly
from ..models import UserProfile
from ..serializers import (
    ConfirmSocialLinkSerializer,
    FacebookAuthSerializer,
    GoogleAuthSerializer,
    LinkSocialAccountSerializer,
    ResendEmailVerificationSerializer,
    SocialAccountSerializer,
    UnlinkSocialAccountSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    VerifyEmailSerializer,
    VerifyPhoneSerializer,
)

User = get_user_model()


@extend_schema_view(
    list=extend_schema(summary="Get current user profile", tags=["Users"]),
    create=extend_schema(summary="Register new user", tags=["Users"]),
)
class UserViewSet(SoftDeleteMixin, viewsets.ViewSet):
    """ViewSet for user registration and authenticated user operations."""

    queryset = User.objects.all()
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
        """Create a new user account."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def list(self, request):
        """Get current user profile."""
        if request.user.is_deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["get", "post"], permission_classes=[AllowAny], url_path="verify-email")
    def verify_email(self, request):
        """Verify email with token."""
        token = request.data.get("token") if request.method == "POST" else request.query_params.get("token")
        serializer = VerifyEmailSerializer(data={"token": token})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"detail": "Email verified successfully.", "user": UserSerializer(user).data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get", "post"], permission_classes=[AllowAny], url_path="verify-phone")
    def verify_phone(self, request):
        """Verify phone with SMS code."""
        token = request.data.get("token") if request.method == "POST" else request.query_params.get("token")
        serializer = VerifyPhoneSerializer(data={"token": token})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"detail": "Phone verified successfully.", "user": UserSerializer(user).data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="resend-email-verification")
    def resend_email_verification(self, request):
        """Resend email verification token."""
        serializer = ResendEmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "If an unverified account exists, a verification email has been sent."}, status=status.HTTP_200_OK)

    @extend_schema(request=GoogleAuthSerializer, examples=[OpenApiExample("Google token", value={"id_token": "<token>"}, request_only=True)])
    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="auth/google")
    def auth_google(self, request):
        """Authenticate with Google ID token."""
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)

    @extend_schema(request=FacebookAuthSerializer, examples=[OpenApiExample("Facebook token", value={"access_token": "<token>"}, request_only=True)])
    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="auth/facebook")
    def auth_facebook(self, request):
        """Authenticate with Facebook access token."""
        serializer = FacebookAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)

    @extend_schema(request=ConfirmSocialLinkSerializer, examples=[OpenApiExample("Confirm social link", value={"token": "<token>"}, request_only=True)])
    @action(detail=False, methods=["get", "post"], permission_classes=[AllowAny], url_path="confirm-social-link")
    def confirm_social_link(self, request):
        """Confirm social account linking."""
        token = request.data.get("token") if request.method == "POST" else request.query_params.get("token")
        serializer = ConfirmSocialLinkSerializer(data={"token": token})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get", "post"], url_path="linked-accounts")
    def linked_accounts(self, request):
        """Manage linked social accounts."""
        if request.method == "GET":
            accounts = request.user.social_accounts.select_related("user").order_by("provider")
            return Response(SocialAccountSerializer(accounts, many=True).data, status=status.HTTP_200_OK)
        serializer = LinkSocialAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        social_account = serializer.save(user=request.user)
        return Response(SocialAccountSerializer(social_account).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["delete"], url_path=r"linked-accounts/(?P<provider>[^/.]+)")
    def unlink_linked_account(self, request, provider=None):
        """Unlink a social account."""
        serializer = UnlinkSocialAccountSerializer(data={"provider": provider})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserViewSet(SoftDeleteMixin, viewsets.ViewSet):
    """Admin-only ViewSet to manage users."""
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()

    def get_queryset(self):
        return self.queryset.all()

    def list(self, request):
        """List all users."""
        queryset = self.get_queryset()
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Retrieve a specific user."""
        user = self.get_queryset().get(pk=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)

    def create(self, request):
        """Create a new user account (admin only)."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        """Soft delete a user."""
        user = self.get_queryset().get(pk=pk)
        self.perform_destroy(user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """Restore a soft-deleted user."""
        user = self.queryset.filter(pk=pk, is_deleted=True).first()
        if not user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        user.is_deleted = False
        user.save()
        return Response(UserSerializer(user).data)


@extend_schema_view(
    list=extend_schema(summary="List user profiles", tags=["User Profiles"]),
    create=extend_schema(summary="Create user profile", tags=["User Profiles"]),
    retrieve=extend_schema(summary="Get user profile details", tags=["User Profiles"]),
    update=extend_schema(summary="Update user profile", tags=["User Profiles"]),
    partial_update=extend_schema(summary="Partially update user profile", tags=["User Profiles"]),
    destroy=extend_schema(summary="Delete user profile", tags=["User Profiles"]),
)


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user profiles."""
    queryset = UserProfile.objects.select_related("user").all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        """Filter profiles by authenticated user if not admin."""
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset.filter(user__is_deleted=False)
        return queryset.filter(
            user=self.request.user, user__is_deleted=False
        )
    def perform_create(self, serializer):
        """Create profile for authenticated user."""
        serializer.save(user=self.request.user)
