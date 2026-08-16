"""Tests for normalizing Google Places responses into Solara domain values."""

from copy import deepcopy

import pytest

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.infrastructure.places.google import (
    normalize_google_attraction,
    normalize_google_destination,
)
from solara_travel.ports.errors import ProviderResponseError


def _destination_payload() -> dict[str, object]:
    """Return representative Google Places data for a destination."""

    return {
        "id": "google-kyoto",
        "displayName": {
            "text": "Kyoto",
            "languageCode": "en",
        },
        "location": {
            "latitude": 35.0116,
            "longitude": 135.7681,
        },
        "addressComponents": [
            {
                "longText": "Kyoto",
                "shortText": "Kyoto",
                "types": ["locality", "political"],
                "languageCode": "en",
            },
            {
                "longText": "Japan",
                "shortText": "JP",
                "types": ["country", "political"],
                "languageCode": "en",
            },
        ],
        "types": [
            "locality",
            "political",
        ],
    }


def _attraction_payload() -> dict[str, object]:
    """Return representative Google Places data for an attraction."""

    return {
        "id": "google-fushimi-inari",
        "displayName": {
            "text": "Fushimi Inari Taisha",
            "languageCode": "en",
        },
        "location": {
            "latitude": 34.9671,
            "longitude": 135.7727,
        },
        "primaryType": "shinto_shrine",
        "types": [
            "shinto_shrine",
            "tourist_attraction",
            "place_of_worship",
            "point_of_interest",
            "establishment",
        ],
    }


def test_normalize_google_destination_returns_destination() -> None:
    """Google destination data should become a Solara Destination."""

    destination = normalize_google_destination(_destination_payload())

    assert isinstance(destination, Destination)


def test_normalize_google_destination_maps_name() -> None:
    """Google display names should populate the destination name."""

    destination = normalize_google_destination(_destination_payload())

    assert destination.name == "Kyoto"


def test_normalize_google_destination_maps_country() -> None:
    """The country address component should populate destination country."""

    destination = normalize_google_destination(_destination_payload())

    assert destination.country == "Japan"


def test_normalize_google_destination_maps_coordinates() -> None:
    """Google coordinates should become Solara-owned GeoCoordinates."""

    destination = normalize_google_destination(_destination_payload())

    assert destination.coordinates == GeoCoordinates(
        latitude=35.0116,
        longitude=135.7681,
    )


def test_normalize_google_destination_strips_provider_text() -> None:
    """Provider formatting whitespace should not enter normalized domain values."""

    payload = _destination_payload()
    payload["displayName"] = {
        "text": "  Kyoto  ",
        "languageCode": "en",
    }
    payload["addressComponents"] = [
        {
            "longText": "  Japan  ",
            "shortText": "JP",
            "types": ["country", "political"],
        },
    ]

    destination = normalize_google_destination(payload)

    assert destination.name == "Kyoto"
    assert destination.country == "Japan"


def test_normalize_google_destination_uses_country_short_text_fallback() -> None:
    """Country short text should be usable when long text is unavailable."""

    payload = _destination_payload()
    payload["addressComponents"] = [
        {
            "shortText": "JP",
            "types": ["country", "political"],
        },
    ]

    destination = normalize_google_destination(payload)

    assert destination.country == "JP"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "Kyoto",
        ["Kyoto"],
        42,
    ],
)
def test_normalize_google_destination_rejects_non_mapping_payload(
    payload: object,
) -> None:
    """External destination responses must have the expected object shape."""

    with pytest.raises(
        ProviderResponseError,
        match="Google place must be an object",
    ):
        normalize_google_destination(payload)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "display_name",
    [
        None,
        "Kyoto",
        [],
        42,
    ],
)
def test_normalize_google_destination_rejects_invalid_display_name_object(
    display_name: object,
) -> None:
    """Google displayName must be an object containing normalized text."""

    payload = _destination_payload()
    payload["displayName"] = display_name

    with pytest.raises(
        ProviderResponseError,
        match="Google place displayName must be an object",
    ):
        normalize_google_destination(payload)


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        " ",
        "\t",
        42,
        [],
    ],
)
def test_normalize_google_destination_rejects_invalid_name(
    text: object,
) -> None:
    """A provider place requires a meaningful display name."""

    payload = _destination_payload()
    payload["displayName"] = {"text": text}

    with pytest.raises(
        ProviderResponseError,
        match="Google place display name must be a non-blank string",
    ):
        normalize_google_destination(payload)


@pytest.mark.parametrize(
    "location",
    [
        None,
        "35.0116,135.7681",
        [],
        42,
    ],
)
def test_normalize_google_destination_rejects_invalid_location_object(
    location: object,
) -> None:
    """Google location data must use the expected coordinate object."""

    payload = _destination_payload()
    payload["location"] = location

    with pytest.raises(
        ProviderResponseError,
        match="Google place location must be an object",
    ):
        normalize_google_destination(payload)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (None, 135.7681),
        (35.0116, None),
        ("35.0116", 135.7681),
        (35.0116, "135.7681"),
        (91.0, 135.7681),
        (35.0116, 181.0),
    ],
)
def test_normalize_google_destination_rejects_invalid_coordinates(
    latitude: object,
    longitude: object,
) -> None:
    """Malformed provider coordinates must become provider response failures."""

    payload = _destination_payload()
    payload["location"] = {
        "latitude": latitude,
        "longitude": longitude,
    }

    with pytest.raises(
        ProviderResponseError,
        match="Google place contains invalid coordinates",
    ):
        normalize_google_destination(payload)


@pytest.mark.parametrize(
    "address_components",
    [
        None,
        [],
        "Japan",
        [{"longText": "Kyoto", "types": ["locality"]}],
        [{"longText": "Japan", "types": []}],
        [{"longText": "Japan"}],
    ],
)
def test_normalize_google_destination_rejects_missing_country(
    address_components: object,
) -> None:
    """Destination normalization requires an explicit country component."""

    payload = _destination_payload()
    payload["addressComponents"] = address_components

    with pytest.raises(
        ProviderResponseError,
        match="Google destination is missing a country",
    ):
        normalize_google_destination(payload)


def test_normalize_google_destination_ignores_malformed_non_country_components() -> None:
    """Unrelated malformed address components should not block a valid country."""

    payload = _destination_payload()
    payload["addressComponents"] = [
        None,
        "Kyoto",
        {
            "longText": "Kyoto",
            "types": ["locality"],
        },
        {
            "longText": "Japan",
            "shortText": "JP",
            "types": ["country", "political"],
        },
    ]

    destination = normalize_google_destination(payload)

    assert destination.country == "Japan"


def test_normalize_google_destination_skips_unusable_country_component() -> None:
    """An unusable country component should not block a later valid country."""

    payload = _destination_payload()
    payload["addressComponents"] = [
        {
            "longText": " ",
            "shortText": "\t",
            "types": ["country", "political"],
        },
        {
            "longText": "Japan",
            "shortText": "JP",
            "types": ["country", "political"],
        },
    ]

    destination = normalize_google_destination(payload)

    assert destination.country == "Japan"


def test_normalize_google_attraction_returns_attraction() -> None:
    """Google attraction data should become a Solara Attraction."""

    attraction = normalize_google_attraction(_attraction_payload())

    assert isinstance(attraction, Attraction)


def test_normalize_google_attraction_maps_name() -> None:
    """Google display names should populate attraction names."""

    attraction = normalize_google_attraction(_attraction_payload())

    assert attraction.name == "Fushimi Inari Taisha"


def test_normalize_google_attraction_maps_coordinates() -> None:
    """Google attraction coordinates should become GeoCoordinates."""

    attraction = normalize_google_attraction(_attraction_payload())

    assert attraction.coordinates == GeoCoordinates(
        latitude=34.9671,
        longitude=135.7727,
    )


def test_normalize_google_attraction_normalizes_primary_type_category() -> None:
    """Google primary types should become stable human-readable categories."""

    attraction = normalize_google_attraction(_attraction_payload())

    assert attraction.category == "shinto shrine"


def test_normalize_google_attraction_casefolds_category() -> None:
    """Provider category casing should not leak into normalized values."""

    payload = _attraction_payload()
    payload["primaryType"] = "ART_MUSEUM"

    attraction = normalize_google_attraction(payload)

    assert attraction.category == "art museum"


def test_normalize_google_attraction_strips_name() -> None:
    """Provider whitespace should be removed from attraction names."""

    payload = _attraction_payload()
    payload["displayName"] = {
        "text": "  Fushimi Inari Taisha  ",
        "languageCode": "en",
    }

    attraction = normalize_google_attraction(payload)

    assert attraction.name == "Fushimi Inari Taisha"


def test_normalize_google_attraction_uses_specific_type_fallback() -> None:
    """A useful provider type should replace a missing primary type."""

    payload = _attraction_payload()
    payload.pop("primaryType")
    payload["types"] = [
        "point_of_interest",
        "tourist_attraction",
        "establishment",
    ]

    attraction = normalize_google_attraction(payload)

    assert attraction.category == "tourist attraction"


def test_normalize_google_attraction_ignores_generic_fallback_types() -> None:
    """Generic Google types should not become misleading attraction categories."""

    payload = _attraction_payload()
    payload.pop("primaryType")
    payload["types"] = [
        "point_of_interest",
        "establishment",
    ]

    attraction = normalize_google_attraction(payload)

    assert attraction.category == "attraction"


@pytest.mark.parametrize(
    "types",
    [
        None,
        [],
        "tourist_attraction",
        [None, 42, ""],
    ],
)
def test_normalize_google_attraction_uses_default_category(
    types: object,
) -> None:
    """Missing useful provider categories should use a stable domain fallback."""

    payload = _attraction_payload()
    payload.pop("primaryType")
    payload["types"] = types

    attraction = normalize_google_attraction(payload)

    assert attraction.category == "attraction"


def test_normalize_google_attraction_uses_types_when_primary_type_is_blank() -> None:
    """Blank primary types should fall back to another useful provider type."""

    payload = _attraction_payload()
    payload["primaryType"] = "   "
    payload["types"] = [
        "museum",
        "point_of_interest",
        "establishment",
    ]

    attraction = normalize_google_attraction(payload)

    assert attraction.category == "museum"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "Fushimi Inari Taisha",
        ["Fushimi Inari Taisha"],
        42,
    ],
)
def test_normalize_google_attraction_rejects_non_mapping_payload(
    payload: object,
) -> None:
    """External attraction responses must have the expected object shape."""

    with pytest.raises(
        ProviderResponseError,
        match="Google place must be an object",
    ):
        normalize_google_attraction(payload)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        " ",
        42,
        [],
    ],
)
def test_normalize_google_attraction_rejects_invalid_name(
    text: object,
) -> None:
    """Attraction normalization requires a meaningful provider display name."""

    payload = _attraction_payload()
    payload["displayName"] = {"text": text}

    with pytest.raises(
        ProviderResponseError,
        match="Google place display name must be a non-blank string",
    ):
        normalize_google_attraction(payload)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (None, 135.7727),
        (34.9671, None),
        ("34.9671", 135.7727),
        (34.9671, "135.7727"),
        (-91.0, 135.7727),
        (34.9671, -181.0),
    ],
)
def test_normalize_google_attraction_rejects_invalid_coordinates(
    latitude: object,
    longitude: object,
) -> None:
    """Invalid attraction coordinates must become provider response failures."""

    payload = deepcopy(_attraction_payload())
    payload["location"] = {
        "latitude": latitude,
        "longitude": longitude,
    }

    with pytest.raises(
        ProviderResponseError,
        match="Google place contains invalid coordinates",
    ):
        normalize_google_attraction(payload)
