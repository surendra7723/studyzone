from urllib.parse import quote

import requests
from rest_framework.exceptions import APIException, NotFound


class ExternalDictionaryService:
    """Client service for fetching word definitions from the Free Dictionary API."""

    BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"

    @classmethod
    def fetch_word_data(cls, word: str):
        """Return the external dictionary payload for a given word.

        Raises:
            NotFound: When the external API reports that the word does not exist.
            APIException: When the upstream request fails or returns an unexpected payload.
        """
        normalized_word = (word or "").strip()
        if not normalized_word:
            raise APIException("A dictionary lookup word is required.")

        endpoint = f"{cls.BASE_URL}/{quote(normalized_word)}"

        try:
            response = requests.get(endpoint, timeout=5, headers={"Accept": "application/json"})
        except requests.exceptions.Timeout as exc:
            raise APIException("The dictionary service timed out while processing the request.") from exc
        except requests.exceptions.RequestException as exc:
            raise APIException("The dictionary service is currently unavailable.") from exc

        if response.status_code == 404:
            raise NotFound(detail="No dictionary entry was found for the provided word.")

        if response.status_code != 200:
            raise APIException(
                f"The dictionary service returned an unexpected status code: {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise APIException("The dictionary service returned an invalid JSON payload.") from exc

        if not isinstance(payload, list) or not payload:
            raise APIException("The dictionary service returned an unexpected payload structure.")

        return payload
