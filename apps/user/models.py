from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# Create your models here.
class User(AbstractUser):
    is_deleted = models.BooleanField(default=False)
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^\+[1-9]\d{1,14}$",
                message="Phone number must be in E.164 format, for example +15551234567.",
            )
        ],
    )
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", blank=True, null=True
    )
    location = models.CharField(max_length=100, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)

    # Study Settings
    preferred_focus_time = models.PositiveIntegerField(
        default=25,
        validators=[MinValueValidator(1)],
        help_text="Default focus duration in minutes",
    )
    preferred_short_break = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Default short break duration in minutes",
    )
    preferred_long_break = models.PositiveIntegerField(
        default=15,
        validators=[MinValueValidator(1)],
        help_text="Default long break duration in minutes",
    )
    pomodoros_until_long_break = models.PositiveIntegerField(
        default=4, validators=[MinValueValidator(1)]
    )

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username}'s profile"


class VerificationToken(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_PHONE = "phone"

    CHANNEL_CHOICES = (
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_PHONE, "Phone"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="verification_tokens",
    )
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(blank=True, null=True)
    attempt_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["channel", "expires_at"]),
            models.Index(fields=["user", "channel", "created_at"]),
        ]

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()

    @property
    def is_used(self):
        return self.used_at is not None

    def __str__(self):
        return f"{self.user.username} {self.channel} token"


class SocialAccount(models.Model):
    PROVIDER_GOOGLE = "google"
    PROVIDER_FACEBOOK = "facebook"

    PROVIDER_CHOICES = (
        (PROVIDER_GOOGLE, "Google"),
        (PROVIDER_FACEBOOK, "Facebook"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    display_name = models.CharField(max_length=255, blank=True)
    picture_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_user_id"],
                name="uniq_social_provider_user",
            ),
            models.UniqueConstraint(
                fields=["user", "provider"],
                name="uniq_social_user_provider",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "email"]),
            models.Index(fields=["user", "provider"]),
        ]

    def __str__(self):
        return f"{self.user.username} via {self.provider}"


class SocialLinkIntent(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="social_link_intents",
    )
    provider = models.CharField(max_length=20, choices=SocialAccount.PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    provider_email = models.EmailField(blank=True)
    provider_display_name = models.CharField(max_length=255, blank=True)
    provider_picture_url = models.URLField(blank=True)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "provider", "created_at"]),
            models.Index(fields=["provider", "expires_at"]),
        ]

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()

    @property
    def is_used(self):
        return self.used_at is not None

    def __str__(self):
        return f"Link intent {self.provider} for {self.user.username}"
