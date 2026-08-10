from rest_framework.generics import ListAPIView

from ..models import AmbienceTrack, Category
from ..serializers import AmbienceCategorySerializer, AmbienceTrackSerializer


class AmbienceTrackListView(ListAPIView):
    queryset = AmbienceTrack.objects.filter(is_active=True)
    serializer_class = AmbienceTrackSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__name__iexact=category)
        return queryset


class AmbienceCategoryListView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = AmbienceCategorySerializer
