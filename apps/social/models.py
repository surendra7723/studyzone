from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from core.models.base import TimeStampedModel


class FriendRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    CANCELLED = "cancelled", "Cancelled"


class Friendship(TimeStampedModel):
    user_low = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_low",
    )
    user_high = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_high",
    )
    accepted_request = models.OneToOneField(
        "FriendRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_friendship",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_low", "user_high"],
                name="uniq_friendship_pair",
            ),
            models.CheckConstraint(
                condition=Q(user_low__lt=F("user_high")),
                name="friendship_users_are_ordered",
            ),
        ]
        indexes = [
            models.Index(fields=["user_low", "user_high"]),
            models.Index(fields=["created_at"]),
        ]

    @classmethod
    def create_for_users(cls, user_a, user_b, accepted_request=None):
        if user_a.pk == user_b.pk:
            raise ValidationError({"friend": "You cannot friend yourself."})

        if user_a.pk < user_b.pk:
            user_low, user_high = user_a, user_b
        else:
            user_low, user_high = user_b, user_a
        return cls.objects.create(
            user_low=user_low,
            user_high=user_high,
            accepted_request=accepted_request,
        )

    def other_user(self, user):
        if user.pk == self.user_low_id:
            return self.user_high
        if user.pk == self.user_high_id:
            return self.user_low
        return None

    def __str__(self):
        return f"{self.user_low.username} <-> {self.user_high.username}"


class FriendRequest(TimeStampedModel):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friend_requests",
    )
    status = models.CharField(
        max_length=16,
        choices=FriendRequestStatus.choices,
        default=FriendRequestStatus.PENDING,
        db_index=True,
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "receiver"],
                name="uniq_friend_request_direction",
            ),
        ]
        indexes = [
            models.Index(fields=["receiver", "status", "created_at"]),
            models.Index(fields=["sender", "status", "created_at"]),
        ]

    def clean(self):
        if self.sender_id and self.receiver_id and self.sender_id == self.receiver_id:
            raise ValidationError({"receiver": "You cannot send a request to yourself."})

    @property
    def is_pending(self):
        return self.status == FriendRequestStatus.PENDING

    def mark_responded(self, status):
        self.status = status
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at", "updated_at"])

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"


class UserPresenceState(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="presence_state",
    )
    is_online = models.BooleanField(default=False, db_index=True)
    last_seen = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["user__username"]
        indexes = [
            models.Index(fields=["is_online", "last_seen"]),
        ]

    def mark_online(self):
        self.is_online = True
        self.save(update_fields=["is_online", "updated_at"])

    def mark_offline(self, seen_at=None):
        self.is_online = False
        self.last_seen = seen_at or timezone.now()
        self.save(update_fields=["is_online", "last_seen", "updated_at"])

    def __str__(self):
        state = "online" if self.is_online else "offline"
        return f"{self.user.username} is {state}"
