from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import SocialAccount, SocialLinkIntent, UserProfile

User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "is_staff", "is_active", "is_deleted")
    list_filter = ("is_staff", "is_active", "is_deleted")
    search_fields = ("username", "email")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "birth_date")
    search_fields = ("user__username", "location")


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "provider_user_id", "email", "created_at")
    list_filter = ("provider",)
    search_fields = ("user__username", "provider_user_id", "email")


@admin.register(SocialLinkIntent)
class SocialLinkIntentAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "provider_email", "expires_at", "used_at")
    list_filter = ("provider", "used_at")
    search_fields = ("user__username", "provider_email", "provider_user_id")
