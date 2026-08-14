"""
Social features views: Friend requests, friendships, and presence tracking.
"""
from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsFriendOrSelf
from .models import FriendRequest, FriendRequestStatus, Friendship, UserPresenceState
from .serializers import (
    FriendRequestCreateSerializer,
    FriendRequestSerializer,
    FriendshipSerializer,
    PresenceSnapshotSerializer,
)
from .services import (
    accept_friend_request,
    broadcast_friend_request_event,
    cancel_friend_request,
    decline_friend_request,
    get_friend_snapshot_queryset,
)


@extend_schema_view(
    list=extend_schema(summary="List all friend requests", tags=["Social - Friends"]),
    create=extend_schema(summary="Send friend request", tags=["Social - Friends"]),
)
class FriendRequestViewSet(viewsets.ModelViewSet):
    """Manage friend requests with full CRUD operations."""

    serializer_class = FriendRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get all friend requests for the current user (sent and received)."""
        user = self.request.user
        return FriendRequest.objects.select_related(
            "sender", "receiver"
        ).filter(
            Q(sender=user) | Q(receiver=user)
        ).distinct()

    def get_serializer_class(self):
        """Use CreateSerializer for create actions."""
        if self.action == 'create':
            return FriendRequestCreateSerializer
        return FriendRequestSerializer

    def perform_create(self, serializer):
        """Create friend request and broadcast event."""
        friend_request = serializer.save()
        broadcast_friend_request_event(friend_request, "friend.request.created")

    @extend_schema(summary="Get incoming friend requests", tags=["Social - Friends"])
    @action(detail=False, methods=['get'])
    def incoming(self, request):
        """Get incoming friend requests."""
        requests = FriendRequest.objects.select_related(
            "sender", "receiver"
        ).filter(
            receiver=request.user,
            status=FriendRequestStatus.PENDING,
        )
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Get outgoing friend requests", tags=["Social - Friends"])
    @action(detail=False, methods=['get'])
    def outgoing(self, request):
        """Get outgoing friend requests."""
        requests = FriendRequest.objects.select_related(
            "sender", "receiver"
        ).filter(
            sender=request.user,
            status=FriendRequestStatus.PENDING,
        )
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Accept friend request", tags=["Social - Friends"])
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a friend request."""
        friend_request = self.get_object()
        if friend_request.receiver != request.user:
            return Response(
                {"detail": "You can only accept requests sent to you."},
                status=status.HTTP_403_FORBIDDEN
            )
        if not friend_request.is_pending:
            return Response(
                {"detail": "Friend request is not pending."},
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            friendship = accept_friend_request(friend_request)
        return Response(
            FriendshipSerializer(friendship, context={"request": request}).data
        )

    @extend_schema(summary="Decline friend request", tags=["Social - Friends"])
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline a friend request."""
        friend_request = self.get_object()
        if friend_request.receiver != request.user:
            return Response(
                {"detail": "You can only decline requests sent to you."},
                status=status.HTTP_403_FORBIDDEN
            )
        if not friend_request.is_pending:
            return Response(
                {"detail": "Friend request is not pending."},
                status=status.HTTP_400_BAD_REQUEST
            )
        decline_friend_request(friend_request)
        return Response(self.get_serializer(friend_request).data)

    @extend_schema(summary="Cancel friend request", tags=["Social - Friends"])
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an outgoing friend request."""
        friend_request = self.get_object()
        if friend_request.sender != request.user:
            return Response(
                {"detail": "You can only cancel requests you sent."},
                status=status.HTTP_403_FORBIDDEN
            )
        if not friend_request.is_pending:
            return Response(
                {"detail": "Friend request is not pending."},
                status=status.HTTP_400_BAD_REQUEST
            )
        cancel_friend_request(friend_request)
        return Response(self.get_serializer(friend_request).data)


@extend_schema_view(
    list=extend_schema(summary="List all friendships", tags=["Social - Friends"]),
)
class FriendshipViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to user friendships."""

    serializer_class = FriendshipSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get all friendships for the current user."""
        user = self.request.user
        return Friendship.objects.select_related(
            "user_low__profile", "user_high__profile"
        ).filter(
            Q(user_low=user) | Q(user_high=user)
        )


@extend_schema_view(
    list=extend_schema(summary="Get presence snapshot", tags=["Social - Presence"]),
)
class PresenceViewSet(viewsets.ReadOnlyModelViewSet):
    """Real-time presence tracking for friends."""

    serializer_class = PresenceSnapshotSerializer
    permission_classes = [IsAuthenticated, IsFriendOrSelf]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['last_seen']
    ordering = ['-last_seen']

    def get_queryset(self):
        """Get presence states for the user's friends."""
        user = self.request.user
        friends = get_friend_snapshot_queryset(user)
        return UserPresenceState.objects.select_related(
            "user", "user__profile"
        ).filter(user__in=friends)
