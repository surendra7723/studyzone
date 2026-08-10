from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from .models import FriendRequest, FriendRequestStatus, Friendship, UserPresenceState
from .services import get_friend_user_ids, get_online_friend_ids

User = get_user_model()


class SocialUserSummarySerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "avatar_url", "is_online", "last_seen")

    def get_avatar_url(self, obj):
        profile = getattr(obj, "profile", None)
        picture = getattr(profile, "profile_picture", None)
        if picture and hasattr(picture, "url"):
            return picture.url
        return None

    def get_is_online(self, obj):
        presence = getattr(obj, "presence_state", None)
        return bool(presence and presence.is_online)

    def get_last_seen(self, obj):
        presence = getattr(obj, "presence_state", None)
        return presence.last_seen if presence else None


class FriendshipSerializer(serializers.ModelSerializer):
    friend = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ("id", "friend", "created_at")

    def get_friend(self, obj):
        request_user = self.context["request"].user
        return SocialUserSummarySerializer(obj.other_user(request_user), context=self.context).data


class FriendRequestSerializer(serializers.ModelSerializer):
    sender = SocialUserSummarySerializer(read_only=True)
    receiver = SocialUserSummarySerializer(read_only=True)

    class Meta:
        model = FriendRequest
        fields = (
            "id",
            "sender",
            "receiver",
            "status",
            "responded_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class FriendRequestCreateSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField(required=False)
    receiver_username = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs):
        request_user = self.context["request"].user
        receiver = None

        receiver_id = attrs.get("receiver_id")
        receiver_username = attrs.get("receiver_username")
        if receiver_id is None and not receiver_username:
            raise serializers.ValidationError(
                {"receiver": "Provide receiver_id or receiver_username."}
            )

        if receiver_id is not None:
            receiver = User.objects.filter(pk=receiver_id).first()
        elif receiver_username:
            receiver = User.objects.filter(username__iexact=receiver_username.strip()).first()

        if not receiver:
            raise serializers.ValidationError({"receiver": "Recipient not found."})
        if receiver.pk == request_user.pk:
            raise serializers.ValidationError({"receiver": "You cannot friend yourself."})

        existing_friend_ids = set(get_friend_user_ids(request_user))
        if receiver.pk in existing_friend_ids:
            raise serializers.ValidationError({"receiver": "You are already friends."})

        duplicate_pending = FriendRequest.objects.filter(
            Q(sender=request_user, receiver=receiver, status=FriendRequestStatus.PENDING)
            | Q(sender=receiver, receiver=request_user, status=FriendRequestStatus.PENDING)
        ).exists()
        if duplicate_pending:
            raise serializers.ValidationError({"receiver": "A pending request already exists."})

        attrs["receiver"] = receiver
        return attrs

    def create(self, validated_data):
        request_user = self.context["request"].user
        friend_request = FriendRequest.objects.create(
            sender=request_user,
            receiver=validated_data["receiver"],
        )
        return friend_request


class PresenceSnapshotSerializer(serializers.ModelSerializer):
    user = SocialUserSummarySerializer(read_only=True)

    class Meta:
        model = UserPresenceState
        fields = ("user", "is_online", "last_seen", "updated_at")


class FriendRequestActionSerializer(serializers.Serializer):
    request_id = serializers.IntegerField()

    def validate_request_id(self, value):
        friend_request = FriendRequest.objects.filter(pk=value).select_related("sender", "receiver").first()
        if not friend_request:
            raise serializers.ValidationError("Friend request not found.")
        self.context["friend_request"] = friend_request
        return value
