import re
import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.user.utils import (
    _create_or_update_social_account,
    _ensure_user_can_sign_in,
    _generate_unique_username,
    _hash_token,
    _issue_jwt_pair,
    _normalize_email,
    _validate_facebook_access_token,
    _validate_google_identity_token,
    issue_email_verification_token,
    issue_phone_verification_token,
    issue_social_link_intent,
    send_phone_verification_sms,
    send_registration_email,
    send_social_link_confirmation_email,
)

from .models import SocialAccount, SocialLinkIntent, UserProfile, VerificationToken

User = get_user_model()
logger = logging.getLogger(__name__)

PHONE_E164_PATTERN = r"^\+[1-9]\d{1,14}$"
SOCIAL_PROVIDER_CHOICES = [
    SocialAccount.PROVIDER_GOOGLE,
    SocialAccount.PROVIDER_FACEBOOK,
]

from core.serializers import FieldRestrictedSerializer


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "user",
            "bio",
            "profile_picture",
            "location",
            "birth_date",
            "preferred_focus_time",
            "preferred_short_break",
            "preferred_long_break",
            "pomodoros_until_long_break",
        )


class UserSerializer(FieldRestrictedSerializer):
    profile = serializers.SerializerMethodField()
    linked_providers = serializers.SerializerMethodField()

    restricted_fields = (
        "is_staff",
        "is_email_verified",
        "is_phone_verified",
        "phone_number",
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "phone_number",
            "is_email_verified",
            "is_phone_verified",
            "is_active",
            "is_staff",
            "profile",
            "linked_providers",
        )

    def get_profile(self, obj):
        try:
            profile = obj.profile
        except User.profile.RelatedObjectDoesNotExist:
            return None
        return UserProfileSerializer(profile).data

    def get_linked_providers(self, obj):
        return list(obj.social_accounts.values_list("provider", flat=True))


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    verification_options = serializers.ChoiceField(
        choices=["email", "phone"],
        write_only=True,
        required=False,
        default="email",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "phone_number",
            "password",
            "password_confirm",
            "verification_options",
        )

    def validate(self, data):
        password_confirm = data.pop("password_confirm")

        if data["password"] != password_confirm:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        email = (data.get("email") or "").strip()
        phone_number = (data.get("phone_number") or "").strip()

        if not email and not phone_number:
            raise serializers.ValidationError(
                {"non_field_errors": ["Either email or phone number is required."]}
            )

        if phone_number and not re.fullmatch(PHONE_E164_PATTERN, phone_number):
            raise serializers.ValidationError(
                {"phone_number": "Phone number must be in E.164 format, for example +15551234567."}
            )

        data["email"] = email
        data["phone_number"] = phone_number or None
        return data

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        email = (value or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_phone_number(self, value):
        phone_number = (value or "").strip()
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return phone_number

    def validate_verification_options(self, value):
        if value not in ["email", "phone"]:
            raise serializers.ValidationError("Invalid verification option.")
        if value == "email" and not self.initial_data.get("email"):
            raise serializers.ValidationError("Email is required for email verification.")
        if value == "phone" and not self.initial_data.get("phone_number"):
            raise serializers.ValidationError("Phone number is required for phone verification.")
        return value
    
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            phone_number=validated_data.get("phone_number"),
            password=validated_data["password"],
        )
        UserProfile.objects.create(user=user)
        verification_option = validated_data.pop("verification_options", None)
        
        if verification_option == "phone" :
            logger.info(f"Issuing phone verification token for user {user.id} at {user.phone_number}")            
            raw_token = issue_phone_verification_token(user)
            send_phone_verification_sms(user, raw_token)
            
        elif verification_option == "email":
            raw_token = issue_email_verification_token(user)
            send_registration_email(user, raw_token)
        
        return user


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)

    default_error_messages = {
        "invalid": "Invalid or expired verification token.",
        "already_verified": "Email is already verified.",
    }

    def validate_token(self, value):
        token_hash = _hash_token(value)
        try:
            token = VerificationToken.objects.select_related("user").get(
                token_hash=token_hash,
                channel=VerificationToken.CHANNEL_EMAIL,
            )
        except VerificationToken.DoesNotExist:
            self.fail("invalid")

        token.attempt_count += 1
        token.save(update_fields=["attempt_count", "updated_at"])

        if token.is_used or token.is_expired:
            self.fail("invalid")

        if token.user.is_email_verified:
            self.fail("already_verified")

        self.context["verification_token"] = token
        return value

    def save(self):
        token = self.context["verification_token"]
        user = token.user

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        token.used_at = timezone.now()
        token.save(update_fields=["used_at", "updated_at"])

        return user

class VerifyPhoneSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)

    default_error_messages = {
        "invalid": "Invalid or expired verification token.",
        "already_verified": "Phone number is already verified.",
    }

    def validate_token(self, value):
        token_hash = _hash_token(value)
        try:
            token = VerificationToken.objects.select_related("user").get(
                token_hash=token_hash,
                channel=VerificationToken.CHANNEL_PHONE,
            )
        except VerificationToken.DoesNotExist:
            self.fail("invalid")

        token.attempt_count += 1
        token.save(update_fields=["attempt_count", "updated_at"])

        if token.is_used or token.is_expired:
            self.fail("invalid")

        if token.user.is_phone_verified:
            self.fail("already_verified")

        self.context["verification_token"] = token
        return value

    def save(self):
        token = self.context["verification_token"]
        user = token.user

        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])

        token.used_at = timezone.now()
        token.save(update_fields=["used_at", "updated_at"])

        return user

class ResendEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self):
        email = self.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        if not user or user.is_email_verified:
            return None

        cooldown_seconds = int(
            getattr(settings, "EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", 60)
        )
        latest_token = (
            VerificationToken.objects.filter(
                user=user,
                channel=VerificationToken.CHANNEL_EMAIL,
            )
            .order_by("-created_at")
            .first()
        )

        if latest_token and (timezone.now() - latest_token.created_at).total_seconds() < cooldown_seconds:
            return user

        raw_token = issue_email_verification_token(user)
        send_registration_email(user, raw_token)
        return user


class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = (
            "id",
            "provider",
            "provider_user_id",
            "email",
            "display_name",
            "picture_url",
            "created_at",
        )


class _BaseSocialAuthSerializer(serializers.Serializer):
    def _resolve_identity(self, validated_data):
        raise NotImplementedError

    def _build_success_response(self, user):
        _ensure_user_can_sign_in(user)
        request = self.context.get("request")
        return {
            "requires_confirmation": False,
            "detail": "Social authentication successful.",
            "user": UserSerializer(user, context={"request": request}).data,
            "tokens": _issue_jwt_pair(user),
        }

    def save(self):
        if not getattr(settings, "SOCIAL_AUTH_ENABLED", True):
            raise serializers.ValidationError({"provider": "Social login is disabled."})

        identity = self._resolve_identity(self.validated_data)

        linked_account = SocialAccount.objects.select_related("user").filter(
            provider=identity["provider"],
            provider_user_id=identity["provider_user_id"],
        ).first()
        if linked_account:
            return self._build_success_response(linked_account.user)

        email = _normalize_email(identity.get("email"))
        existing_user = User.objects.filter(email__iexact=email).first() if email else None
        if existing_user:
            raw_intent_token = issue_social_link_intent(existing_user, identity)
            if raw_intent_token:
                send_social_link_confirmation_email(
                    existing_user,
                    identity["provider"],
                    raw_intent_token,
                )
            return {
                "requires_confirmation": True,
                "detail": "Confirmation is required to link this social account. Check your email.",
            }

        username_seed = identity.get("display_name") or (
            email.split("@")[0] if email else "socialuser"
        )
        try:
            with transaction.atomic():
                username = _generate_unique_username(username_seed)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=None,
                )
                if identity.get("email_verified") and email:
                    user.is_email_verified = True
                    user.save(update_fields=["is_email_verified"])

                UserProfile.objects.create(user=user)
                _create_or_update_social_account(user, identity)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"detail": "Could not complete social sign-in. Please try again."}
            ) from exc

        return self._build_success_response(user)


class GoogleAuthSerializer(_BaseSocialAuthSerializer):
    id_token = serializers.CharField(write_only=True)

    def _resolve_identity(self, validated_data):
        return _validate_google_identity_token(validated_data["id_token"])


class FacebookAuthSerializer(_BaseSocialAuthSerializer):
    access_token = serializers.CharField(write_only=True)

    def _resolve_identity(self, validated_data):
        return _validate_facebook_access_token(validated_data["access_token"])


SOCIAL_PROVIDER_VALIDATORS = {
    SocialAccount.PROVIDER_GOOGLE: _validate_google_identity_token,
    SocialAccount.PROVIDER_FACEBOOK: _validate_facebook_access_token,
}


class ConfirmSocialLinkSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)

    default_error_messages = {
        "invalid": "Invalid or expired social link confirmation token.",
    }

    def validate_token(self, value):
        token_hash = _hash_token(value)
        try:
            intent = SocialLinkIntent.objects.select_related("user").get(token_hash=token_hash)
        except SocialLinkIntent.DoesNotExist:
            self.fail("invalid")

        if intent.is_used or intent.is_expired:
            self.fail("invalid")

        self.context["link_intent"] = intent
        return value

    def save(self):
        with transaction.atomic():
            intent = SocialLinkIntent.objects.select_for_update().select_related("user").get(
                id=self.context["link_intent"].id
            )
            user = intent.user
            _ensure_user_can_sign_in(user)

            if intent.is_used or intent.is_expired:
                self.fail("invalid")

            existing = SocialAccount.objects.filter(
                provider=intent.provider,
                provider_user_id=intent.provider_user_id,
            ).exclude(user=user)
            if existing.exists():
                raise serializers.ValidationError(
                    {"detail": "This social account is already linked to another user."}
                )

            SocialAccount.objects.update_or_create(
                user=user,
                provider=intent.provider,
                defaults={
                    "provider_user_id": intent.provider_user_id,
                    "email": intent.provider_email,
                    "display_name": intent.provider_display_name,
                    "picture_url": intent.provider_picture_url,
                    "metadata": intent.payload,
                },
            )

            intent.used_at = timezone.now()
            intent.save(update_fields=["used_at", "updated_at"])

        return {
            "detail": "Social account linked successfully.",
            "requires_confirmation": False,
            "user": UserSerializer(user, context={"request": self.context.get("request")}).data,
            "tokens": _issue_jwt_pair(user),
        }


class LinkSocialAccountSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=SOCIAL_PROVIDER_CHOICES)
    id_token = serializers.CharField(required=False, allow_blank=True)
    access_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        provider = attrs["provider"]
        if provider == SocialAccount.PROVIDER_GOOGLE and not attrs.get("id_token"):
            raise serializers.ValidationError({"id_token": "This field is required for Google."})
        if provider == SocialAccount.PROVIDER_FACEBOOK and not attrs.get("access_token"):
            raise serializers.ValidationError({"access_token": "This field is required for Facebook."})
        return attrs

    def save(self, user):
        provider = self.validated_data["provider"]
        token_value = (
            self.validated_data.get("id_token")
            if provider == SocialAccount.PROVIDER_GOOGLE
            else self.validated_data.get("access_token")
        )
        identity = SOCIAL_PROVIDER_VALIDATORS[provider](token_value)

        with transaction.atomic():
            existing = SocialAccount.objects.select_for_update().filter(
                provider=identity["provider"],
                provider_user_id=identity["provider_user_id"],
            ).first()
            if existing and existing.user_id != user.id:
                raise serializers.ValidationError(
                    {"detail": "This social account is already linked to another user."}
                )

            if SocialAccount.objects.filter(user=user, provider=identity["provider"]).exclude(
                provider_user_id=identity["provider_user_id"]
            ).exists():
                raise serializers.ValidationError(
                    {"detail": f"Your account is already linked with {identity['provider']}."}
                )

            social_account, _ = _create_or_update_social_account(user, identity)
        return social_account


class UnlinkSocialAccountSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=SOCIAL_PROVIDER_CHOICES)

    def save(self, user):
        provider = self.validated_data["provider"]
        with transaction.atomic():
            social_account = SocialAccount.objects.select_for_update().filter(
                user=user,
                provider=provider,
            ).first()
            if not social_account:
                raise serializers.ValidationError(
                    {"detail": f"No linked {provider} account found."}
                )

            linked_count = SocialAccount.objects.filter(user=user).count()
            if linked_count <= 1 and not user.has_usable_password():
                raise serializers.ValidationError(
                    {
                        "detail": (
                            "Cannot unlink your last sign-in method. "
                            "Set a password or link another provider first."
                        )
                    }
                )

            social_account.delete()
        return None


class SoftDeleteAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.is_deleted:
            raise serializers.ValidationError(
                {"detail": "Your account has been deactivated."}
            )
        return data


class SoftDeleteAwareTokenObtainPairView(TokenObtainPairView):
    serializer_class = SoftDeleteAwareTokenObtainPairSerializer
