"""Models for the dictionary app."""

from django.conf import settings
from django.db import models

from core.mixins import OwnedModel


class SearchHistory(OwnedModel, models.Model):
    """Track user's word search history chronologically."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_history",
        help_text="The user who performed the search.",
    )
    word = models.CharField(max_length=255, db_index=True, help_text="The searched word.")
    searched_at = models.DateTimeField(auto_now_add=True, db_index=True, help_text="When the word was searched.")
    # Store the definition/response for quick re-display
    definition_data = models.JSONField(default=dict, blank=True, help_text="Cached definition data from the external API.")

    class Meta:
        ordering = ['-searched_at']
        verbose_name_plural = 'Search histories'
        indexes = [
            models.Index(fields=['user', 'searched_at']),
            models.Index(fields=['user', 'word']),
        ]

    def __str__(self):
        return f"{self.user.username} searched '{self.word}' at {self.searched_at}"


class WordEntry(OwnedModel, models.Model):
    """User-managed word entries (noted or bookmarked)."""

    class EntryType(models.TextChoices):
        NOTE = 'note', 'Note'
        BOOKMARK = 'bookmark', 'Bookmark'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="word_entries",
        help_text="The owner of this word entry.",
    )
    word = models.CharField(max_length=255, db_index=True, help_text="The word saved by the user.")
    entry_type = models.CharField(
        max_length=10,
        choices=EntryType.choices,
        default=EntryType.NOTE,
        db_index=True,
        help_text="Whether this entry is a note or a bookmark.",
    )
    # For bookmarks: custom user note
    custom_note = models.TextField(blank=True, default='', help_text="Optional personal note, only allowed for bookmarks.")
    # Cache the latest definition for offline access
    definition_data = models.JSONField(default=dict, blank=True, help_text="Cached definition data from the external API.")
    # When added to user's collection
    added_at = models.DateTimeField(auto_now_add=True, db_index=True, help_text="When the word was added to the user's collection.")
    # Optional: when user last reviewed/practiced this word
    last_reviewed_at = models.DateTimeField(null=True, blank=True, help_text="When the user last reviewed or practiced this word.")

    class Meta:
        ordering = ['-added_at']
        verbose_name_plural = 'Word entries'
        indexes = [
            models.Index(fields=['user', 'entry_type']),
            models.Index(fields=['user', 'word', 'entry_type']),
        ]
        constraints = [
            # A user can have at most one entry per word per type
            models.UniqueConstraint(
                fields=['user', 'word', 'entry_type'],
                name='unique_word_entry_per_user_per_type'
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.word} ({self.entry_type})"