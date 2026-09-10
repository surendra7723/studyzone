"""Integration tests for Social features.

Tests the interaction between friend requests, friendships, and notifications.
"""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.social.models import FriendRequest, Friendship
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


pytestmark = pytest.mark.integration


@pytest.fixture
def other_client(other_user):
    """Authenticated client for other_user."""
    client = APIClient()
    refresh = RefreshToken.for_user(other_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


class TestFriendRequestFlow:
    """Test friend request creation, acceptance, and rejection."""
    
    @pytest.mark.skip(reason="Requires Redis for channel broadcasting")
    def test_send_friend_request(self, authenticated_client, other_user):
        """Sending a friend request creates pending request."""
        url = reverse('social:friend-request-list')
        data = {'receiver_id': other_user.id}
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.skip(reason="Requires Redis for channel broadcasting")
    def test_accept_friend_request_creates_friendship(
        self, other_client, user, other_user, friend_request
    ):
        """Accepting a request creates a Friendship."""
        url = reverse('social:friend-request-accept', kwargs={'pk': friend_request.pk})
        response = other_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert Friendship.objects.filter(
            user_low__in=[user, other_user],
            user_high__in=[user, other_user]
        ).exists()
    
    @pytest.mark.skip(reason="Requires Redis for channel broadcasting")
    def test_reject_friend_request(self, other_client, friend_request):
        """Rejecting a request updates status."""
        url = reverse('social:friend-request-decline', kwargs={'pk': friend_request.pk})
        response = other_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        friend_request.refresh_from_db()
        assert friend_request.status == 'declined'
    
    def test_cannot_send_duplicate_request(self, authenticated_client, other_user, friend_request):
        """Cannot send duplicate friend request."""
        url = reverse('social:friend-request-list')
        data = {'receiver_id': other_user.id}
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_cannot_friend_self(self, authenticated_client, user):
        """Cannot send friend request to self."""
        url = reverse('social:friend-request-list')
        data = {'receiver_id': user.id}
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestFriendshipManagement:
    """Test friendship listing and removal."""
    
    def test_list_friends(self, authenticated_client, other_user, friendship):
        """Users can list their friends."""
        url = reverse('social:friendship-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        friend_ids = [f['friend']['id'] for f in response.data]
        assert other_user.id in friend_ids
    
    @pytest.mark.skip(reason="FriendshipViewSet is read-only, delete not supported")
    def test_remove_friendship(self, authenticated_client, friendship):
        """Users can remove friendships."""
        url = reverse('social:friendship-detail', kwargs={'pk': friendship.pk})
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
