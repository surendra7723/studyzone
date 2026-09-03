from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, PushSubscriptionView

app_name = "notifications"

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
    path("push-subscriptions/", PushSubscriptionView.as_view(), name="push-subscription"),
]
