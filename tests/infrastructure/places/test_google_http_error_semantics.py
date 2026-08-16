"""Regression tests for Google Places HTTP error semantics."""

from datetime import date

import pytest

from solara_travel.domain.preferences import TravellerPreferences
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.infrastructure.http import (
    JsonHttpDecodeError,
    JsonHttpResponse,
)
from solara_travel.infrastructure.places.google import GooglePlacesHttpClient
from solara_travel.ports.errors import ProviderResponseError


def _request() -> RecommendationRequest:
    """Return a minimal destination-discovery request."""

    return RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 15),
        ),
        preferences=TravellerPreferences(),
    )


class InvalidJsonTransport:
    """Transport that simulates a provider response containing invalid JSON."""

    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> JsonHttpResponse:
        """Raise the decode failure produced by the concrete HTTP transport."""

        raise JsonHttpDecodeError(
            "HTTP response did not contain valid JSON"
        )


def test_google_places_maps_invalid_json_to_provider_response_error() -> None:
    """Malformed Google response bodies are response failures, not outages."""

    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=InvalidJsonTransport(),
    )

    with pytest.raises(
        ProviderResponseError,
        match="Google Places returned invalid JSON",
    ) as exc_info:
        client.search_destinations(_request())

    assert isinstance(exc_info.value.__cause__, JsonHttpDecodeError)
