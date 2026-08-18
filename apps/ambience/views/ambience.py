from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from core.mixins import PaginationMixin

from ..models import AmbienceTrack, Category
from ..serializers import AmbienceCategorySerializer, AmbienceTrackSerializer


class AmbienceTrackListView(PaginationMixin, ListAPIView):
    queryset = AmbienceTrack.objects.filter(is_active=True)
    serializer_class = AmbienceTrackSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__name__iexact=category)
        return queryset


class AmbienceCategoryListView(PaginationMixin, ListAPIView):
    queryset = Category.objects.all()
    serializer_class = AmbienceCategorySerializer
    permission_classes = [AllowAny]
