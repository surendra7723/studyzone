from core.serializers import BaseModelSerializer

from .models import Notification, PushSubscription


class NotificationSerializer(BaseModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient",
            "actor",
            "verb",
            "read",
            "is_deleted",
            "target",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PushSubscriptionSerializer(BaseModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ["id", "endpoint", "p256dh", "auth", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]
