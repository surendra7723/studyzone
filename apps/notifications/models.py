from django.db import models
from django.contrib.auth import get_user_model

from core.models.base import TimeStampedModel

User = get_user_model()


class Notification(TimeStampedModel):
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    verb = models.CharField(
        max_length=100,
    )
    read = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    target = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "read", "created_at"]),
            models.Index(fields=["recipient", "is_deleted", "created_at"]),
        ]

    def __str__(self):
        return f"{self.verb} for {self.recipient.username}"
