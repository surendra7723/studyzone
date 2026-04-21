from core.serializers import BaseModelSerializer

from ..models import BaseTasksModel


class TasksBaseSerializer(BaseModelSerializer):
    """Base serializer for tasks."""

    class Meta:
        model = BaseTasksModel
        fields = "__all__"
