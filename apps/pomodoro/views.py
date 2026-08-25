from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)

from core.mixins import PaginationMixin
from .models import PomodoroSession, Goal
from .serializers import PomodoroSessionSerializer, GoalSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List pomodoro sessions",
        description="Returns all pomodoro sessions for the authenticated user",
        tags=["Pomodoro - Sessions"],
    ),
    create=extend_schema(
        summary="Create a pomodoro session",
        description="Create a new pomodoro session",
        tags=["Pomodoro - Sessions"],
    ),
    retrieve=extend_schema(
        summary="Get pomodoro session details",
        description="Retrieve details of a specific pomodoro session",
        tags=["Pomodoro - Sessions"],
    ),
    update=extend_schema(
        summary="Update a pomodoro session",
        description="Update all fields of a pomodoro session",
        tags=["Pomodoro - Sessions"],
    ),
    partial_update=extend_schema(
        summary="Partially update a pomodoro session",
        description="Update specific fields of a pomodoro session",
        tags=["Pomodoro - Sessions"],
    ),
    destroy=extend_schema(
        summary="Delete a pomodoro session",
        description="Delete a pomodoro session permanently",
        tags=["Pomodoro - Sessions"],
    ),
)
class PomodoroSessionViewSet(viewsets.ModelViewSet):
    queryset = PomodoroSession.objects.all()
    serializer_class = PomodoroSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List goals",
        description="Returns all goals for the authenticated user",
        tags=["Pomodoro - Goals"],
        parameters=[
            OpenApiParameter(
                name="is_completed",
                description="Filter by completion status",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="ordering",
                description="Order by field (prefix with - for descending)",
                required=False,
                type=str,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create a goal",
        description="Create a new goal for the authenticated user",
        tags=["Pomodoro - Goals"],
    ),
    retrieve=extend_schema(
        summary="Get goal details",
        description="Retrieve details of a specific goal",
        tags=["Pomodoro - Goals"],
    ),
    update=extend_schema(
        summary="Update a goal",
        description="Update all fields of a goal",
        tags=["Pomodoro - Goals"],
    ),
    partial_update=extend_schema(
        summary="Partially update a goal",
        description="Update specific fields of a goal",
        tags=["Pomodoro - Goals"],
    ),
    destroy=extend_schema(
        summary="Delete a goal",
        description="Delete a goal permanently",
        tags=["Pomodoro - Goals"],
    ),
)
class GoalViewSet(PaginationMixin, viewsets.ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ["target_date", "title"]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="Toggle goal completion",
        description="Toggle goal completion status",
        tags=["Pomodoro - Goals"],
    )
    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        goal = self.get_object()
        goal.is_completed = not goal.is_completed
        goal.save()
        serializer = self.get_serializer(goal)
        return Response(serializer.data)
