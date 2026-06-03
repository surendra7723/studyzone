import re
import secrets
import hashlib
import logging
from datetime import timedelta
from threading import local

from twilio.rest import Client
import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount, SocialLinkIntent, UserProfile, VerificationToken

User = get_user_model()
logger = logging.getLogger(__name__)

PHONE_E164_PATTERN = r"^\+[1-9]\d{1,14}$"
SOCIAL_PROVIDER_CHOICES = [
    SocialAccount.PROVIDER_GOOGLE,
    SocialAccount.PROVIDER_FACEBOOK,
]


def _hash_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _verification_expiry():
    minutes = int(getattr(settings, "EMAIL_VERIFICATION_TOKEN_TTL_MINUTES", 30))
    return timezone.now() + timedelta(minutes=minutes)


def _verification_base_url():
    return getattr(settings, "EMAIL_VERIFICATION_URL_BASE", "http://localhost:8000")


def _social_link_base_url():
    return getattr(settings, "SOCIAL_LINK_CONFIRM_URL_BASE", _verification_base_url())


def _social_link_expiry():
    minutes = int(getattr(settings, "SOCIAL_LINK_TOKEN_TTL_MINUTES", 30))
    return timezone.now() + timedelta(minutes=minutes)


def _social_link_cooldown_seconds():
    return int(getattr(settings, "SOCIAL_LINK_RESEND_COOLDOWN_SECONDS", 60))


def _issue_jwt_pair(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def _ensure_user_can_sign_in(user):
    if not user.is_active or getattr(user, "is_deleted", False):
        raise serializers.ValidationError(
            {"detail": "This account is not available for sign-in."}
        )


def _normalize_email(value):
    return (value or "").strip().lower()


def _generate_unique_username(base_value):
    base = re.sub(r"[^a-zA-Z0-9._-]+", "", (base_value or "").strip())
    base = base[:120] if base else "socialuser"
    candidate = base
    counter = 1
    while User.objects.filter(username__iexact=candidate).exists():
        suffix = f"{counter}"
        max_base_len = 150 - len(suffix)
        candidate = f"{base[:max_base_len]}{suffix}"
        counter += 1
    return candidate


def _create_or_update_social_account(user, identity_payload):
    defaults = {
        "user": user,
        "email": identity_payload.get("email") or "",
        "display_name": identity_payload.get("display_name") or "",
        "picture_url": identity_payload.get("picture_url") or "",
        "metadata": identity_payload.get("raw") or {},
    }

    # Avoid reassigning an existing social account to a different user.
    # Use get_or_create and if an existing record belongs to another user, raise.
    try:
        social_account, created = SocialAccount.objects.get_or_create(
            provider=identity_payload["provider"],
            provider_user_id=identity_payload["provider_user_id"],
            defaults=defaults,
        )
    except IntegrityError:
        # Unlikely but handle unique constraint races by attempting to fetch.
        social_account = SocialAccount.objects.filter(
            provider=identity_payload["provider"],
            provider_user_id=identity_payload["provider_user_id"],
        ).first()
        if social_account and social_account.user_id != user.id:
            raise
        created = False

    if not created:
        # Update mutable fields only if the record is already owned by this user.
        if social_account.user_id != user.id:
            raise IntegrityError("Social account already linked to another user")
        changed = False
        for key in ("email", "display_name", "picture_url", "metadata"):
            val = defaults.get(key)
            if getattr(social_account, key) != val:
                setattr(social_account, key, val)
                changed = True
        if changed:
            social_account.save()

    return social_account, created


def issue_social_link_intent(user, identity_payload):
    latest_intent = (
        SocialLinkIntent.objects.filter(
            user=user,
            provider=identity_payload["provider"],
            used_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )
    if latest_intent:
        elapsed = (timezone.now() - latest_intent.created_at).total_seconds()
        if elapsed < _social_link_cooldown_seconds():
            return None

    SocialLinkIntent.objects.filter(
        user=user,
        provider=identity_payload["provider"],
        used_at__isnull=True,
    ).update(used_at=timezone.now(), updated_at=timezone.now())

    raw_token = secrets.token_urlsafe(32)
    SocialLinkIntent.objects.create(
        user=user,
        provider=identity_payload["provider"],
        provider_user_id=identity_payload["provider_user_id"],
        provider_email=identity_payload.get("email") or "",
        provider_display_name=identity_payload.get("display_name") or "",
        provider_picture_url=identity_payload.get("picture_url") or "",
        payload=identity_payload.get("raw") or {},
        token_hash=_hash_token(raw_token),
        expires_at=_social_link_expiry(),
    )
    return raw_token


def send_social_link_confirmation_email(user, provider, raw_token):
    confirm_url = (
        f"{_social_link_base_url().rstrip('/')}/api/users/confirm-social-link/?token={raw_token}"
    )
    provider_title = provider.capitalize()
    send_mail(
        subject=f"Confirm linking your {provider_title} account",
        message=(
            "A request was made to sign in with your social account. "
            f"Confirm linking by opening this link: {confirm_url}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def _validate_google_identity_token(raw_id_token):
    if not getattr(settings, "SOCIAL_AUTH_ENABLED", True):
        raise serializers.ValidationError({"provider": "Social login is disabled."})

    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    if not client_id:
        raise serializers.ValidationError(
            {"provider": "Google login is not configured on this server."}
        )

    try:
        payload = google_id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            client_id,
        )
    except Exception as exc:
        raise serializers.ValidationError({"token": "Invalid Google token."}) from exc

    provider_user_id = str(payload.get("sub") or "").strip()
    if not provider_user_id:
        raise serializers.ValidationError({"token": "Google token missing subject."})

    email = _normalize_email(payload.get("email"))
    return {
        "provider": SocialAccount.PROVIDER_GOOGLE,
        "provider_user_id": provider_user_id,
        "email": email,
        "display_name": (payload.get("name") or "").strip(),
        "picture_url": (payload.get("picture") or "").strip(),
        "email_verified": bool(payload.get("email_verified")),
        "raw": payload,
    }


def _validate_facebook_access_token(raw_access_token):
    if not getattr(settings, "SOCIAL_AUTH_ENABLED", True):
        raise serializers.ValidationError({"provider": "Social login is disabled."})

    facebook_app_id = getattr(settings, "FACEBOOK_APP_ID", "")
    facebook_app_secret = getattr(settings, "FACEBOOK_APP_SECRET", "")
    if not facebook_app_id or not facebook_app_secret:
        raise serializers.ValidationError(
            {"provider": "Facebook login is not configured on this server."}
        )

    try:
        response = requests.get(
            "https://graph.facebook.com/me",
            params={"fields": "id,name,email,picture", "access_token": raw_access_token},
            timeout=8,
        )
    except requests.RequestException as exc:
        raise serializers.ValidationError(
            {"token": "Facebook service is unavailable right now."}
        ) from exc

    if response.status_code != 200:
        raise serializers.ValidationError({"token": "Invalid Facebook token."})

    payload = response.json()
    provider_user_id = str(payload.get("id") or "").strip()
    if not provider_user_id:
        raise serializers.ValidationError({"token": "Facebook token missing user id."})

    app_access_token = f"{facebook_app_id}|{facebook_app_secret}"
    try:
        debug_response = requests.get(
            "https://graph.facebook.com/debug_token",
            params={
                "input_token": raw_access_token,
                "access_token": app_access_token,
            },
            timeout=8,
        )
    except requests.RequestException as exc:
        raise serializers.ValidationError(
            {"token": "Facebook token validation failed."}
        ) from exc

    if debug_response.status_code != 200:
        raise serializers.ValidationError({"token": "Invalid Facebook token."})

    debug_payload = (debug_response.json() or {}).get("data") or {}
    if not debug_payload.get("is_valid"):
        raise serializers.ValidationError({"token": "Invalid Facebook token."})
    if str(debug_payload.get("app_id") or "") != str(facebook_app_id):
        raise serializers.ValidationError({"token": "Facebook app mismatch."})
    debug_user_id = str(debug_payload.get("user_id") or "").strip()
    if debug_user_id and debug_user_id != provider_user_id:
        raise serializers.ValidationError({"token": "Facebook user mismatch."})

    picture_data = payload.get("picture") or {}
    picture_url = ((picture_data.get("data") or {}).get("url") or "").strip()
    email = _normalize_email(payload.get("email"))
    return {
        "provider": SocialAccount.PROVIDER_FACEBOOK,
        "provider_user_id": provider_user_id,
        "email": email,
        "display_name": (payload.get("name") or "").strip(),
        "picture_url": picture_url,
        "email_verified": False,
        "raw": payload,
    }


def issue_email_verification_token(user):
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    VerificationToken.objects.create(
        user=user,
        channel=VerificationToken.CHANNEL_EMAIL,
        token_hash=token_hash,
        expires_at=_verification_expiry(),
    )
    return raw_token

def issue_phone_verification_token(user):
    raw_token = f"{secrets.randbelow(900000) + 100000}"  # 6-digit code
    token_hash = _hash_token(raw_token)

    VerificationToken.objects.create(
        user=user,
        channel=VerificationToken.CHANNEL_PHONE,
        token_hash=token_hash,
        expires_at=_verification_expiry(),
    )
    return raw_token

def send_registration_email(user, raw_verification_token):
    verify_url = (
        f"{_verification_base_url().rstrip('/')}/api/users/verify-email/?token={raw_verification_token}"
    )
    html_message = render_to_string(
        "emails/registration_email.html",
        {
            "user": user,
            "verify_url": verify_url,
        },
    )
    send_mail(
        subject="Welcome to Studyzone - Verify Your Email",
        message=(
            "Welcome to Studyzone! "
            f"Verify your email by opening this link: {verify_url}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_phone_verification_sms(user, raw_verification_token):
    if getattr(settings, "MOCK_TWILIO", False):
        logger.info(
            f"(MOCK) Sent phone verification SMS to user {user.id} at {user.phone_number}: {raw_verification_token}"
        )
        subject = f"Mock SMS to {user.phone_number}"
        email_body = f"From:{settings.TWILIO_FROM_NUMBER}\nTo: {user.phone_number}\n\nYour Studyzone verification code is: {raw_verification_token}"
        send_mail(
            subject=subject,
            message=email_body,
            from_email='twilio-mock@local.dev',
            recipient_list=[f'twilio-mock@local.dev'],
            fail_silently=False,
        )
        return type('MockSMS',(),{"sid": "MOCK_123456789_LOCAL"})()

    else:
        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=(
                    f"Your Studyzone verification code is: {raw_verification_token}. "
                    f"Please enter this code to verify your phone number."
                ),
                from_=settings.TWILIO_PHONE_NUMBER,
                to=user.phone_number,
            )
            logger.info(
                f"Sent phone verification SMS to user {user.id} at {user.phone_number}: {message.sid}"
            )

            VerificationToken.objects.create(
                user=user,
                channel=VerificationToken.CHANNEL_PHONE,
                token_hash=_hash_token(raw_verification_token),
                expires_at=_verification_expiry(),
            )

            return message
        
        except Exception as exc:
            logger.error(
                f"Failed to send phone verification SMS to user {user.id} at {user.phone_number}: {exc}"
            )
            raise serializers.ValidationError(
                {"phone_number": "Failed to send verification SMS. Please try again later."}
            ) from exc

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


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    linked_providers = serializers.SerializerMethodField()

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
        return {
            "requires_confirmation": False,
            "detail": "Social authentication successful.",
            "user": UserSerializer(user).data,
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
            "user": UserSerializer(user).data,
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
