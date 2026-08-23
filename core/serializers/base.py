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


class FieldRestrictedSerializer(serializers.ModelSerializer):
    restricted_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)

        is_owner = user and user.is_authenticated and (
            instance == user
            or (hasattr(instance, "get_owner") and instance.get_owner() == user)
            or getattr(user, "is_staff", False)
        )

        if not is_owner:
            for field in self.restricted_fields:
                data.pop(field, None)

        return data
