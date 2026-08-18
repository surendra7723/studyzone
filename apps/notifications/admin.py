from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "recipient",
        "actor",
        "verb",
        "read",
        "is_deleted",
        "created_at",
    ]
    list_filter = ["read", "is_deleted", "verb", "created_at"]
    search_fields = [
        "recipient__username",
        "actor__username",
        "verb",
        "content",
    ]
