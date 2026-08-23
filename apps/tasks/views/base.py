"""
Task management views with full CRUD operations.
"""
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import filters, status
from rest_framework.decorators import action

from rest_framework.response import Response

from core.views import UserScopedViewSet, BulkOperationsViewSet
from core.permissions import IsAuthenticatedAndActive, IsOwnerOrReadOnly
from ..models import Task, Category
from ..serializers import TaskSerializer, CategorySerializer



@extend_schema_view(
    list=extend_schema(
        summary="List all tasks",
        description="Returns all tasks for the authenticated user with optional filtering and search",
        tags=["Tasks"],
        parameters=[
            OpenApiParameter(name="category", description="Filter by category ID", required=False, type=int),
            OpenApiParameter(name="priority", description="Filter by priority (1=Low, 2=Medium, 3=High)", required=False, type=int),
            OpenApiParameter(name="is_completed", description="Filter by completion status", required=False, type=bool),
            OpenApiParameter(name="search", description="Search in task title and description", required=False, type=str),
            OpenApiParameter(name="ordering", description="Order by field (prefix with - for descending)", required=False, type=str),
        ],
    ),
    create=extend_schema(summary="Create a new task", description="Create a new task for the authenticated user", tags=["Tasks"]),
    retrieve=extend_schema(summary="Get task details", description="Retrieve details of a specific task", tags=["Tasks"]),
    update=extend_schema(summary="Update a task", description="Update all fields of a task", tags=["Tasks"]),
    partial_update=extend_schema(summary="Partially update a task", description="Update specific fields of a task", tags=["Tasks"]),
    destroy=extend_schema(summary="Delete a task", description="Delete a task permanently", tags=["Tasks"]),
)
class TaskViewSet(BulkOperationsViewSet):
    """
    Full CRUD operations for task management.
    
    Supports filtering, searching, sorting, and bulk operations.
    """
    
    queryset = Task.objects.select_related('category', 'user').all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticatedAndActive, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'priority', 'is_completed']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']

    @extend_schema(summary="Mark task as completed", description="Toggle task completion status", tags=["Tasks"])
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a task as completed."""
        task = self.get_object()
        task.is_completed = True
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data)

    @extend_schema(summary="Mark task as incomplete", description="Mark a completed task as incomplete", tags=["Tasks"])
    @action(detail=True, methods=['post'])
    def uncomplete(self, request, pk=None):
        """Mark a task as incomplete."""
        task = self.get_object()
        task.is_completed = False
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data)

    @extend_schema(summary="Get task statistics", description="Get statistics about user's tasks", tags=["Tasks"])
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get task statistics for the current user."""
        queryset = self.get_queryset()
        
        total_tasks = queryset.count()
        completed_tasks = queryset.filter(is_completed=True).count()
        pending_tasks = queryset.filter(is_completed=False).count()
        high_priority = queryset.filter(priority=3, is_completed=False).count()
        overdue_tasks = queryset.filter(is_completed=False, due_date__lt=timezone.now()).count() if Task._meta.get_field('due_date') else 0
        
        return Response({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'high_priority_pending': high_priority,
            'overdue_tasks': overdue_tasks,
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        })



@extend_schema_view(
    list=extend_schema(summary="List all categories", description="Returns all categories for the authenticated user", tags=["Tasks - Categories"]),
    create=extend_schema(summary="Create a new category", description="Create a new task category", tags=["Tasks - Categories"]),
    retrieve=extend_schema(summary="Get category details", description="Retrieve details of a specific category", tags=["Tasks - Categories"]),
    update=extend_schema(summary="Update a category", description="Update all fields of a category", tags=["Tasks - Categories"]),
    partial_update=extend_schema(summary="Partially update a category", description="Update specific fields of a category", tags=["Tasks - Categories"]),
    destroy=extend_schema(summary="Delete a category", description="Delete a category (tasks will have category set to null)", tags=["Tasks - Categories"]),
)
class CategoryViewSet(UserScopedViewSet):
    """Manage task categories."""
    
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedAndActive, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @extend_schema(summary="Get category task count", description="Get the number of tasks in this category", tags=["Tasks - Categories"])
    @action(detail=True, methods=['get'])
    def task_count(self, request, pk=None):
        """Get the number of tasks in this category."""
        category = self.get_object()
        total = category.tasks.count()
        completed = category.tasks.filter(is_completed=True).count()
        pending = category.tasks.filter(is_completed=False).count()
        
        return Response({
            'category_id': category.id,
            'category_name': category.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'pending_tasks': pending,
        })


    ordering = ['-created_at']

