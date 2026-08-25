from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from core.mixins import PaginationMixin
from drf_spectacular.utils import extend_schema, OpenApiParameter

from ..models import AmbienceTrack, Category
from ..serializers import AmbienceCategorySerializer, AmbienceTrackSerializer


@extend_schema(
    summary="List ambience tracks",
    description="Returns all active ambience tracks, optionally filtered by category",
    tags=["Ambience"],
    parameters=[
        OpenApiParameter(
            name="category",
            description="Filter by category name (case-insensitive)",
            required=False,
            type=str,
        ),
    ],
)
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


@extend_schema(
    summary="List ambience categories",
    description="Returns all ambience categories",
    tags=["Ambience"],
)
class AmbienceCategoryListView(PaginationMixin, ListAPIView):
    queryset = Category.objects.all()
    serializer_class = AmbienceCategorySerializer
    permission_classes = [AllowAny]
