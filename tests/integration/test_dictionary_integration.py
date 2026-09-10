"""Integration tests for Dictionary features.

Tests word lookup, search history, and word entries.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch

from dictionary_app.models import SearchHistory, WordEntry


pytestmark = pytest.mark.integration


class TestDictionaryLookupIntegration:
    """Test word lookup with external API."""
    
    def test_lookup_word_success(self, authenticated_client):
        """Looking up a word calls the external dictionary API."""
        mock_response = [{
            'word': 'test',
            'meanings': [{'partOfSpeech': 'noun', 'definitions': [{'definition': 'Test'}]}]
        }]
        
        with patch('dictionary_app.views.ExternalDictionaryService.fetch_word_data') as mock_fetch:
            mock_fetch.return_value = mock_response
            
            url = reverse('dictionary:dict-lookup', kwargs={'word': 'test'})
            response = authenticated_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
    
    def test_lookup_word_not_found(self, authenticated_client):
        """Lookup returns 404 for non-existent words."""
        with patch('dictionary_app.views.ExternalDictionaryService.fetch_word_data') as mock_fetch:
            mock_fetch.return_value = None
            
            url = reverse('dictionary:dict-lookup', kwargs={'word': 'nonexistent'})
            response = authenticated_client.get(url)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSearchHistoryIntegration:
    """Test search history management."""
    
    def test_list_search_history(self, authenticated_client, search_history):
        """Users can list their search history."""
        url = reverse('dictionary:search-history-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_clear_search_history(self, authenticated_client, search_history):
        """Users can clear their search history."""
        url = reverse('dictionary:search-history-clear-history')
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestWordEntryIntegration:
    """Test word entry (notes/bookmarks) management."""
    
    def test_create_word_entry_note(self, authenticated_client, user):
        """Users can create word entry notes."""
        url = reverse('dictionary:word-entry-list')
        data = {'word': 'ephemeral', 'entry_type': 'note'}
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_create_word_entry_bookmark(self, authenticated_client, user):
        """Users can bookmark words."""
        url = reverse('dictionary:word-entry-list')
        data = {'word': 'serendipity', 'entry_type': 'bookmark', 'custom_note': 'A happy coincidence'}
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_unique_entry_per_type(self, authenticated_client, user):
        """Cannot create duplicate entry for same word and type."""
        WordEntry.objects.create(user=user, word='test', entry_type='note')
        
        url = reverse('dictionary:word-entry-list')
        data = {'word': 'test', 'entry_type': 'note'}
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_list_word_entries(self, authenticated_client, word_entry_note):
        """Users can list their word entries."""
        url = reverse('dictionary:word-entry-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_delete_word_entry(self, authenticated_client, word_entry_note):
        """Users can delete their word entries."""
        url = reverse('dictionary:word-entry-detail', kwargs={'pk': word_entry_note.pk})
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
