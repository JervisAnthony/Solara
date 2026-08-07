"""Tests for destination domain entities."""

from dataclasses import FrozenInstanceError

import pytest

from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates


def test_destination_accepts_valid_values() -> None:
    """A destination should preserve its defining travel-domain values."""

    coordinates = GeoCoordinates(
        latitude=35.6762,
        longitude=139.6503,
    )

    destination = Destination(
        name="Tokyo",
        country="Japan",
        coordinates=coordinates,
    )

    assert destination.name == "Tokyo"
    assert destination.country == "Japan"
    assert destination.coordinates == coordinates


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_destination_rejects_blank_name(name: str) -> None:
    """A destination requires a meaningful non-blank name."""

    with pytest.raises(
        ValueError,
        match="destination name must not be blank",
    ):
        Destination(
            name=name,
            country="Japan",
            coordinates=GeoCoordinates(
                latitude=35.6762,
                longitude=139.6503,
            ),
        )


@pytest.mark.parametrize(
    "country",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_destination_rejects_blank_country(country: str) -> None:
    """A destination requires a meaningful country name."""

    with pytest.raises(
        ValueError,
        match="destination country must not be blank",
    ):
        Destination(
            name="Tokyo",
            country=country,
            coordinates=GeoCoordinates(
                latitude=35.6762,
                longitude=139.6503,
            ),
        )


@pytest.mark.parametrize(
    ("name", "country"),
    [
        (None, "Japan"),
        (123, "Japan"),
        (["Tokyo"], "Japan"),
        ("Tokyo", None),
        ("Tokyo", 123),
        ("Tokyo", ["Japan"]),
    ],
)
def test_destination_rejects_non_string_name_or_country(
    name: object,
    country: object,
) -> None:
    """Destination names and countries must be strings."""

    with pytest.raises(
        TypeError,
        match="destination name and country must be strings",
    ):
        Destination(
            name=name,  # type: ignore[arg-type]
            country=country,  # type: ignore[arg-type]
            coordinates=GeoCoordinates(
                latitude=35.6762,
                longitude=139.6503,
            ),
        )


def test_destination_rejects_invalid_coordinates_type() -> None:
    """Destination coordinates must use Solara's geographic value object."""

    with pytest.raises(
        TypeError,
        match="destination coordinates must be GeoCoordinates",
    ):
        Destination(
            name="Tokyo",
            country="Japan",
            coordinates=(35.6762, 139.6503),  # type: ignore[arg-type]
        )


def test_destination_uses_value_equality() -> None:
    """Destinations with identical values should compare equally."""

    coordinates = GeoCoordinates(
        latitude=35.6762,
        longitude=139.6503,
    )

    first = Destination(
        name="Tokyo",
        country="Japan",
        coordinates=coordinates,
    )
    second = Destination(
        name="Tokyo",
        country="Japan",
        coordinates=coordinates,
    )

    assert first == second


def test_destination_is_hashable() -> None:
    """A destination should be usable in immutable collections."""

    destination = Destination(
        name="Tokyo",
        country="Japan",
        coordinates=GeoCoordinates(
            latitude=35.6762,
            longitude=139.6503,
        ),
    )

    assert {destination, destination} == {destination}


def test_destination_is_immutable() -> None:
    """Destination identity values must not change after construction."""

    destination = Destination(
        name="Tokyo",
        country="Japan",
        coordinates=GeoCoordinates(
            latitude=35.6762,
            longitude=139.6503,
        ),
    )

    with pytest.raises(FrozenInstanceError):
        destination.name = "Kyoto"