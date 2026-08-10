from core.serializers import BaseModelSerializer

from ..models import AmbienceTrack, Category


class AmbienceTrackSerializer(BaseModelSerializer):
    class Meta:
        model = AmbienceTrack
        fields = ["id", "name", "category", "file", "duration_seconds", "is_active"]


class AmbienceCategorySerializer(BaseModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]
