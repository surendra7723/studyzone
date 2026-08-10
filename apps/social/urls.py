from django.urls import path

from .views import (
    FriendListView,
    FriendRequestAcceptView,
    FriendRequestCancelView,
    FriendRequestDeclineView,
    FriendRequestListCreateView,
    IncomingFriendRequestListView,
    OutgoingFriendRequestListView,
    PresenceSnapshotView,
)

urlpatterns = [
    path("friends/", FriendListView.as_view(), name="social-friends"),
    path("presence/", PresenceSnapshotView.as_view(), name="social-presence"),
    path("friend-requests/", FriendRequestListCreateView.as_view(), name="social-friend-requests"),
    path("friend-requests/incoming/", IncomingFriendRequestListView.as_view(), name="social-friend-requests-incoming"),
    path("friend-requests/outgoing/", OutgoingFriendRequestListView.as_view(), name="social-friend-requests-outgoing"),
    path("friend-requests/<int:pk>/accept/", FriendRequestAcceptView.as_view(), name="social-friend-request-accept"),
    path("friend-requests/<int:pk>/decline/", FriendRequestDeclineView.as_view(), name="social-friend-request-decline"),
    path("friend-requests/<int:pk>/cancel/", FriendRequestCancelView.as_view(), name="social-friend-request-cancel"),
]
