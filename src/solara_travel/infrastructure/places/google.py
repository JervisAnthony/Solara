"""Google Places normalization and provider integration for Solara."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real
from typing import Protocol

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.infrastructure.http import (
    JsonHttpDecodeError,
    JsonHttpTransport,
)
from solara_travel.ports.errors import (
    ProviderAuthenticationError,
    ProviderError,
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

_GENERIC_GOOGLE_PLACE_TYPES = frozenset(
    {
        "establishment",
        "point_of_interest",
    }
)


class GooglePlacesClient(Protocol):
    """Transport-facing contract required by the Google Places provider."""

    def search_destinations(
        self,
        request: RecommendationRequest,
    ) -> object:
        """Return a raw Google Places destination-search response."""

        ...

    def search_attractions(
        self,
        destination: Destination,
    ) -> object:
        """Return a raw Google Places attraction-search response."""

        ...


@dataclass(slots=True)
class GooglePlacesHttpClient:
    """Google Places API client using an injected JSON HTTP transport."""

    api_key: str = field(repr=False)
    transport: JsonHttpTransport
    timeout_seconds: float = 10.0
    destination_page_size: int = 10
    attraction_max_results: int = 20
    attraction_radius_meters: float = 30_000.0

    def __post_init__(self) -> None:
        """Validate Google Places client configuration."""

        if not isinstance(self.api_key, str):
            raise TypeError("api_key must be a string")

        if not self.api_key.strip():
            raise ValueError("api_key must not be blank")

        if (
            not isinstance(self.timeout_seconds, Real)
            or isinstance(self.timeout_seconds, bool)
        ):
            raise TypeError("timeout_seconds must be a real number")

        if not isfinite(self.timeout_seconds):
            raise ValueError("timeout_seconds must be a finite number")

        if self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than zero")

        if (
            not isinstance(self.destination_page_size, int)
            or isinstance(self.destination_page_size, bool)
        ):
            raise TypeError("destination_page_size must be an integer")

        if not 1 <= self.destination_page_size <= 20:
            raise ValueError(
                "destination_page_size must be between 1 and 20"
            )

        if (
            not isinstance(self.attraction_max_results, int)
            or isinstance(self.attraction_max_results, bool)
        ):
            raise TypeError("attraction_max_results must be an integer")

        if not 1 <= self.attraction_max_results <= 20:
            raise ValueError(
                "attraction_max_results must be between 1 and 20"
            )

        if (
            not isinstance(self.attraction_radius_meters, Real)
            or isinstance(self.attraction_radius_meters, bool)
        ):
            raise TypeError(
                "attraction_radius_meters must be a real number"
            )

        if not isfinite(self.attraction_radius_meters):
            raise ValueError(
                "attraction_radius_meters must be a finite number"
            )

        if not 0.0 < self.attraction_radius_meters <= 50_000.0:
            raise ValueError(
                "attraction_radius_meters must be between 0 and 50000"
            )

    def search_destinations(
        self,
        request: RecommendationRequest,
    ) -> object:
        """Search Google Places for candidate travel destinations."""

        text_query = "travel destinations"
        interests = request.preferences.interests

        if interests is not None:
            interest_text = ", ".join(
                interest.strip()
                for interest in interests.interests
            )
            text_query = f"{text_query} for {interest_text}"

        payload: dict[str, object] = {
            "textQuery": text_query,
            "includedType": "locality",
            "strictTypeFiltering": True,
            "languageCode": "en",
            "pageSize": self.destination_page_size,
        }

        return self._post_google(
            url=_TEXT_SEARCH_URL,
            field_mask=_DESTINATION_FIELD_MASK,
            payload=payload,
        )

    def search_attractions(
        self,
        destination: Destination,
    ) -> object:
        """Search Google Places for attractions near a destination."""

        payload: dict[str, object] = {
            "includedTypes": ["tourist_attraction"],
            "maxResultCount": self.attraction_max_results,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": destination.coordinates.latitude,
                        "longitude": destination.coordinates.longitude,
                    },
                    "radius": self.attraction_radius_meters,
                },
            },
            "rankPreference": "POPULARITY",
            "languageCode": "en",
        }

        return self._post_google(
            url=_NEARBY_SEARCH_URL,
            field_mask=_ATTRACTION_FIELD_MASK,
            payload=payload,
        )

    def _post_google(
        self,
        *,
        url: str,
        field_mask: str,
        payload: dict[str, object],
    ) -> object:
        """Send a Google Places request and translate HTTP failures."""

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }

        try:
            response = self.transport.post_json(
                url=url,
                headers=headers,
                payload=payload,
                timeout_seconds=self.timeout_seconds,
            )
        except JsonHttpDecodeError as exc:
            raise ProviderResponseError(
                "Google Places returned invalid JSON"
            ) from exc
        except Exception as exc:
            raise ProviderUnavailableError(
                "Google Places request failed"
            ) from exc

        status_code = response.status_code

        if 200 <= status_code < 300:
            return response.payload

        if status_code in {401, 403}:
            raise ProviderAuthenticationError(
                "Google Places authentication failed"
            )

        if status_code == 429:
            raise ProviderRateLimitError(
                "Google Places rate limit exceeded"
            )

        if 400 <= status_code < 500:
            raise ProviderResponseError(
                "Google Places rejected the request"
            )

        if 500 <= status_code < 600:
            raise ProviderUnavailableError(
                "Google Places service unavailable"
            )

        raise ProviderResponseError(
            "Google Places returned unexpected HTTP status"
        )


@dataclass(slots=True)
class GooglePlacesProvider:
    """Google-backed implementation of Solara's places-provider contract.

    The injected client owns transport concerns. This adapter is responsible
    only for normalizing responses and translating infrastructure failures into
    Solara's provider error hierarchy.
    """

    client: GooglePlacesClient

    def discover_destinations(
        self,
        request: RecommendationRequest,
    ) -> tuple[Destination, ...]:
        """Discover and normalize destinations using the injected client."""

        try:
            response = self.client.search_destinations(request)
            places = _extract_places(response)

            return tuple(
                normalize_google_destination(place)
                for place in places
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                "Google Places request failed"
            ) from exc

    def discover_attractions(
        self,
        destination: Destination,
    ) -> tuple[Attraction, ...]:
        """Discover and normalize attractions using the injected client."""

        try:
            response = self.client.search_attractions(destination)
            places = _extract_places(response)

            return tuple(
                normalize_google_attraction(place)
                for place in places
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                "Google Places request failed"
            ) from exc


def normalize_google_destination(
    payload: Mapping[str, object],
) -> Destination:
    """Normalize a Google Places result into a Solara Destination."""

    place = _require_place_mapping(payload)
    name = _extract_display_name(place)
    coordinates = _extract_coordinates(place)
    country = _extract_country(place)

    return Destination(
        name=name,
        country=country,
        coordinates=coordinates,
    )


def normalize_google_attraction(
    payload: Mapping[str, object],
) -> Attraction:
    """Normalize a Google Places result into a Solara Attraction."""

    place = _require_place_mapping(payload)
    name = _extract_display_name(place)
    coordinates = _extract_coordinates(place)
    category = _extract_attraction_category(place)

    return Attraction(
        name=name,
        category=category,
        coordinates=coordinates,
    )


def _extract_places(
    response: object,
) -> list[object]:
    """Extract the places collection from a raw Google search response."""

    if not isinstance(response, Mapping):
        raise ProviderResponseError(
            "Google Places response must be an object"
        )

    if "places" not in response:
        return []

    places = response["places"]

    if not isinstance(places, list):
        raise ProviderResponseError(
            "Google Places response places must be a list"
        )

    return places


def _require_place_mapping(
    payload: object,
) -> Mapping[str, object]:
    """Return a provider place object or raise a normalized response error."""

    if not isinstance(payload, Mapping):
        raise ProviderResponseError(
            "Google place must be an object"
        )

    return payload


def _extract_display_name(
    place: Mapping[str, object],
) -> str:
    """Extract and normalize Google's localized display-name text."""

    display_name = place.get("displayName")

    if not isinstance(display_name, Mapping):
        raise ProviderResponseError(
            "Google place displayName must be an object"
        )

    text = display_name.get("text")

    if not isinstance(text, str) or not text.strip():
        raise ProviderResponseError(
            "Google place display name must be a non-blank string"
        )

    return text.strip()


def _extract_coordinates(
    place: Mapping[str, object],
) -> GeoCoordinates:
    """Extract Google coordinates and normalize domain validation failures."""

    location = place.get("location")

    if not isinstance(location, Mapping):
        raise ProviderResponseError(
            "Google place location must be an object"
        )

    latitude = location.get("latitude")
    longitude = location.get("longitude")

    if (
        not isinstance(latitude, Real)
        or isinstance(latitude, bool)
        or not isinstance(longitude, Real)
        or isinstance(longitude, bool)
    ):
        raise ProviderResponseError(
            "Google place contains invalid coordinates"
        )

    try:
        return GeoCoordinates(
            latitude=latitude,
            longitude=longitude,
        )
    except (TypeError, ValueError) as exc:
        raise ProviderResponseError(
            "Google place contains invalid coordinates"
        ) from exc


def _extract_country(
    place: Mapping[str, object],
) -> str:
    """Extract the explicit country address component from a Google place."""

    address_components = place.get("addressComponents")

    if not isinstance(address_components, list):
        raise ProviderResponseError(
            "Google destination is missing a country"
        )

    for component in address_components:
        if not isinstance(component, Mapping):
            continue

        types = component.get("types")

        if not isinstance(types, list) or "country" not in types:
            continue

        long_text = component.get("longText")

        if isinstance(long_text, str) and long_text.strip():
            return long_text.strip()

        short_text = component.get("shortText")

        if isinstance(short_text, str) and short_text.strip():
            return short_text.strip()

    raise ProviderResponseError(
        "Google destination is missing a country"
    )


def _extract_attraction_category(
    place: Mapping[str, object],
) -> str:
    """Return a stable human-readable attraction category."""

    primary_type = place.get("primaryType")

    if isinstance(primary_type, str) and primary_type.strip():
        return _normalize_category(primary_type)

    types = place.get("types")

    if isinstance(types, list):
        for place_type in types:
            if (
                not isinstance(place_type, str)
                or not place_type.strip()
            ):
                continue

            normalized_type = place_type.strip().casefold()

            if normalized_type in _GENERIC_GOOGLE_PLACE_TYPES:
                continue

            return _normalize_category(place_type)

    return "attraction"


def _normalize_category(value: str) -> str:
    """Normalize a Google place type into stable display text."""

    return value.strip().casefold().replace("_", " ")
