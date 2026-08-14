"""
Core permission classes for API access control.
"""
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticatedOrReadOnly

# Re-export a project-scoped name for convenience and to keep this module useful
IsAuthenticatedOrReadOnlyPermission = IsAuthenticatedOrReadOnly


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow owners of an object to edit it.
    
    Assumes the model instance has a `user` attribute.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        return obj.user == request.user


class IsVerifiedUser(permissions.BasePermission):
    """
    Permission to only allow verified users (email or phone).
    
    Useful for sensitive operations that require account verification.
    """

    message = "You must verify your email or phone number to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow if either email or phone is verified
        return request.user.is_email_verified or request.user.is_phone_verified
