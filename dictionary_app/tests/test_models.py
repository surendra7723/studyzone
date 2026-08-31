"""Tests for dictionary app models."""

from django.test import TestCase
from django.db import IntegrityError
from django.contrib.auth import get_user_model

from dictionary_app.models import SearchHistory, WordEntry

User = get_user_model()


class SearchHistoryModelTests(TestCase):
    """Tests for SearchHistory model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_history_auto_populates_searched_at(self):
        """Test that searched_at is automatically set on creation."""
        history = SearchHistory.objects.create(
            user=self.user,
            word="hello",
            definition_data={"word": "hello", "meanings": []},
        )
        self.assertIsNotNone(history.searched_at)

    def test_history_str_representation(self):
        """Test string representation."""
        history = SearchHistory.objects.create(
            user=self.user,
            word="hello",
            definition_data={},
        )
        expected = f"testuser searched 'hello' at {history.searched_at}"
        self.assertEqual(str(history), expected)

    def test_history_ordering(self):
        """Test that history is ordered by searched_at descending."""
        SearchHistory.objects.create(user=self.user, word="first", definition_data={})
        SearchHistory.objects.create(user=self.user, word="second", definition_data={})
        SearchHistory.objects.create(user=self.user, word="third", definition_data={})

        history = list(SearchHistory.objects.all())
        self.assertEqual(history[0].word, "third")
        self.assertEqual(history[1].word, "second")
        self.assertEqual(history[2].word, "first")


class WordEntryModelTests(TestCase):
    """Tests for WordEntry model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.other_user = User.objects.create_user(username="otheruser", password="testpass123")

    def test_create_note_entry(self):
        """Test creating a note-type entry."""
        entry = WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.NOTE,
        )
        self.assertEqual(entry.entry_type, WordEntry.EntryType.NOTE)
        self.assertEqual(entry.custom_note, "")

    def test_create_bookmark_entry_with_note(self):
        """Test creating a bookmark with custom note."""
        entry = WordEntry.objects.create(
            user=self.user,
            word="world",
            entry_type=WordEntry.EntryType.BOOKMARK,
            custom_note="Important word to remember",
        )
        self.assertEqual(entry.entry_type, WordEntry.EntryType.BOOKMARK)
        self.assertEqual(entry.custom_note, "Important word to remember")

    def test_unique_word_per_type_per_user(self):
        """Test that user can only have one entry per word per type."""
        WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.NOTE,
        )
        with self.assertRaises(IntegrityError):
            WordEntry.objects.create(
                user=self.user,
                word="hello",
                entry_type=WordEntry.EntryType.NOTE,
            )

    def test_same_word_different_types_allowed(self):
        """Test that user can have both note and bookmark for same word."""
        WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.NOTE,
        )
        # This should not raise
        bookmark = WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.BOOKMARK,
            custom_note="Bookmarked!",
        )
        self.assertEqual(bookmark.entry_type, WordEntry.EntryType.BOOKMARK)

    def test_different_users_same_word_allowed(self):
        """Test that different users can have entries for the same word."""
        WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.NOTE,
        )
        # This should not raise
        entry = WordEntry.objects.create(
            user=self.other_user,
            word="hello",
            entry_type=WordEntry.EntryType.NOTE,
        )
        self.assertEqual(entry.user, self.other_user)

    def test_str_representation(self):
        """Test string representation."""
        entry = WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.BOOKMARK,
        )
        expected = "testuser - hello (bookmark)"
        self.assertEqual(str(entry), expected)

    def test_ordering(self):
        """Test that entries are ordered by added_at descending."""
        WordEntry.objects.create(user=self.user, word="first", entry_type=WordEntry.EntryType.NOTE)
        WordEntry.objects.create(user=self.user, word="second", entry_type=WordEntry.EntryType.NOTE)
        WordEntry.objects.create(user=self.user, word="third", entry_type=WordEntry.EntryType.NOTE)

        entries = list(WordEntry.objects.all())
        self.assertEqual(entries[0].word, "third")
        self.assertEqual(entries[1].word, "second")
        self.assertEqual(entries[2].word, "first")