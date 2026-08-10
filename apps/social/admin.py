from django.contrib import admin

from .models import FriendRequest, Friendship, UserPresenceState


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "status", "created_at", "responded_at")
    list_filter = ("status",)
    search_fields = ("sender__username", "receiver__username")


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("user_low", "user_high", "created_at")
    search_fields = ("user_low__username", "user_high__username")


@admin.register(UserPresenceState)
class UserPresenceStateAdmin(admin.ModelAdmin):
    list_display = ("user", "is_online", "last_seen", "updated_at")
    list_filter = ("is_online",)
    search_fields = ("user__username",)
