"""Tests for WordEntryUpdateSerializer."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from dictionary_app.models import WordEntry
from dictionary_app.serializers import WordEntryUpdateSerializer

User = get_user_model()


class WordEntryUpdateSerializerTests(TestCase):
    """Tests for WordEntryUpdateSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.factory = APIRequestFactory()

    def test_update_entry_type_to_bookmark_with_note(self):
        """Test updating note to bookmark with custom note."""
        entry = WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.NOTE,
        )
        request = self.factory.patch("/")
        request.user = self.user

        serializer = WordEntryUpdateSerializer(entry, data={
            'entry_type': 'bookmark',
            'custom_note': 'New note',
        }, context={'request': request}, partial=True)
        self.assertTrue(serializer.is_valid())

    def test_reject_custom_note_when_changing_to_note(self):
        """Test validation rejects custom_note when entry_type is note."""
        entry = WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.BOOKMARK,
            custom_note="Existing note",
        )
        request = self.factory.patch("/")
        request.user = self.user

        serializer = WordEntryUpdateSerializer(entry, data={
            'entry_type': 'note',
            'custom_note': 'Should fail',
        }, context={'request': request}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('custom_note', serializer.errors)

    def test_clear_custom_note_when_changing_to_note(self):
        """Test clearing custom_note when changing to note type."""
        entry = WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.BOOKMARK,
            custom_note="Existing note",
        )
        request = self.factory.patch("/")
        request.user = self.user

        serializer = WordEntryUpdateSerializer(entry, data={
            'entry_type': 'note',
            'custom_note': '',  # Empty is allowed
        }, context={'request': request}, partial=True)
        self.assertTrue(serializer.is_valid())