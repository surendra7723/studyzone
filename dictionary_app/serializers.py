from rest_framework import serializers


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
