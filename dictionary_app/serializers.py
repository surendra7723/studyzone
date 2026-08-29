"""Serializers for the dictionary app."""

from rest_framework import serializers

from .models import SearchHistory, WordEntry


class DictionaryDefinitionSerializer(serializers.Serializer):
    """Serializer for a single definition entry from the dictionary API."""

    definition = serializers.CharField(allow_blank=True, required=False)
    example = serializers.CharField(allow_blank=True, required=False, allow_null=True)


class DictionaryMeaningSerializer(serializers.Serializer):
    """Serializer for a single meaning entry with nested definitions."""

    partOfSpeech = serializers.CharField(allow_blank=True, required=False)
    definitions = DictionaryDefinitionSerializer(many=True, required=False)


class DictionaryResponseSerializer(serializers.Serializer):
    """Serializer for the normalized dictionary response payload."""

    word = serializers.CharField(allow_blank=True, required=False)
    phonetic = serializers.CharField(allow_blank=True, required=False, allow_null=True)
    meanings = DictionaryMeaningSerializer(many=True, required=False)


class SearchHistorySerializer(serializers.ModelSerializer):
    """Serializer for search history entries."""

    class Meta:
        model = SearchHistory
        fields = ['id', 'word', 'searched_at', 'definition_data']
        read_only_fields = fields  # History is append-only


class WordEntrySerializer(serializers.ModelSerializer):
    """Serializer for user word entries (notes/bookmarks)."""

    class Meta:
        model = WordEntry
        fields = [
            'id', 'word', 'entry_type', 'custom_note',
            'definition_data', 'added_at', 'last_reviewed_at'
        ]
        read_only_fields = ['id', 'added_at', 'definition_data', 'last_reviewed_at']

    def validate_word(self, value):
        """Normalize word to lowercase and strip whitespace."""
        return value.strip().lower()

    def validate(self, attrs):
        """Cross-field validation: custom_note only for bookmarks."""
        entry_type = attrs.get('entry_type', self.instance.entry_type if self.instance else WordEntry.EntryType.NOTE)
        custom_note = attrs.get('custom_note', '')

        if entry_type == WordEntry.EntryType.NOTE and custom_note:
            raise serializers.ValidationError({
                'custom_note': 'Custom notes are only allowed for bookmarked words.'
            })
        return attrs


class WordEntryCreateSerializer(WordEntrySerializer):
    """Serializer for creating word entries (fetches definition from external API)."""

    # Accept the definition from the lookup to avoid re-fetching
    definition_data = serializers.JSONField(required=False, write_only=True)

    class Meta(WordEntrySerializer.Meta):
        read_only_fields = ['id', 'added_at', 'last_reviewed_at']


class WordEntryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating word entries (only custom_note and entry_type)."""

    class Meta:
        model = WordEntry
        fields = ['entry_type', 'custom_note']

    def validate(self, attrs):
        """Ensure custom_note only with bookmark type."""
        entry_type = attrs.get('entry_type', self.instance.entry_type)
        custom_note = attrs.get('custom_note', self.instance.custom_note)

        if entry_type == WordEntry.EntryType.NOTE and custom_note:
            raise serializers.ValidationError({
                'custom_note': 'Cannot add custom note to a note-type entry. Change to bookmark first.'
            })
        return attrs
