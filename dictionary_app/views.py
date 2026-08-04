from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import DictionaryResponseSerializer
from .services import ExternalDictionaryService


class DictionaryLookupView(APIView):
    """Look up a word using the public Free Dictionary API."""

    authentication_classes = []
    permission_classes = []

    def get(self, request, word):
        """Fetch and normalize the external dictionary payload for a word."""
        payload = ExternalDictionaryService.fetch_word_data(word)

        if not isinstance(payload, list) or not payload:
            raise APIException("The dictionary service returned an unexpected payload structure.")

        first_entry = payload[0]
        serializer = DictionaryResponseSerializer(data=first_entry)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
