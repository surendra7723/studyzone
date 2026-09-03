from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import SoftDeleteMixin, PaginationMixin, UserFilterMixin
from core.permissions import IsOwnerOrReadOnly
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)

from .models import Notification, PushSubscription
from .serializers import NotificationSerializer, PushSubscriptionSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List notifications",
        description="Returns notifications for the authenticated user",
        tags=["Notifications"],
        parameters=[
            OpenApiParameter(
                name="read",
                description="Filter by read status",
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
        summary="Create a notification",
        description="Create a notification (admin/system action)",
        tags=["Notifications"],
    ),
    retrieve=extend_schema(
        summary="Get notification details",
        description="Retrieve details of a specific notification",
        tags=["Notifications"],
    ),
    update=extend_schema(
        summary="Update a notification",
        description="Update a notification",
        tags=["Notifications"],
    ),
    partial_update=extend_schema(
        summary="Partially update a notification",
        description="Partially update a notification",
        tags=["Notifications"],
    ),
    destroy=extend_schema(
        summary="Delete a notification",
        description="Soft delete a notification",
        tags=["Notifications"],
    ),
)
class NotificationViewSet(SoftDeleteMixin, PaginationMixin, UserFilterMixin, ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["read"]

    def perform_create(self, serializer):
        serializer.save(recipient=self.request.user)

    @extend_schema(
        summary="Mark notification as read",
        description="Mark a notification as read",
        tags=["Notifications"],
    )
    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response(self.get_serializer(notification).data)

    @extend_schema(
        summary="Mark all notifications as read",
        description="Mark all user's notifications as read",
        tags=["Notifications"],
    )
    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = Notification.objects.filter(
            recipient=request.user, read=False, is_deleted=False
        ).update(read=True)
        return Response({"updated": updated})

    @extend_schema(
        summary="Get unread notification count",
        description=(
            "Get the number of unread notifications for the current user"
        ),
        tags=["Notifications"],
    )
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = Notification.objects.filter(
            recipient=request.user, read=False, is_deleted=False
        ).count()
        return Response({"unread_count": count})

    @extend_schema(
        summary="Bulk mark as read",
        description="Mark multiple notifications as read",
        tags=["Notifications"],
    )
    @action(detail=False, methods=["post"], url_path="bulk-mark-read")
    def bulk_mark_read(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list):
            return Response(
                {"detail": "Expected 'ids' to be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = Notification.objects.filter(
            recipient=request.user, id__in=ids, is_deleted=False
        ).update(read=True)
        return Response({"updated": updated})


class PushSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Subscribe to push notifications",
        description="Register a browser push subscription for the authenticated user",
        tags=["Notifications - Push"],
        request=PushSubscriptionSerializer,
        responses={status.HTTP_201_CREATED: PushSubscriptionSerializer},
    )
    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription, _ = PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=serializer.validated_data["endpoint"],
            defaults={
                "p256dh": serializer.validated_data["p256dh"],
                "auth": serializer.validated_data["auth"],
                "is_active": True,
            },
        )
        return Response(
            PushSubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Unsubscribe from push notifications",
        description="Deactivate a browser push subscription for the authenticated user",
        tags=["Notifications - Push"],
        request=PushSubscriptionSerializer,
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def delete(self, request):
        endpoint = request.data.get("endpoint")
        if not endpoint:
            return Response(
                {"detail": "Expected 'endpoint' in request body."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        PushSubscription.objects.filter(
            user=request.user, endpoint=endpoint
        ).update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
