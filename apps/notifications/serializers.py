from core.serializers import BaseModelSerializer

from .models import Notification


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
