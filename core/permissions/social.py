"""
Social-specific permission classes.
"""
from rest_framework import permissions
from django.db.models import Q


class IsFriendOrSelf(permissions.BasePermission):
    """
    Permission to only allow access to friends or self.
    
    Used for social features like viewing presence, profiles, etc.
    """

    message = "You can only access your own data or your friends' data."

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check if the user is accessing their own data or a friend's data.
        
        Assumes obj has a 'user' attribute or is a User instance.
        """
        user = request.user
        
        # If obj is the user themselves
        if hasattr(obj, 'user'):
            target_user = obj.user
        else:
            target_user = obj
        
        # Allow access to own data
        if target_user == user:
            return True
        
        # Check if they are friends
        from apps.social.models import Friendship
        
        friendship_exists = Friendship.objects.filter(
            Q(user_low=user, user_high=target_user) |
            Q(user_low=target_user, user_high=user)
        ).exists()
        
        return friendship_exists
