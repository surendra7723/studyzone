"""
Core mixins for reusable view functionality.
"""
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination


class UserFilterMixin:
    """
    Automatically filters queryset by request.user and sets user on creation.

    Usage:
        class MyViewSet(UserFilterMixin, viewsets.ModelViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
    """

    def get_queryset(self):
        """Filter queryset to only include objects owned by the current user."""
        queryset = super().get_queryset()
        if hasattr(queryset.model, "user"):
            return queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        """Automatically set the user field on creation."""
        serializer.save(user=self.request.user)


class SoftDeleteMixin:
    """
    Implements soft delete instead of hard delete.

    Requires model to have 'is_deleted' BooleanField.

    Usage:
        class MyViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
    """

    def get_queryset(self):
        """Exclude soft-deleted objects from queryset."""
        queryset = super().get_queryset()
        if hasattr(queryset.model, "is_deleted"):
            return queryset.filter(is_deleted=False)
        return queryset

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        if hasattr(instance, "is_deleted"):
            instance.is_deleted = True
            instance.save()
        else:
            # Fallback to hard delete if model doesn't support soft delete
            instance.delete()


class TimestampMixin:
    """
    Provides automatic timestamp handling.

    Ensures updated_at is set on update operations.
    """

    def perform_update(self, serializer):
        """Set updated_at timestamp on update."""
        if hasattr(serializer.Meta.model, "updated_at"):
            serializer.save(updated_at=timezone.now())
        else:
            serializer.save()


class PaginationMixin:
    """
    Provides consistent pagination across views.

    Usage:
        class MyViewSet(PaginationMixin, viewsets.ModelViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
    """

    class StandardPagination(PageNumberPagination):
        page_size = 20
        page_size_query_param = "page_size"
        max_page_size = 100

    pagination_class = StandardPagination


class UserScopedQuerySetMixin:
    """
    Filters the viewset queryset by the current user.

    Requires the viewset's `queryset` to provide a `for_user(user)` method,
    typically via a custom QuerySet registered with QuerySet.as_manager().
    """

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        return self.queryset.for_user(self.request.user)
