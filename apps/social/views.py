from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FriendRequest, FriendRequestStatus, Friendship, UserPresenceState
from .serializers import (
    FriendRequestCreateSerializer,
    FriendRequestSerializer,
    FriendshipSerializer,
    PresenceSnapshotSerializer,
    SocialUserSummarySerializer,
)
from .services import (
    accept_friend_request,
    broadcast_friend_request_event,
    cancel_friend_request,
    decline_friend_request,
    get_friend_snapshot_queryset,
    get_friend_user_ids,
)

User = get_user_model()


class FriendRequestListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        requests = FriendRequest.objects.select_related("sender", "receiver").filter(
            sender=request.user
        ) | FriendRequest.objects.select_related("sender", "receiver").filter(receiver=request.user)
        return Response(FriendRequestSerializer(requests.distinct(), many=True, context={"request": request}).data)

    def post(self, request):
        serializer = FriendRequestCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        friend_request = serializer.save()
        broadcast_friend_request_event(friend_request, "friend.request.created")
        return Response(FriendRequestSerializer(friend_request, context={"request": request}).data, status=status.HTTP_201_CREATED)


class IncomingFriendRequestListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        requests = FriendRequest.objects.select_related("sender", "receiver").filter(
            receiver=request.user,
            status=FriendRequestStatus.PENDING,
        )
        return Response(FriendRequestSerializer(requests, many=True, context={"request": request}).data)


class OutgoingFriendRequestListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        requests = FriendRequest.objects.select_related("sender", "receiver").filter(
            sender=request.user,
            status=FriendRequestStatus.PENDING,
        )
        return Response(FriendRequestSerializer(requests, many=True, context={"request": request}).data)


class FriendRequestAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        friend_request = get_object_or_404(FriendRequest, pk=pk, receiver=request.user)
        if not friend_request.is_pending:
            return Response({"detail": "Friend request is not pending."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            friendship = accept_friend_request(friend_request)
        return Response(FriendshipSerializer(friendship, context={"request": request}).data)


class FriendRequestDeclineView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        friend_request = get_object_or_404(FriendRequest, pk=pk, receiver=request.user)
        if not friend_request.is_pending:
            return Response({"detail": "Friend request is not pending."}, status=status.HTTP_400_BAD_REQUEST)
        decline_friend_request(friend_request)
        return Response(FriendRequestSerializer(friend_request, context={"request": request}).data)


class FriendRequestCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        friend_request = get_object_or_404(FriendRequest, pk=pk, sender=request.user)
        if not friend_request.is_pending:
            return Response({"detail": "Friend request is not pending."}, status=status.HTTP_400_BAD_REQUEST)
        cancel_friend_request(friend_request)
        return Response(FriendRequestSerializer(friend_request, context={"request": request}).data)


class FriendListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        friends = get_friend_snapshot_queryset(request.user)
        return Response(SocialUserSummarySerializer(friends, many=True, context={"request": request}).data)


class PresenceSnapshotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        friends = get_friend_snapshot_queryset(request.user)
        states = UserPresenceState.objects.select_related("user", "user__profile").filter(user__in=friends)
        return Response(PresenceSnapshotSerializer(states, many=True, context={"request": request}).data)
