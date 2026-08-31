from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from dictionary_app.models import SearchHistory, WordEntry

User = get_user_model()


class DictionaryLookupViewTests(TestCase):
    """Tests for the dictionary lookup API view."""

    @patch("dictionary_app.views.ExternalDictionaryService.fetch_word_data")
    def test_lookup_returns_serialized_payload(self, mock_fetch_word_data):
        """The view should return the normalized payload for a successful lookup."""
        mock_fetch_word_data.return_value = [
            {
                "word": "hello",
                "phonetic": "/həˈloʊ/",
                "meanings": [
                    {
                        "partOfSpeech": "interjection",
                        "definitions": [
                            {"definition": "Used as a greeting.", "example": "Hello, world!"}
                        ],
                    }
                ],
            }
        ]

        response = self.client.get(reverse("dictionary:dict-lookup", kwargs={"word": "hello"}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["word"], "hello")
        self.assertEqual(response.json()["phonetic"], "/həˈloʊ/")
        self.assertEqual(response.json()["meanings"][0]["partOfSpeech"], "interjection")
        self.assertEqual(response.json()["meanings"][0]["definitions"][0]["definition"], "Used as a greeting.")

    @patch("dictionary_app.views.ExternalDictionaryService.fetch_word_data")
    def test_lookup_handles_missing_word(self, mock_fetch_word_data):
        """The view should return 404 when word not found."""
        from rest_framework.exceptions import NotFound
        mock_fetch_word_data.side_effect = NotFound(detail="No dictionary entry was found for the provided word.")

        response = self.client.get(reverse("dictionary:dict-lookup", kwargs={"word": "nonexistentword123"}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("dictionary_app.views.ExternalDictionaryService.fetch_word_data")
    def test_lookup_creates_search_history_for_authenticated_user(self, mock_fetch_word_data):
        """Lookup should create search history entry for authenticated user."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        mock_fetch_word_data.return_value = [
            {"word": "hello", "phonetic": "/həˈloʊ/", "meanings": []}
        ]

        user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_login(user)

        response = self.client.get(reverse("dictionary:dict-lookup", kwargs={"word": "hello"}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        history = SearchHistory.objects.filter(user=user, word="hello").first()
        self.assertIsNotNone(history)
        self.assertEqual(history.word, "hello")
        self.assertIn("word", history.definition_data)
        self.assertEqual(history.definition_data["word"], "hello")


class SearchHistoryViewSetTests(TestCase):
    """Tests for SearchHistoryViewSet."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.other_user = User.objects.create_user(username="otheruser", password="testpass123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_history(self):
        """Test listing user's search history."""
        SearchHistory.objects.create(user=self.user, word="first", definition_data={})
        SearchHistory.objects.create(user=self.user, word="second", definition_data={})

        response = self.client.get(reverse("dictionary:search-history-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["word"], "second")
        self.assertEqual(response.json()[1]["word"], "first")

    def test_list_history_isolated_per_user(self):
        """Test users only see their own history."""
        SearchHistory.objects.create(user=self.user, word="mine", definition_data={})
        SearchHistory.objects.create(user=self.other_user, word="theirs", definition_data={})

        response = self.client.get(reverse("dictionary:search-history-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["word"], "mine")

    def test_retrieve_history_entry(self):
        """Test retrieving a single history entry."""
        history = SearchHistory.objects.create(
            user=self.user, word="hello", definition_data={"word": "hello"}
        )

        response = self.client.get(reverse("dictionary:search-history-detail", kwargs={"pk": history.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["word"], "hello")

    def test_cannot_retrieve_other_users_history(self):
        """Test user cannot retrieve another user's history."""
        history = SearchHistory.objects.create(
            user=self.other_user, word="private", definition_data={}
        )

        response = self.client.get(reverse("dictionary:search-history-detail", kwargs={"pk": history.pk}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_clear_history(self):
        """Test clearing all history for current user."""
        SearchHistory.objects.create(user=self.user, word="first", definition_data={})
        SearchHistory.objects.create(user=self.user, word="second", definition_data={})
        SearchHistory.objects.create(user=self.other_user, word="other", definition_data={})

        response = self.client.delete(reverse("dictionary:search-history-clear-history"))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(SearchHistory.objects.filter(user=self.user).count(), 0)
        self.assertEqual(SearchHistory.objects.filter(user=self.other_user).count(), 1)

    def test_recent_history(self):
        """Test recent history endpoint returns last 20 entries."""
        for i in range(25):
            SearchHistory.objects.create(user=self.user, word=f"word{i}", definition_data={})

        response = self.client.get(reverse("dictionary:search-history-recent"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 20)
        self.assertEqual(response.json()[0]["word"], "word24")
        self.assertEqual(response.json()[19]["word"], "word5")

    def test_history_read_only(self):
        """Test history cannot be modified via POST/PUT/PATCH."""
        history = SearchHistory.objects.create(user=self.user, word="hello", definition_data={})

        for method in ['post', 'put', 'patch']:
            response = getattr(self.client, method)(
                reverse("dictionary:search-history-detail", kwargs={"pk": history.pk}),
                {"word": "changed"},
                format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class WordEntryViewSetTests(TestCase):
    """Tests for WordEntryViewSet."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.other_user = User.objects.create_user(username="otheruser", password="testpass123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_note_entry(self):
        """Test creating a note-type entry."""
        response = self.client.post(
            reverse("dictionary:word-entry-list"),
            {"word": "hello", "entry_type": "note"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["word"], "hello")
        self.assertEqual(response.json()["entry_type"], "note")
        self.assertEqual(response.json()["custom_note"], "")

    def test_create_bookmark_entry_with_note(self):
        """Test creating a bookmark with custom note."""
        response = self.client.post(
            reverse("dictionary:word-entry-list"),
            {
                "word": "world",
                "entry_type": "bookmark",
                "custom_note": "Important word"
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["entry_type"], "bookmark")
        self.assertEqual(response.json()["custom_note"], "Important word")

    def test_reject_custom_note_on_note_type(self):
        """Test validation rejects custom_note for note entries."""
        response = self.client.post(
            reverse("dictionary:word-entry-list"),
            {
                "word": "hello",
                "entry_type": "note",
                "custom_note": "Should fail"
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("custom_note", response.json())

    def test_list_entries(self):
        """Test listing user's word entries."""
        WordEntry.objects.create(user=self.user, word="first", entry_type=WordEntry.EntryType.NOTE)
        WordEntry.objects.create(user=self.user, word="second", entry_type=WordEntry.EntryType.BOOKMARK)

        response = self.client.get(reverse("dictionary:word-entry-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_list_entries_isolated_per_user(self):
        """Test users only see their own entries."""
        WordEntry.objects.create(user=self.user, word="mine", entry_type=WordEntry.EntryType.NOTE)
        WordEntry.objects.create(user=self.other_user, word="theirs", entry_type=WordEntry.EntryType.NOTE)

        response = self.client.get(reverse("dictionary:word-entry-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["word"], "mine")

    def test_retrieve_entry(self):
        """Test retrieving a single entry."""
        entry = WordEntry.objects.create(
            user=self.user, word="hello", entry_type=WordEntry.EntryType.BOOKMARK,
            custom_note="Test note"
        )

        response = self.client.get(reverse("dictionary:word-entry-detail", kwargs={"pk": entry.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["word"], "hello")
        self.assertEqual(response.json()["custom_note"], "Test note")

    def test_update_entry_type_to_bookmark_with_note(self):
        """Test updating note to bookmark with custom note."""
        entry = WordEntry.objects.create(
            user=self.user, word="hello", entry_type=WordEntry.EntryType.NOTE
        )

        response = self.client.patch(
            reverse("dictionary:word-entry-detail", kwargs={"pk": entry.pk}),
            {"entry_type": "bookmark", "custom_note": "New note"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["entry_type"], "bookmark")
        self.assertEqual(response.json()["custom_note"], "New note")

    def test_reject_custom_note_when_changing_to_note(self):
        """Test validation rejects custom_note when entry_type is note."""
        entry = WordEntry.objects.create(
            user=self.user, word="hello", entry_type=WordEntry.EntryType.BOOKMARK,
            custom_note="Existing note"
        )

        response = self.client.patch(
            reverse("dictionary:word-entry-detail", kwargs={"pk": entry.pk}),
            {"entry_type": "note", "custom_note": "Should fail"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("custom_note", response.json())

    def test_clear_custom_note_when_changing_to_note(self):
        """Test clearing custom_note when changing to note type."""
        entry = WordEntry.objects.create(
            user=self.user, word="hello", entry_type=WordEntry.EntryType.BOOKMARK,
            custom_note="Existing note"
        )

        response = self.client.patch(
            reverse("dictionary:word-entry-detail", kwargs={"pk": entry.pk}),
            {"entry_type": "note", "custom_note": ""},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["entry_type"], "note")
        self.assertEqual(response.json()["custom_note"], "")

    def test_delete_entry(self):
        """Test deleting an entry."""
        entry = WordEntry.objects.create(
            user=self.user, word="hello", entry_type=WordEntry.EntryType.NOTE
        )

        response = self.client.delete(reverse("dictionary:word-entry-detail", kwargs={"pk": entry.pk}))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(WordEntry.objects.filter(user=self.user).count(), 0)

    def test_notes_action(self):
        """Test notes endpoint returns only note-type entries."""
        WordEntry.objects.create(user=self.user, word="note1", entry_type=WordEntry.EntryType.NOTE)
        WordEntry.objects.create(user=self.user, word="note2", entry_type=WordEntry.EntryType.NOTE)
        WordEntry.objects.create(user=self.user, word="bookmark1", entry_type=WordEntry.EntryType.BOOKMARK)

        response = self.client.get(reverse("dictionary:word-entry-notes"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        for entry in response.json():
            self.assertEqual(entry["entry_type"], "note")

    def test_bookmarks_action(self):
        """Test bookmarks endpoint returns only bookmark-type entries."""
        WordEntry.objects.create(user=self.user, word="note1", entry_type=WordEntry.EntryType.NOTE)
        WordEntry.objects.create(user=self.user, word="bookmark1", entry_type=WordEntry.EntryType.BOOKMARK)
        WordEntry.objects.create(user=self.user, word="bookmark2", entry_type=WordEntry.EntryType.BOOKMARK)

        response = self.client.get(reverse("dictionary:word-entry-bookmarks"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        for entry in response.json():
            self.assertEqual(entry["entry_type"], "bookmark")

    def test_mark_reviewed(self):
        """Test marking an entry as reviewed."""
        entry = WordEntry.objects.create(
            user=self.user, word="hello", entry_type=WordEntry.EntryType.NOTE
        )
        self.assertIsNone(entry.last_reviewed_at)

        response = self.client.post(reverse("dictionary:word-entry-mark-reviewed", kwargs={"pk": entry.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry.refresh_from_db()
        self.assertIsNotNone(entry.last_reviewed_at)

    def test_bulk_toggle_type(self):
        """Test bulk updating entry types."""
        entries = [
            WordEntry.objects.create(user=self.user, word=f"word{i}", entry_type=WordEntry.EntryType.NOTE)
            for i in range(3)
        ]

        response = self.client.post(
            reverse("dictionary:word-entry-bulk-toggle-type"),
            {"ids": [e.id for e in entries], "entry_type": "bookmark"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["detail"], "Updated 3 entries.")
        for entry in WordEntry.objects.filter(user=self.user):
            self.assertEqual(entry.entry_type, "bookmark")

    def test_bulk_toggle_type_clears_notes(self):
        """Test bulk toggle to note clears custom notes."""
        entries = [
            WordEntry.objects.create(
                user=self.user, word=f"word{i}", entry_type=WordEntry.EntryType.BOOKMARK,
                custom_note=f"Note {i}"
            )
            for i in range(3)
        ]

        response = self.client.post(
            reverse("dictionary:word-entry-bulk-toggle-type"),
            {"ids": [e.id for e in entries], "entry_type": "note"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for entry in WordEntry.objects.filter(user=self.user):
            self.assertEqual(entry.entry_type, "note")
            self.assertEqual(entry.custom_note, "")

    def test_bulk_toggle_invalid_type(self):
        """Test bulk toggle with invalid entry_type."""
        entry = WordEntry.objects.create(user=self.user, word="hello", entry_type=WordEntry.EntryType.NOTE)

        response = self.client.post(
            reverse("dictionary:word-entry-bulk-toggle-type"),
            {"ids": [entry.id], "entry_type": "invalid"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.json())

    def test_bulk_toggle_invalid_ids(self):
        """Test bulk toggle with invalid IDs."""
        response = self.client.post(
            reverse("dictionary:word-entry-bulk-toggle-type"),
            {"ids": "not-a-list", "entry_type": "bookmark"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
