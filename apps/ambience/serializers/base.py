from core.serializers import BaseModelSerializer

from ..models import BaseAmbienceModel


class AmbienceBaseSerializer(BaseModelSerializer):
    """Base serializer for ambience."""

    class Meta:
        model = BaseAmbienceModel
        fields = "__all__"
