import json
import os
from datetime import timedelta

import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import FriendRequest, FriendRequestStatus, Friendship, UserPresenceState

User = get_user_model()

PRESENCE_KEY_PREFIX = "studyzone:presence:online"
PRESENCE_TTL_SECONDS = int(getattr(settings, "SOCIAL_PRESENCE_TTL_SECONDS", 90))


def get_presence_redis_url():
    return getattr(
        settings,
        "SOCIAL_PRESENCE_REDIS_URL",
        getattr(settings, "CELERY_BROKER_URL", os.getenv("SOCIAL_PRESENCE_REDIS_URL", "redis://localhost:6379/0")),
    )


def get_presence_client():
    return redis.Redis.from_url(get_presence_redis_url(), decode_responses=True)


def presence_cache_key(user_id):
    return f"{PRESENCE_KEY_PREFIX}:{user_id}"


def presence_group_name(user_id):
    return f"social.user.{user_id}"


def get_friend_user_ids(user):
    friendships = Friendship.objects.filter(
        user_low=user,
    ).values_list("user_high_id", flat=True)
    reverse_friendships = Friendship.objects.filter(
        user_high=user,
    ).values_list("user_low_id", flat=True)
    return list(friendships) + list(reverse_friendships)


def get_online_friend_ids(user):
    client = get_presence_client()
    friend_ids = get_friend_user_ids(user)
    if not friend_ids:
        return []
    keys = [presence_cache_key(friend_id) for friend_id in friend_ids]
    online_keys = client.exists(*keys) if keys else 0
    if not online_keys:
        return []
    return [friend_id for friend_id in friend_ids if client.exists(presence_cache_key(friend_id))]


def get_friend_snapshot_queryset(user):
    friend_ids = get_friend_user_ids(user)
    if not friend_ids:
        return User.objects.none()
    return User.objects.filter(id__in=friend_ids).select_related("profile", "presence_state")


def ensure_presence_state(user):
    state, _ = UserPresenceState.objects.get_or_create(user=user)
    return state


def mark_user_online(user):
    client = get_presence_client()
    state = ensure_presence_state(user)
    previous_online = state.is_online
    client.setex(presence_cache_key(user.id), PRESENCE_TTL_SECONDS, timezone.now().isoformat())
    if not previous_online:
        state.is_online = True
        state.save(update_fields=["is_online", "updated_at"])
    return not previous_online


def refresh_user_presence(user):
    client = get_presence_client()
    client.setex(presence_cache_key(user.id), PRESENCE_TTL_SECONDS, timezone.now().isoformat())
    state = ensure_presence_state(user)
    if not state.is_online:
        state.is_online = True
        state.save(update_fields=["is_online", "updated_at"])
    return state


def mark_user_offline(user, seen_at=None):
    client = get_presence_client()
    client.delete(presence_cache_key(user.id))
    state = ensure_presence_state(user)
    was_online = state.is_online
    state.is_online = False
    state.last_seen = seen_at or timezone.now()
    state.save(update_fields=["is_online", "last_seen", "updated_at"])
    return was_online


def maybe_mark_stale_presence_offline(user):
    client = get_presence_client()
    if client.exists(presence_cache_key(user.id)):
        return False
    state = ensure_presence_state(user)
    if state.is_online:
        mark_user_offline(user)
        return True
    return False


def broadcast_to_user(user_id, payload):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        presence_group_name(user_id),
        {"type": "social.event", "payload": payload},
    )


def broadcast_to_friends(user, payload):
    for friend_id in get_friend_user_ids(user):
        broadcast_to_user(friend_id, payload)


def broadcast_presence_change(user, is_online):
    state = UserPresenceState.objects.filter(user=user).first()
    payload = {
        "event": "presence.changed",
        "user_id": user.id,
        "username": user.username,
        "is_online": is_online,
        "last_seen": state.last_seen if state else None,
    }
    broadcast_to_friends(user, payload)


def broadcast_friend_request_event(friend_request, event_name):
    payload = {
        "event": event_name,
        "friend_request_id": friend_request.id,
        "sender_id": friend_request.sender_id,
        "receiver_id": friend_request.receiver_id,
        "status": friend_request.status,
    }
    broadcast_to_user(friend_request.receiver_id, payload)
    broadcast_to_user(friend_request.sender_id, payload)


def accept_friend_request(friend_request):
    friend_request.mark_responded(FriendRequestStatus.ACCEPTED)
    friendship = Friendship.create_for_users(
        friend_request.sender,
        friend_request.receiver,
        accepted_request=friend_request,
    )
    broadcast_friend_request_event(friend_request, "friend.request.accepted")
    return friendship


def decline_friend_request(friend_request):
    friend_request.mark_responded(FriendRequestStatus.DECLINED)
    broadcast_friend_request_event(friend_request, "friend.request.declined")
    return friend_request


def cancel_friend_request(friend_request):
    friend_request.mark_responded(FriendRequestStatus.CANCELLED)
    broadcast_friend_request_event(friend_request, "friend.request.cancelled")
    return friend_request
