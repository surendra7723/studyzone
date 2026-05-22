from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


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
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "is_active", "is_staff", "profile")
