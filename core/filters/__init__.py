"""
Custom filter backends for API filtering.
"""
from rest_framework import filters


class UserFilterBackend(filters.BaseFilterBackend):
    """
    Filter that only allows users to see their own objects.
    
    Automatically filters queryset by request.user.
    """

    def filter_queryset(self, request, queryset, view):
        """Filter queryset to only include objects owned by the current user."""
        if hasattr(queryset.model, "user"):
            return queryset.filter(user=request.user)
        return queryset
