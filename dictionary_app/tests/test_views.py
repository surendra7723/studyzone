from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework import status


class DictionaryLookupViewTests(SimpleTestCase):
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
