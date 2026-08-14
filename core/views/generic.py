"""
Generic reusable ViewSets with common patterns.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..mixins import UserFilterMixin, SoftDeleteMixin, TimestampMixin


class UserScopedViewSet(UserFilterMixin, TimestampMixin, viewsets.ModelViewSet):
    """
    ViewSet that automatically filters by user and handles timestamps.
    
    Perfect for user-owned resources like tasks, goals, categories.
    
    Usage:
        class TaskViewSet(UserScopedViewSet):
            queryset = Task.objects.all()
            serializer_class = TaskSerializer
            permission_classes = [IsAuthenticated]
    """

    pass


class SoftDeleteViewSet(SoftDeleteMixin, UserFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet with soft delete capability.
    
    Requires model to have 'is_deleted' BooleanField.
    
    Usage:
        class MyViewSet(SoftDeleteViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
    """

    pass


class BulkOperationsViewSet(UserFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet with bulk create, update, and delete operations.
    
    Adds three custom actions:
    - bulk_create: Create multiple instances at once
    - bulk_update: Update multiple instances at once
    - bulk_delete: Delete multiple instances at once
    """

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        """
        Create multiple instances at once.
        
        Expects a list of objects in the request body.
        
        Example:
            POST /api/tasks/bulk-create/
            [
                {"title": "Task 1", "priority": 1},
                {"title": "Task 2", "priority": 2}
            ]
        """
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["patch"], url_path="bulk-update")
    def bulk_update(self, request):
        """
        Update multiple instances at once.
        
        Expects a list of objects with 'id' field in the request body.
        
        Example:
            PATCH /api/tasks/bulk-update/
            [
                {"id": 1, "is_completed": true},
                {"id": 2, "is_completed": true}
            ]
        """
        if not isinstance(request.data, list):
            return Response(
                {"detail": "Expected a list of items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_items = []
        for item_data in request.data:
            if "id" not in item_data:
                return Response(
                    {"detail": "Each item must include an 'id' field."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance = self.get_queryset().filter(id=item_data["id"]).first()
            if not instance:
                continue

            serializer = self.get_serializer(
                instance, data=item_data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            updated_items.append(serializer.data)

        return Response(updated_items, status=status.HTTP_200_OK)

    @action(detail=False, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request):
        """
        Delete multiple instances at once.
        
        Expects a list of IDs in the request body.
        
        Example:
            DELETE /api/tasks/bulk-delete/
            {"ids": [1, 2, 3, 4, 5]}
        """
        ids = request.data.get("ids", [])
        if not isinstance(ids, list):
            return Response(
                {"detail": "Expected 'ids' to be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.count()
        queryset.delete()

        return Response(
            {"detail": f"Successfully deleted {count} items."},
            status=status.HTTP_204_NO_CONTENT,
        )
