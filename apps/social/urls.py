from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FriendRequestViewSet, FriendshipViewSet, PresenceViewSet

app_name = "social"

router = DefaultRouter()
router.register(r'friend-requests', FriendRequestViewSet, basename='friend-request')
router.register(r'friendships', FriendshipViewSet, basename='friendship')
router.register(r'presence', PresenceViewSet, basename='presence')

urlpatterns = [
    path('', include(router.urls)),
]

