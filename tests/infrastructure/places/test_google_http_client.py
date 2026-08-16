"""Tests for Google Places HTTP-client request construction and failures."""

from datetime import date
from math import inf, nan

import pytest

from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.preferences import (
    TravellerInterests,
    TravellerPreferences,
)
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.infrastructure.http import JsonHttpResponse
from solara_travel.infrastructure.places.google import GooglePlacesHttpClient
from solara_travel.ports.errors import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)

_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"

_DESTINATION_FIELD_MASK = (
    "places.displayName,"
    "places.location,"
    "places.addressComponents"
)

_ATTRACTION_FIELD_MASK = (
    "places.displayName,"
    "places.location,"
    "places.primaryType,"
    "places.types"
)

_MISSING = object()


def _request(
    *,
    interests: tuple[str, ...] | None = (
        "history",
        "food",
        "architecture",
    ),
) -> RecommendationRequest:
    """Return a representative destination-discovery request."""

    traveller_interests = (
        TravellerInterests(interests=interests)
        if interests is not None
        else None
    )

    return RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 15),
        ),
        preferences=TravellerPreferences(
            interests=traveller_interests,
            preferred_pace="moderate",
            preferred_climate="mild",
        ),
    )


def _destination() -> Destination:
    """Return a representative attraction-search destination."""

    return Destination(
        name="Kyoto",
        country="Japan",
        coordinates=GeoCoordinates(
            latitude=35.0116,
            longitude=135.7681,
        ),
    )


class FakeJsonHttpTransport:
    """Record JSON HTTP calls and return controlled responses."""

    def __init__(
        self,
        *,
        response: object = _MISSING,
        error: Exception | None = None,
    ) -> None:
        self.response = (
            JsonHttpResponse(
                status_code=200,
                payload={"places": []},
            )
            if response is _MISSING
            else response
        )
        self.error = error
        self.requests: list[dict[str, object]] = []

    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> JsonHttpResponse:
        """Record a request and return the configured response."""

        self.requests.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )

        if self.error is not None:
            raise self.error

        assert isinstance(self.response, JsonHttpResponse)
        return self.response


def test_google_places_http_client_accepts_valid_configuration() -> None:
    """A valid client configuration should be preserved."""

    transport = FakeJsonHttpTransport()

    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
        timeout_seconds=8.0,
        destination_page_size=8,
        attraction_max_results=15,
        attraction_radius_meters=25_000.0,
    )

    assert client.api_key == "test-api-key"
    assert client.transport is transport
    assert client.timeout_seconds == 8.0
    assert client.destination_page_size == 8
    assert client.attraction_max_results == 15
    assert client.attraction_radius_meters == 25_000.0


@pytest.mark.parametrize(
    "api_key",
    [
        "",
        " ",
        "\t",
        "\n",
    ],
)
def test_google_places_http_client_rejects_blank_api_key(
    api_key: str,
) -> None:
    """Google authentication configuration requires a meaningful API key."""

    with pytest.raises(
        ValueError,
        match="api_key must not be blank",
    ):
        GooglePlacesHttpClient(
            api_key=api_key,
            transport=FakeJsonHttpTransport(),
        )


@pytest.mark.parametrize(
    "api_key",
    [
        None,
        42,
        ["key"],
        True,
    ],
)
def test_google_places_http_client_rejects_non_string_api_key(
    api_key: object,
) -> None:
    """Google API keys must be represented as strings."""

    with pytest.raises(
        TypeError,
        match="api_key must be a string",
    ):
        GooglePlacesHttpClient(
            api_key=api_key,  # type: ignore[arg-type]
            transport=FakeJsonHttpTransport(),
        )


@pytest.mark.parametrize(
    "timeout_seconds",
    [
        0.0,
        -0.1,
        -10.0,
    ],
)
def test_google_places_http_client_rejects_non_positive_timeout(
    timeout_seconds: float,
) -> None:
    """HTTP requests require a strictly positive timeout."""

    with pytest.raises(
        ValueError,
        match="timeout_seconds must be greater than zero",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            timeout_seconds=timeout_seconds,
        )


@pytest.mark.parametrize(
    "timeout_seconds",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_google_places_http_client_rejects_non_finite_timeout(
    timeout_seconds: float,
) -> None:
    """HTTP timeout configuration must be finite."""

    with pytest.raises(
        ValueError,
        match="timeout_seconds must be a finite number",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            timeout_seconds=timeout_seconds,
        )


@pytest.mark.parametrize(
    "timeout_seconds",
    [
        None,
        "10.0",
        [10.0],
        True,
    ],
)
def test_google_places_http_client_rejects_non_numeric_timeout(
    timeout_seconds: object,
) -> None:
    """HTTP timeout configuration must be numeric."""

    with pytest.raises(
        TypeError,
        match="timeout_seconds must be a real number",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            timeout_seconds=timeout_seconds,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "destination_page_size",
    [
        0,
        -1,
        21,
        100,
    ],
)
def test_google_places_http_client_rejects_invalid_destination_page_size(
    destination_page_size: int,
) -> None:
    """Text Search page size must remain within Google's supported range."""

    with pytest.raises(
        ValueError,
        match="destination_page_size must be between 1 and 20",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            destination_page_size=destination_page_size,
        )


@pytest.mark.parametrize(
    "destination_page_size",
    [
        None,
        10.5,
        "10",
        True,
    ],
)
def test_google_places_http_client_rejects_non_integer_destination_page_size(
    destination_page_size: object,
) -> None:
    """Text Search page size must use a real integer count."""

    with pytest.raises(
        TypeError,
        match="destination_page_size must be an integer",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            destination_page_size=destination_page_size,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "attraction_max_results",
    [
        0,
        -1,
        21,
        100,
    ],
)
def test_google_places_http_client_rejects_invalid_attraction_max_results(
    attraction_max_results: int,
) -> None:
    """Nearby Search result count must remain within Google's limits."""

    with pytest.raises(
        ValueError,
        match="attraction_max_results must be between 1 and 20",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            attraction_max_results=attraction_max_results,
        )


@pytest.mark.parametrize(
    "attraction_max_results",
    [
        None,
        10.5,
        "10",
        True,
    ],
)
def test_google_places_http_client_rejects_non_integer_attraction_max_results(
    attraction_max_results: object,
) -> None:
    """Nearby Search result limits must use integer counts."""

    with pytest.raises(
        TypeError,
        match="attraction_max_results must be an integer",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            attraction_max_results=attraction_max_results,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "attraction_radius_meters",
    [
        0.0,
        -0.1,
        -100.0,
        50_000.0001,
        100_000.0,
    ],
)
def test_google_places_http_client_rejects_invalid_attraction_radius(
    attraction_radius_meters: float,
) -> None:
    """Nearby Search radius must stay within Google's supported circle."""

    with pytest.raises(
        ValueError,
        match="attraction_radius_meters must be between 0 and 50000",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            attraction_radius_meters=attraction_radius_meters,
        )


@pytest.mark.parametrize(
    "attraction_radius_meters",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_google_places_http_client_rejects_non_finite_attraction_radius(
    attraction_radius_meters: float,
) -> None:
    """Nearby Search radius must be finite."""

    with pytest.raises(
        ValueError,
        match="attraction_radius_meters must be a finite number",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            attraction_radius_meters=attraction_radius_meters,
        )


@pytest.mark.parametrize(
    "attraction_radius_meters",
    [
        None,
        "30000",
        [30_000.0],
        True,
    ],
)
def test_google_places_http_client_rejects_non_numeric_attraction_radius(
    attraction_radius_meters: object,
) -> None:
    """Nearby Search radius must be represented numerically."""

    with pytest.raises(
        TypeError,
        match="attraction_radius_meters must be a real number",
    ):
        GooglePlacesHttpClient(
            api_key="test-api-key",
            transport=FakeJsonHttpTransport(),
            attraction_radius_meters=attraction_radius_meters,  # type: ignore[arg-type]
        )


def test_search_destinations_posts_to_google_text_search() -> None:
    """Destination discovery should use Google Places Text Search."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    client.search_destinations(_request())

    assert transport.requests[0]["url"] == _TEXT_SEARCH_URL


def test_search_destinations_sends_authentication_and_field_mask_headers() -> None:
    """Text Search should send only the required Google request headers."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    client.search_destinations(_request())

    assert transport.requests[0]["headers"] == {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": "test-api-key",
        "X-Goog-FieldMask": _DESTINATION_FIELD_MASK,
    }


def test_search_destinations_builds_interest_aware_query() -> None:
    """Traveller interests should guide candidate destination retrieval."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    client.search_destinations(_request())

    assert transport.requests[0]["payload"] == {
        "textQuery": "travel destinations for history, food, architecture",
        "includedType": "locality",
        "strictTypeFiltering": True,
        "languageCode": "en",
        "pageSize": 10,
    }


def test_search_destinations_strips_interest_whitespace() -> None:
    """Provider query formatting should normalize preserved interest text."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    client.search_destinations(
        _request(
            interests=(
                " history ",
                " food ",
            ),
        )
    )

    assert (
        transport.requests[0]["payload"]["textQuery"]
        == "travel destinations for history, food"
    )


def test_search_destinations_uses_generic_query_without_interests() -> None:
    """Destination discovery should work without stated traveller interests."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    client.search_destinations(
        _request(interests=None),
    )

    assert (
        transport.requests[0]["payload"]["textQuery"]
        == "travel destinations"
    )


def test_search_destinations_passes_configured_page_size() -> None:
    """Configured destination result limits should reach Google Text Search."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
        destination_page_size=7,
    )

    client.search_destinations(_request())

    assert transport.requests[0]["payload"]["pageSize"] == 7


def test_search_destinations_passes_configured_timeout() -> None:
    """Transport calls should use the configured client timeout."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
        timeout_seconds=6.5,
    )

    client.search_destinations(_request())

    assert transport.requests[0]["timeout_seconds"] == 6.5


def test_search_destinations_returns_json_payload_unchanged() -> None:
    """The HTTP client should leave response normalization to its provider."""

    payload = {
        "places": [
            {
                "displayName": {
                    "text": "Kyoto",
                },
            },
        ],
    }
    transport = FakeJsonHttpTransport(
        response=JsonHttpResponse(
            status_code=200,
            payload=payload,
        ),
    )
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    result = client.search_destinations(_request())

    assert result is payload


@pytest.mark.parametrize(
    "status_code",
    [
        401,
        403,
    ],
)
def test_google_http_client_maps_authentication_failures(
    status_code: int,
) -> None:
    """Google authentication failures should use Solara's semantic error."""

    transport = FakeJsonHttpTransport(
        response=JsonHttpResponse(
            status_code=status_code,
            payload={"error": "authentication failed"},
        ),
    )
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    with pytest.raises(
        ProviderAuthenticationError,
        match="Google Places authentication failed",
    ):
        client.search_destinations(_request())


def test_google_http_client_maps_rate_limit_failure() -> None:
    """Google quota exhaustion should become a rate-limit provider error."""

    transport = FakeJsonHttpTransport(
        response=JsonHttpResponse(
            status_code=429,
            payload={"error": "quota exceeded"},
        ),
    )
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    with pytest.raises(
        ProviderRateLimitError,
        match="Google Places rate limit exceeded",
    ):
        client.search_destinations(_request())


@pytest.mark.parametrize(
    "status_code",
    [
        400,
        404,
        409,
        422,
    ],
)
def test_google_http_client_maps_rejected_requests(
    status_code: int,
) -> None:
    """Other Google client errors should become provider response errors."""

    transport = FakeJsonHttpTransport(
        response=JsonHttpResponse(
            status_code=status_code,
            payload={"error": "invalid request"},
        ),
    )
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    with pytest.raises(
        ProviderResponseError,
        match="Google Places rejected the request",
    ):
        client.search_destinations(_request())


@pytest.mark.parametrize(
    "status_code",
    [
        500,
        502,
        503,
        504,
    ],
)
def test_google_http_client_maps_service_failures(
    status_code: int,
) -> None:
    """Google server failures should become provider-unavailable errors."""

    transport = FakeJsonHttpTransport(
        response=JsonHttpResponse(
            status_code=status_code,
            payload={"error": "service unavailable"},
        ),
    )
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    with pytest.raises(
        ProviderUnavailableError,
        match="Google Places service unavailable",
    ):
        client.search_destinations(_request())


def test_google_http_client_rejects_unexpected_http_status() -> None:
    """Unexpected non-success statuses should not be treated as valid data."""

    transport = FakeJsonHttpTransport(
        response=JsonHttpResponse(
            status_code=302,
            payload={"places": []},
        ),
    )
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    with pytest.raises(
        ProviderResponseError,
        match="Google Places returned unexpected HTTP status",
    ):
        client.search_destinations(_request())


def test_google_http_client_maps_timeout_failure() -> None:
    """Transport timeouts should become provider-unavailable errors."""

    transport = FakeJsonHttpTransport(
        error=TimeoutError("request timed out"),
    )
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    with pytest.raises(
        ProviderUnavailableError,
        match="Google Places request failed",
    ) as exc_info:
        client.search_destinations(_request())

    assert isinstance(exc_info.value.__cause__, TimeoutError)


def test_google_http_client_maps_network_failure() -> None:
    """Network transport failures should become provider-unavailable errors."""

    transport = FakeJsonHttpTransport(
        error=OSError("network unavailable"),
    )
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    with pytest.raises(
        ProviderUnavailableError,
        match="Google Places request failed",
    ) as exc_info:
        client.search_destinations(_request())

    assert isinstance(exc_info.value.__cause__, OSError)


def test_search_attractions_posts_to_google_nearby_search() -> None:
    """Attraction discovery should use Google Places Nearby Search."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    client.search_attractions(_destination())

    assert transport.requests[0]["url"] == _NEARBY_SEARCH_URL


def test_search_attractions_sends_authentication_and_field_mask_headers() -> None:
    """Nearby Search should request only fields required by normalization."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    client.search_attractions(_destination())

    assert transport.requests[0]["headers"] == {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": "test-api-key",
        "X-Goog-FieldMask": _ATTRACTION_FIELD_MASK,
    }


def test_search_attractions_builds_nearby_search_payload() -> None:
    """Attractions should be retrieved around the destination coordinates."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    client.search_attractions(_destination())

    assert transport.requests[0]["payload"] == {
        "includedTypes": ["tourist_attraction"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": 35.0116,
                    "longitude": 135.7681,
                },
                "radius": 30_000.0,
            },
        },
        "rankPreference": "POPULARITY",
        "languageCode": "en",
    }


def test_search_attractions_passes_configured_result_limit() -> None:
    """Configured attraction result limits should reach Nearby Search."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
        attraction_max_results=12,
    )

    client.search_attractions(_destination())

    assert transport.requests[0]["payload"]["maxResultCount"] == 12


def test_search_attractions_passes_configured_radius() -> None:
    """Configured search radius should be represented in meters."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
        attraction_radius_meters=12_500.0,
    )

    client.search_attractions(_destination())

    location_restriction = transport.requests[0]["payload"][
        "locationRestriction"
    ]
    assert isinstance(location_restriction, dict)

    circle = location_restriction["circle"]
    assert isinstance(circle, dict)

    assert circle["radius"] == 12_500.0


def test_search_attractions_passes_configured_timeout() -> None:
    """Nearby Search should use the same explicit timeout policy."""

    transport = FakeJsonHttpTransport()
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
        timeout_seconds=4.0,
    )

    client.search_attractions(_destination())

    assert transport.requests[0]["timeout_seconds"] == 4.0


def test_search_attractions_returns_json_payload_unchanged() -> None:
    """Attraction response normalization should remain outside the HTTP client."""

    payload = {
        "places": [
            {
                "displayName": {
                    "text": "Fushimi Inari Taisha",
                },
            },
        ],
    }
    transport = FakeJsonHttpTransport(
        response=JsonHttpResponse(
            status_code=200,
            payload=payload,
        ),
    )
    client = GooglePlacesHttpClient(
        api_key="test-api-key",
        transport=transport,
    )

    result = client.search_attractions(_destination())

    assert result is payload
