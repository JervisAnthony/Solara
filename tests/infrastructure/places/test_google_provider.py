"""Tests for the Google Places provider adapter."""

from datetime import date

import pytest

from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.preferences import TravellerInterests, TravellerPreferences
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.infrastructure.places.google import GooglePlacesProvider
from solara_travel.ports.errors import (
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.ports.places import PlacesProvider


def _request() -> RecommendationRequest:
    """Return a representative destination-discovery request."""

    return RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 15),
        ),
        preferences=TravellerPreferences(
            interests=TravellerInterests(
                interests=("history", "food", "architecture"),
            ),
            preferred_pace="moderate",
            preferred_climate="mild",
        ),
    )


def _destination() -> Destination:
    """Return a representative normalized destination."""

    return Destination(
        name="Kyoto",
        country="Japan",
        coordinates=GeoCoordinates(
            latitude=35.0116,
            longitude=135.7681,
        ),
    )


def _destination_place(
    name: str,
    country: str,
    latitude: float,
    longitude: float,
) -> dict[str, object]:
    """Build representative raw Google destination data."""

    return {
        "displayName": {
            "text": name,
            "languageCode": "en",
        },
        "location": {
            "latitude": latitude,
            "longitude": longitude,
        },
        "addressComponents": [
            {
                "longText": country,
                "shortText": country[:2].upper(),
                "types": ["country", "political"],
            },
        ],
    }


def _attraction_place(
    name: str,
    category: str,
    latitude: float,
    longitude: float,
) -> dict[str, object]:
    """Build representative raw Google attraction data."""

    return {
        "displayName": {
            "text": name,
            "languageCode": "en",
        },
        "location": {
            "latitude": latitude,
            "longitude": longitude,
        },
        "primaryType": category,
        "types": [
            category,
            "tourist_attraction",
            "point_of_interest",
            "establishment",
        ],
    }


_MISSING = object()


class FakeGooglePlacesClient:
    """Controllable Google client used by offline provider tests."""

    def __init__(
        self,
        *,
        destination_response: object = _MISSING,
        attraction_response: object = _MISSING,
        destination_error: Exception | None = None,
        attraction_error: Exception | None = None,
    ) -> None:
        self.destination_response = (
            {"places": []}
            if destination_response is _MISSING
            else destination_response
        )
        self.attraction_response = (
            {"places": []}
            if attraction_response is _MISSING
            else attraction_response
        )
        self.destination_error = destination_error
        self.attraction_error = attraction_error
        self.destination_requests: list[RecommendationRequest] = []
        self.attraction_destinations: list[Destination] = []

    def search_destinations(
        self,
        request: RecommendationRequest,
    ) -> object:
        """Return controlled destination-search provider data."""

        self.destination_requests.append(request)

        if self.destination_error is not None:
            raise self.destination_error

        return self.destination_response

    def search_attractions(
        self,
        destination: Destination,
    ) -> object:
        """Return controlled attraction-search provider data."""

        self.attraction_destinations.append(destination)

        if self.attraction_error is not None:
            raise self.attraction_error

        return self.attraction_response


def test_google_places_provider_satisfies_places_provider_contract() -> None:
    """The adapter should structurally implement Solara's combined places port."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(),
    )

    assert isinstance(provider, PlacesProvider)


def test_discover_destinations_passes_request_to_client() -> None:
    """The provider should pass the original Solara request to its client."""

    client = FakeGooglePlacesClient()
    provider = GooglePlacesProvider(client=client)
    request = _request()

    provider.discover_destinations(request)

    assert client.destination_requests == [request]
    assert client.destination_requests[0] is request


def test_discover_destinations_normalizes_google_places() -> None:
    """Raw Google destination places should become domain destinations."""

    client = FakeGooglePlacesClient(
        destination_response={
            "places": [
                _destination_place(
                    "Kyoto",
                    "Japan",
                    35.0116,
                    135.7681,
                ),
                _destination_place(
                    "Lisbon",
                    "Portugal",
                    38.7223,
                    -9.1393,
                ),
            ],
        },
    )
    provider = GooglePlacesProvider(client=client)

    destinations = provider.discover_destinations(_request())

    assert destinations == (
        Destination(
            name="Kyoto",
            country="Japan",
            coordinates=GeoCoordinates(
                latitude=35.0116,
                longitude=135.7681,
            ),
        ),
        Destination(
            name="Lisbon",
            country="Portugal",
            coordinates=GeoCoordinates(
                latitude=38.7223,
                longitude=-9.1393,
            ),
        ),
    )


def test_discover_destinations_preserves_provider_order() -> None:
    """Normalization must not silently reorder provider results."""

    client = FakeGooglePlacesClient(
        destination_response={
            "places": [
                _destination_place(
                    "Lisbon",
                    "Portugal",
                    38.7223,
                    -9.1393,
                ),
                _destination_place(
                    "Kyoto",
                    "Japan",
                    35.0116,
                    135.7681,
                ),
            ],
        },
    )
    provider = GooglePlacesProvider(client=client)

    destinations = provider.discover_destinations(_request())

    assert tuple(destination.name for destination in destinations) == (
        "Lisbon",
        "Kyoto",
    )


def test_discover_destinations_returns_immutable_tuple() -> None:
    """Provider boundaries should return immutable domain collections."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            destination_response={
                "places": [
                    _destination_place(
                        "Kyoto",
                        "Japan",
                        35.0116,
                        135.7681,
                    ),
                ],
            },
        ),
    )

    destinations = provider.discover_destinations(_request())

    assert isinstance(destinations, tuple)


def test_discover_destinations_supports_empty_places_list() -> None:
    """A successful provider search may legitimately return no destinations."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            destination_response={"places": []},
        ),
    )

    assert provider.discover_destinations(_request()) == ()


def test_discover_destinations_supports_missing_places_field() -> None:
    """Google responses without places should represent an empty result set."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            destination_response={},
        ),
    )

    assert provider.discover_destinations(_request()) == ()


@pytest.mark.parametrize(
    "response",
    [
        None,
        "places",
        [],
        42,
    ],
)
def test_discover_destinations_rejects_non_object_response(
    response: object,
) -> None:
    """Google search responses must use the expected top-level object."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            destination_response=response,
        ),
    )

    with pytest.raises(
        ProviderResponseError,
        match="Google Places response must be an object",
    ):
        provider.discover_destinations(_request())


@pytest.mark.parametrize(
    "places",
    [
        None,
        "Kyoto",
        {},
        42,
    ],
)
def test_discover_destinations_rejects_invalid_places_collection(
    places: object,
) -> None:
    """The Google places member must be an array when present."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            destination_response={"places": places},
        ),
    )

    with pytest.raises(
        ProviderResponseError,
        match="Google Places response places must be a list",
    ):
        provider.discover_destinations(_request())


def test_discover_destinations_rejects_malformed_place() -> None:
    """Malformed individual results should remain provider response failures."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            destination_response={
                "places": [
                    _destination_place(
                        "Kyoto",
                        "Japan",
                        35.0116,
                        135.7681,
                    ),
                    "not-a-place",
                ],
            },
        ),
    )

    with pytest.raises(
        ProviderResponseError,
        match="Google place must be an object",
    ):
        provider.discover_destinations(_request())


def test_discover_destinations_propagates_known_provider_failure() -> None:
    """Known provider failures should retain their semantic error type."""

    error = ProviderRateLimitError("Google Places quota exceeded")
    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            destination_error=error,
        ),
    )

    with pytest.raises(ProviderRateLimitError) as exc_info:
        provider.discover_destinations(_request())

    assert exc_info.value is error


def test_discover_destinations_wraps_unexpected_client_failure() -> None:
    """Unexpected client failures should become provider-unavailable errors."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            destination_error=TimeoutError("network timed out"),
        ),
    )

    with pytest.raises(
        ProviderUnavailableError,
        match="Google Places request failed",
    ) as exc_info:
        provider.discover_destinations(_request())

    assert isinstance(exc_info.value.__cause__, TimeoutError)


def test_discover_attractions_passes_destination_to_client() -> None:
    """The provider should pass normalized destination evidence to its client."""

    client = FakeGooglePlacesClient()
    provider = GooglePlacesProvider(client=client)
    destination = _destination()

    provider.discover_attractions(destination)

    assert client.attraction_destinations == [destination]
    assert client.attraction_destinations[0] is destination


def test_discover_attractions_normalizes_google_places() -> None:
    """Raw Google attraction places should become domain attractions."""

    client = FakeGooglePlacesClient(
        attraction_response={
            "places": [
                _attraction_place(
                    "Fushimi Inari Taisha",
                    "shinto_shrine",
                    34.9671,
                    135.7727,
                ),
                _attraction_place(
                    "Kyoto National Museum",
                    "museum",
                    34.9900,
                    135.7730,
                ),
            ],
        },
    )
    provider = GooglePlacesProvider(client=client)

    attractions = provider.discover_attractions(_destination())

    assert tuple(attraction.name for attraction in attractions) == (
        "Fushimi Inari Taisha",
        "Kyoto National Museum",
    )
    assert tuple(attraction.category for attraction in attractions) == (
        "shinto shrine",
        "museum",
    )


def test_discover_attractions_preserves_provider_order() -> None:
    """Attraction normalization should preserve Google result ordering."""

    client = FakeGooglePlacesClient(
        attraction_response={
            "places": [
                _attraction_place(
                    "Kyoto National Museum",
                    "museum",
                    34.9900,
                    135.7730,
                ),
                _attraction_place(
                    "Fushimi Inari Taisha",
                    "shinto_shrine",
                    34.9671,
                    135.7727,
                ),
            ],
        },
    )
    provider = GooglePlacesProvider(client=client)

    attractions = provider.discover_attractions(_destination())

    assert tuple(attraction.name for attraction in attractions) == (
        "Kyoto National Museum",
        "Fushimi Inari Taisha",
    )


def test_discover_attractions_returns_immutable_tuple() -> None:
    """Attraction discovery should expose immutable domain collections."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            attraction_response={
                "places": [
                    _attraction_place(
                        "Fushimi Inari Taisha",
                        "shinto_shrine",
                        34.9671,
                        135.7727,
                    ),
                ],
            },
        ),
    )

    attractions = provider.discover_attractions(_destination())

    assert isinstance(attractions, tuple)


def test_discover_attractions_supports_empty_places_list() -> None:
    """A successful search may legitimately find no attractions."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            attraction_response={"places": []},
        ),
    )

    assert provider.discover_attractions(_destination()) == ()


def test_discover_attractions_supports_missing_places_field() -> None:
    """A missing places field should normalize to an empty attraction set."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            attraction_response={},
        ),
    )

    assert provider.discover_attractions(_destination()) == ()


@pytest.mark.parametrize(
    "response",
    [
        None,
        "places",
        [],
        42,
    ],
)
def test_discover_attractions_rejects_non_object_response(
    response: object,
) -> None:
    """Attraction searches require an object-shaped Google response."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            attraction_response=response,
        ),
    )

    with pytest.raises(
        ProviderResponseError,
        match="Google Places response must be an object",
    ):
        provider.discover_attractions(_destination())


@pytest.mark.parametrize(
    "places",
    [
        None,
        "attractions",
        {},
        42,
    ],
)
def test_discover_attractions_rejects_invalid_places_collection(
    places: object,
) -> None:
    """Google attraction responses require a list-valued places member."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            attraction_response={"places": places},
        ),
    )

    with pytest.raises(
        ProviderResponseError,
        match="Google Places response places must be a list",
    ):
        provider.discover_attractions(_destination())


def test_discover_attractions_rejects_malformed_place() -> None:
    """Malformed attraction data should remain a provider response failure."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            attraction_response={
                "places": [
                    _attraction_place(
                        "Fushimi Inari Taisha",
                        "shinto_shrine",
                        34.9671,
                        135.7727,
                    ),
                    None,
                ],
            },
        ),
    )

    with pytest.raises(
        ProviderResponseError,
        match="Google place must be an object",
    ):
        provider.discover_attractions(_destination())


def test_discover_attractions_propagates_known_provider_failure() -> None:
    """Known provider errors should pass through the infrastructure boundary."""

    error = ProviderRateLimitError("Google Places quota exceeded")
    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            attraction_error=error,
        ),
    )

    with pytest.raises(ProviderRateLimitError) as exc_info:
        provider.discover_attractions(_destination())

    assert exc_info.value is error


def test_discover_attractions_wraps_unexpected_client_failure() -> None:
    """Unexpected attraction-client failures should be normalized."""

    provider = GooglePlacesProvider(
        client=FakeGooglePlacesClient(
            attraction_error=TimeoutError("network timed out"),
        ),
    )

    with pytest.raises(
        ProviderUnavailableError,
        match="Google Places request failed",
    ) as exc_info:
        provider.discover_attractions(_destination())

    assert isinstance(exc_info.value.__cause__, TimeoutError)
