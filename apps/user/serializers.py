import re

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile

User = get_user_model()

PHONE_E164_PATTERN = r"^\+[1-9]\d{1,14}$"


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
        )

    def get_profile(self, obj):
        try:
            profile = obj.profile
        except User.profile.RelatedObjectDoesNotExist:
            return None
        return UserProfileSerializer(profile).data


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "phone_number",
            "password",
            "password_confirm",
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

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            phone_number=validated_data.get("phone_number"),
            password=validated_data["password"],
        )
        UserProfile.objects.create(user=user)

        if user.email:
            send_mail(
                subject="Welcome to Studyzone",
                message=(
                    f"Hi {user.username},\n\n"
                    "Your Studyzone account has been created successfully.\n"
                    "If you are running locally, you can verify delivery in Mailpit.\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        return user
