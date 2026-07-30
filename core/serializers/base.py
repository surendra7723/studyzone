from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """Base serializer for feature apps."""

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """
    def __init__(self, *args, **kwargs):
        # Pop custom 'fields' argument and initialize parent
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop fields not in the allowed list
            allowed = set(fields)
            for field_name in set(self.fields) - allowed:
                self.fields.pop(field_name)
