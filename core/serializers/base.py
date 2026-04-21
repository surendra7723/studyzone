from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """Base serializer for feature apps."""

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
