from django.contrib import admin

from .models import AmbienceTrack, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(AmbienceTrack)
class AmbienceTrackAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "duration_seconds", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name"]
