from core.serializers import BaseModelSerializer

from ..models import BaseServerModel


class ServerBaseSerializer(BaseModelSerializer):
    """Base serializer for server."""

    class Meta:
        model = BaseServerModel
        fields = "__all__"
