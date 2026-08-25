
from rest_framework import permissions


class IsFriendOrSelf(permissions.BasePermission):
    message = "You can only access your own data or your friends' data."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user

        if hasattr(obj, "user"):
            target_user = obj.user
        else:
            target_user = obj

        if target_user == user:
            return True

        cache = getattr(request, "_friend_cache", None)
        if cache is None:
            cache = {}
            request._friend_cache = cache

        low_id, high_id = sorted((user.id, target_user.id))
        key = (low_id, high_id)
        if key not in cache:
            from apps.social.models import Friendship

            cache[key] = Friendship.objects.filter(
                user_low=low_id, user_high=high_id
            ).exists()

        return cache[key]
