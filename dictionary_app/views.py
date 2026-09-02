"""Views for the dictionary app."""

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAuthenticatedAndActive, IsOwnerOrReadOnly
from core.views.generic import UserScopedViewSet

from .models import SearchHistory, WordEntry
from .serializers import (
    DictionaryResponseSerializer,
    SearchHistorySerializer,
    WordEntryCreateSerializer,
    WordEntrySerializer,
    WordEntryUpdateSerializer,
)
from .services import ExternalDictionaryService


@extend_schema(
    summary="Look up a word definition",
    description=(
        "Fetch and normalize the external dictionary payload for a word. "
        "Authenticated users have their search recorded in history."
    ),
    tags=["Dictionary"],
)
class DictionaryLookupView(APIView):
    """Look up a word using the public Free Dictionary API."""

    serializer_class = DictionaryResponseSerializer
    # Allow public access, but still attempt authentication so that
    # authenticated users get their searches recorded in history.
    permission_classes = []

    def get(self, request, word):
        """Fetch and normalize the external dictionary payload for a word."""
        payload = ExternalDictionaryService.fetch_word_data(word)

        if not isinstance(payload, list) or not payload:
            raise APIException("The dictionary service returned an unexpected payload structure.")

        first_entry = payload[0]
        serializer = DictionaryResponseSerializer(data=first_entry)
        serializer.is_valid(raise_exception=True)

        # If authenticated user, save to search history
        if request.user and request.user.is_authenticated:
            SearchHistory.objects.update_or_create(
                user=request.user,
                word=word.lower().strip(),
                searched_at__date=timezone.now().date(),
                defaults={'definition_data': serializer.data}
            )

        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary="List search history",
        description="Returns all search history entries for the authenticated user",
        tags=["Dictionary - Search History"],
        parameters=[
            OpenApiParameter(
                name="ordering",
                description="Order by field (prefix with - for descending)",
                required=False,
                type=str,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get search history entry details",
        description="Retrieve details of a specific search history entry",
        tags=["Dictionary - Search History"],
    ),
    destroy=extend_schema(
        summary="Delete a search history entry",
        description="Delete a single search history entry permanently",
        tags=["Dictionary - Search History"],
    ),
)
class SearchHistoryViewSet(UserScopedViewSet):
    """ViewSet for managing user's search history."""

    queryset = SearchHistory.objects.all()
    serializer_class = SearchHistorySerializer
    permission_classes = [IsAuthenticatedAndActive, IsOwnerOrReadOnly]

    # Read-only by default (history is append-only via lookup)
    http_method_names = ['get', 'head', 'options', 'delete']

    @extend_schema(
        summary="Clear all search history",
        description="Delete all search history entries for the current user",
        tags=["Dictionary - Search History"],
    )
    @action(detail=False, methods=['delete'], url_path='clear')
    def clear_history(self, request):
        """Clear all search history for the current user."""
        count, _ = self.get_queryset().delete()
        return Response(
            {'detail': f'Successfully cleared {count} history entries.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @extend_schema(
        summary="Get recent search history",
        description="Get the last 20 search history entries for the current user",
        tags=["Dictionary - Search History"],
    )
    @action(detail=False, methods=['get'], url_path='recent')
    def recent(self, request):
        """Get recent search history (last 20 entries)."""
        queryset = self.get_queryset()[:20]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List word entries",
        description="Returns all word entries (notes and bookmarks) for the authenticated user",
        tags=["Dictionary - Words"],
        parameters=[
            OpenApiParameter(
                name="entry_type",
                description="Filter by entry type (note or bookmark)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                description="Order by field (prefix with - for descending)",
                required=False,
                type=str,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create a word entry",
        description="Create a new note or bookmark for a word",
        tags=["Dictionary - Words"],
    ),
    retrieve=extend_schema(
        summary="Get word entry details",
        description="Retrieve details of a specific word entry",
        tags=["Dictionary - Words"],
    ),
    update=extend_schema(
        summary="Update a word entry",
        description="Update all fields of a word entry",
        tags=["Dictionary - Words"],
    ),
    partial_update=extend_schema(
        summary="Partially update a word entry",
        description="Update specific fields of a word entry",
        tags=["Dictionary - Words"],
    ),
    destroy=extend_schema(
        summary="Delete a word entry",
        description="Delete a word entry permanently",
        tags=["Dictionary - Words"],
    ),
)
class WordEntryViewSet(UserScopedViewSet):
    """ViewSet for managing user's word entries (notes/bookmarks)."""

    queryset = WordEntry.objects.select_related('user').all()
    permission_classes = [IsAuthenticatedAndActive, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'create':
            return WordEntryCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return WordEntryUpdateSerializer
        return WordEntrySerializer

    def perform_create(self, serializer):
        """Auto-set user and fetch definition if not provided."""
        definition_data = serializer.validated_data.pop('definition_data', {})
        if not definition_data:
            # Fetch from external API
            try:
                payload = ExternalDictionaryService.fetch_word_data(serializer.validated_data['word'])
                if payload and isinstance(payload, list):
                    definition_data = DictionaryResponseSerializer(payload[0]).data
            except Exception:
                pass  # Graceful degradation - save without definition

        serializer.save(user=self.request.user, definition_data=definition_data)

    @extend_schema(
        summary="Get all note entries",
        description="Get all note-type entries for the authenticated user",
        tags=["Dictionary - Words"],
    )
    @action(detail=False, methods=['get'], url_path='notes')
    def notes(self, request):
        """Get all note-type entries."""
        queryset = self.get_queryset().filter(entry_type=WordEntry.EntryType.NOTE)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get all bookmark entries",
        description="Get all bookmark-type entries for the authenticated user",
        tags=["Dictionary - Words"],
    )
    @action(detail=False, methods=['get'], url_path='bookmarks')
    def bookmarks(self, request):
        """Get all bookmark-type entries."""
        queryset = self.get_queryset().filter(entry_type=WordEntry.EntryType.BOOKMARK)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Mark word entry as reviewed",
        description="Update last_reviewed_at timestamp for a word entry",
        tags=["Dictionary - Words"],
    )
    @action(detail=True, methods=['post'], url_path='review')
    def mark_reviewed(self, request, pk=None):
        """Mark a word entry as reviewed (update last_reviewed_at)."""
        entry = self.get_object()
        entry.last_reviewed_at = timezone.now()
        entry.save(update_fields=['last_reviewed_at'])
        serializer = self.get_serializer(entry)
        return Response(serializer.data)

    @extend_schema(
        summary="Bulk toggle entry types",
        description="Bulk update entry types between note and bookmark",
        tags=["Dictionary - Words"],
        request={
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of word entry IDs",
                        },
                        "entry_type": {
                            "type": "string",
                            "enum": ["note", "bookmark"],
                            "description": "The new entry type",
                        },
                    },
                    "required": ["ids", "entry_type"],
                }
            }
        },
    )
    @action(detail=False, methods=['post'], url_path='bulk-toggle')
    def bulk_toggle_type(self, request):
        """Bulk update entry types (note <-> bookmark)."""
        ids = request.data.get('ids', [])
        new_type = request.data.get('entry_type')

        if not ids or not isinstance(ids, list):
            return Response(
                {'detail': 'Expected a list of IDs.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_type not in WordEntry.EntryType.values:
            return Response(
                {'detail': f'Invalid entry_type. Must be one of: {WordEntry.EntryType.values}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(id__in=ids)
        updated = queryset.update(entry_type=new_type)

        # Clear custom_note if changing to note type
        if new_type == WordEntry.EntryType.NOTE:
            queryset.update(custom_note='')

        return Response({'detail': f'Updated {updated} entries.'}, status=status.HTTP_200_OK)
