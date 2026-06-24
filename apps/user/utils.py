
import secrets

from apps.user.models import VerificationToken

import re
import secrets
import hashlib
import logging
from datetime import timedelta

from twilio.rest import Client
import requests
from django.conf import settings
from django.db import IntegrityError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount, SocialLinkIntent, User, VerificationToken

logger = logging.getLogger(__name__)

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
        logger.info(f"(MOCK) Sent phone verification SMS to user {user.id} at {user.phone_number}: {raw_verification_token}")
        # Token already created in issue_phone_verification_token, do not create again
        return type('MockSMS', (), {"sid": "MOCK_123456789_LOCAL"})()
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
            logger.info(f"Sent phone verification SMS to user {user.id} at {user.phone_number}: {message.sid}")
            # Token already created, no need to create again
            return message
        except Exception as exc:
            logger.error(f"Failed to send phone verification SMS to user {user.id} at {user.phone_number}: {exc}")
            raise serializers.ValidationError(
                {"phone_number": "Failed to send verification SMS. Please try again later."}
            ) from exc
        