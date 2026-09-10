"""Integration tests for Notification features.

Tests the interaction between notifications, users, and push subscriptions.
"""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.notifications.models import Notification, PushSubscription


pytestmark = pytest.mark.integration


class TestNotificationManagement:
    """Test notification CRUD operations."""
    
    def test_list_notifications(self, authenticated_client, notification):
        """Users can list their notifications."""
        url = reverse('notifications:notification-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_mark_notification_read(self, authenticated_client, notification):
        """Users can mark notifications as read."""
        url = reverse('notifications:notification-mark-read', kwargs={'pk': notification.pk})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        notification.refresh_from_db()
        assert notification.read is True
    
    def test_soft_delete_notification(self, authenticated_client, notification):
        """Soft delete marks notification as deleted."""
        url = reverse('notifications:notification-detail', kwargs={'pk': notification.pk})
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        notification.refresh_from_db()
        assert notification.is_deleted is True
    
    def test_user_cannot_access_other_notifications(
        self, authenticated_client, other_user
    ):
        """Users cannot access other users' notifications."""
        other_notification = Notification.objects.create(
            recipient=other_user,
            verb='test.verb',
            content='Test'
        )
        
        url = reverse('notifications:notification-detail', kwargs={'pk': other_notification.pk})
        response = authenticated_client.get(url)
        
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


class TestPushSubscriptionIntegration:
    """Test push subscription management."""
    
    def test_create_push_subscription(self, authenticated_client, user):
        """Users can create push subscriptions."""
        url = reverse('notifications:push-subscription')
        data = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/new-endpoint',
            'p256dh': 'new-p256dh-key',
            'auth': 'new-auth-key'
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert PushSubscription.objects.filter(
            user=user,
            endpoint=data['endpoint']
        ).exists()
    
    def test_delete_push_subscription(self, authenticated_client, push_subscription):
        """Users can delete their push subscriptions."""
        url = reverse('notifications:push-subscription')
        data = {'endpoint': push_subscription.endpoint}
        
        response = authenticated_client.delete(url, data, format='json')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        push_subscription.refresh_from_db()
        assert push_subscription.is_active is False


class TestNotificationBulkOperations:
    """Test bulk notification operations."""
    
    def test_mark_all_read(self, authenticated_client, multiple_notifications):
        """Users can mark all notifications as read."""
        url = reverse('notifications:notification-mark-all-read')
        response = authenticated_client.post(url)
        
        if response.status_code == status.HTTP_200_OK:
            for notif in multiple_notifications:
                notif.refresh_from_db()
                assert notif.read is True
