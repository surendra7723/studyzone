"""Integration tests for Ambience features.

Tests ambience tracks and categories for focus sessions.
"""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.ambience.models import Category as AmbienceCategory, AmbienceTrack


pytestmark = pytest.mark.integration


class TestAmbienceTrackIntegration:
    """Test ambience track listing and filtering."""
    
    def test_list_active_tracks(self, api_client, ambience_track):
        """Active tracks are publicly listed."""
        url = reverse('ambience:track-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        track_names = [t['name'] for t in response.data['results']]
        assert ambience_track.name in track_names
    
    def test_inactive_tracks_excluded(self, api_client, inactive_ambience_track):
        """Inactive tracks are not listed."""
        url = reverse('ambience:track-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        track_names = [t['name'] for t in response.data['results']]
        assert inactive_ambience_track.name not in track_names
    
    def test_filter_tracks_by_category(self, api_client, ambience_track, ambience_category):
        """Tracks can be filtered by category."""
        url = reverse('ambience:track-list')
        response = api_client.get(url, {'category': ambience_category.name})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_unauthenticated_access_allowed(self, api_client):
        """Ambience endpoints are public."""
        url = reverse('ambience:track-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK


class TestAmbienceCategoryIntegration:
    """Test ambience category listing."""
    
    def test_list_categories(self, api_client, ambience_category):
        """Categories are publicly listed."""
        url = reverse('ambience:category-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        category_names = [c['name'] for c in response.data['results']]
        assert ambience_category.name in category_names


# Fixture for inactive track
@pytest.fixture
def inactive_ambience_track(ambience_category):
    """Create an inactive ambience track."""
    return AmbienceTrack.objects.create(
        name='Old Sounds',
        category=ambience_category,
        duration_seconds=200,
        is_active=False
    )
