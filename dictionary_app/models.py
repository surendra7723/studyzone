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
    )
    word = models.CharField(max_length=255, db_index=True)
    searched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # Store the definition/response for quick re-display
    definition_data = models.JSONField(default=dict, blank=True)

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
    )
    word = models.CharField(max_length=255, db_index=True)
    entry_type = models.CharField(
        max_length=10,
        choices=EntryType.choices,
        default=EntryType.NOTE,
        db_index=True,
    )
    # For bookmarks: custom user note
    custom_note = models.TextField(blank=True, default='')
    # Cache the latest definition for offline access
    definition_data = models.JSONField(default=dict, blank=True)
    # When added to user's collection
    added_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # Optional: when user last reviewed/practiced this word
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

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