"""Tests for dictionary app serializers."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from dictionary_app.models import SearchHistory, WordEntry
from dictionary_app.serializers import (
    SearchHistorySerializer,
    WordEntrySerializer,
    WordEntryCreateSerializer,
    WordEntryUpdateSerializer,
)

User = get_user_model()


class SearchHistorySerializerTests(TestCase):
    """Tests for SearchHistorySerializer."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.factory = APIRequestFactory()

    def test_serializer_fields(self):
        """Test serializer includes expected fields."""
        history = SearchHistory.objects.create(
            user=self.user,
            word="hello",
            definition_data={"word": "hello", "meanings": []},
        )
        serializer = SearchHistorySerializer(history)
        data = serializer.data

        self.assertIn('id', data)
        self.assertIn('word', data)
        self.assertIn('searched_at', data)
        self.assertIn('definition_data', data)
        self.assertEqual(data['word'], "hello")

    def test_read_only_fields(self):
        """Test all fields are read-only."""
        serializer = SearchHistorySerializer()
        for field_name, field in serializer.fields.items():
            self.assertTrue(field.read_only, f"Field {field_name} should be read-only")


class WordEntrySerializerTests(TestCase):
    """Tests for WordEntrySerializer."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.factory = APIRequestFactory()

    def test_validate_word_normalizes(self):
        """Test word is normalized to lowercase and stripped."""
        request = self.factory.post("/")
        request.user = self.user

        serializer = WordEntrySerializer(data={
            'word': '  Hello  ',
            'entry_type': 'note',
        }, context={'request': request})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['word'], 'hello')

    def test_reject_custom_note_on_note_type(self):
        """Test validation rejects custom_note for note entries."""
        request = self.factory.post("/")
        request.user = self.user

        serializer = WordEntrySerializer(data={
            'word': 'hello',
            'entry_type': 'note',
            'custom_note': 'This should fail',
        }, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('custom_note', serializer.errors)

    def test_allow_custom_note_on_bookmark_type(self):
        """Test validation allows custom_note for bookmark entries."""
        request = self.factory.post("/")
        request.user = self.user

        serializer = WordEntrySerializer(data={
            'word': 'hello',
            'entry_type': 'bookmark',
            'custom_note': 'This is a note',
        }, context={'request': request})
        self.assertTrue(serializer.is_valid())

    def test_serializer_fields(self):
        """Test serializer includes expected fields."""
        entry = WordEntry.objects.create(
            user=self.user,
            word="hello",
            entry_type=WordEntry.EntryType.BOOKMARK,
            custom_note="Test note",
            definition_data={"word": "hello"},
        )
        request = self.factory.get("/")
        request.user = self.user

        serializer = WordEntrySerializer(entry, context={'request': request})
        data = serializer.data

        self.assertIn('id', data)
        self.assertIn('word', data)
        self.assertIn('entry_type', data)
        self.assertIn('custom_note', data)
        self.assertIn('definition_data', data)
        self.assertIn('added_at', data)
        self.assertIn('last_reviewed_at', data)
        self.assertEqual(data['word'], "hello")
        self.assertEqual(data['entry_type'], "bookmark")
        self.assertEqual(data['custom_note'], "Test note")


class WordEntryCreateSerializerTests(TestCase):
    """Tests for WordEntryCreateSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.factory = APIRequestFactory()

    def test_create_with_definition_data(self):
        """Test creating entry with provided definition_data."""
        request = self.factory.post("/")
        request.user = self.user

        serializer = WordEntryCreateSerializer(data={
            'word': 'hello',
            'entry_type': 'bookmark',
            'custom_note': 'Test note',
            'definition_data': {'word': 'hello', 'meanings': []},
        }, context={'request': request})
        self.assertTrue(serializer.is_valid())

    def test_create_without_definition_data(self):
        """Test creating entry without definition_data (will be fetched)."""
        request = self.factory.post("/")
        request.user = self.user

        serializer = WordEntryCreateSerializer(data={
            'word': 'hello',
            'entry_type': 'note',
        }, context={'request': request})
        self.assertTrue(serializer.is_valid())