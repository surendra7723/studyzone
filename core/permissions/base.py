
from rest_framework import permissions


class IsNotDeleted(permissions.BasePermission):
    message = "Your account has been deactivated."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and not user.is_deleted)


class IsAuthenticatedAndActive(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return not request.user.is_deleted


class IsOwner(permissions.BasePermission):
    message = "You must be the owner of this object."

    def has_object_permission(self, request, view, obj):
        owner = None
        if hasattr(obj, "get_owner"):
            owner = obj.get_owner()
        elif hasattr(obj, "user"):
            owner = obj.user
        elif isinstance(obj, type(request.user)) and obj == request.user:
            owner = request.user
        return owner == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    message = "You do not have permission to modify this object."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = None
        if hasattr(obj, "get_owner"):
            owner = obj.get_owner()
        elif hasattr(obj, "user"):
            owner = obj.user
        elif isinstance(obj, type(request.user)) and obj == request.user:
            owner = request.user
        return owner == request.user
