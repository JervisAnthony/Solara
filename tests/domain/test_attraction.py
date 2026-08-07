"""Tests for attraction domain entities."""

from dataclasses import FrozenInstanceError

import pytest

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.geography import GeoCoordinates


def test_attraction_accepts_valid_values() -> None:
    """An attraction should preserve its defining travel-domain values."""

    coordinates = GeoCoordinates(
        latitude=35.6586,
        longitude=139.7454,
    )

    attraction = Attraction(
        name="Tokyo Tower",
        category="landmark",
        coordinates=coordinates,
    )

    assert attraction.name == "Tokyo Tower"
    assert attraction.category == "landmark"
    assert attraction.coordinates == coordinates


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
def test_attraction_rejects_blank_name(name: str) -> None:
    """An attraction requires a meaningful non-blank name."""

    with pytest.raises(
        ValueError,
        match="attraction name must not be blank",
    ):
        Attraction(
            name=name,
            category="landmark",
            coordinates=GeoCoordinates(
                latitude=35.6586,
                longitude=139.7454,
            ),
        )


@pytest.mark.parametrize(
    "category",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_attraction_rejects_blank_category(category: str) -> None:
    """An attraction requires a meaningful category."""

    with pytest.raises(
        ValueError,
        match="attraction category must not be blank",
    ):
        Attraction(
            name="Tokyo Tower",
            category=category,
            coordinates=GeoCoordinates(
                latitude=35.6586,
                longitude=139.7454,
            ),
        )


@pytest.mark.parametrize(
    ("name", "category"),
    [
        (None, "landmark"),
        (123, "landmark"),
        (["Tokyo Tower"], "landmark"),
        ("Tokyo Tower", None),
        ("Tokyo Tower", 123),
        ("Tokyo Tower", ["landmark"]),
    ],
)
def test_attraction_rejects_non_string_name_or_category(
    name: object,
    category: object,
) -> None:
    """Attraction names and categories must be strings."""

    with pytest.raises(
        TypeError,
        match="attraction name and category must be strings",
    ):
        Attraction(
            name=name,  # type: ignore[arg-type]
            category=category,  # type: ignore[arg-type]
            coordinates=GeoCoordinates(
                latitude=35.6586,
                longitude=139.7454,
            ),
        )


def test_attraction_rejects_invalid_coordinates_type() -> None:
    """Attraction coordinates must use Solara's geographic value object."""

    with pytest.raises(
        TypeError,
        match="attraction coordinates must be GeoCoordinates",
    ):
        Attraction(
            name="Tokyo Tower",
            category="landmark",
            coordinates=(35.6586, 139.7454),  # type: ignore[arg-type]
        )


def test_attraction_preserves_meaningful_whitespace_inside_name() -> None:
    """Validation should not alter meaningful internal name whitespace."""

    attraction = Attraction(
        name="Tokyo National Museum",
        category="museum",
        coordinates=GeoCoordinates(
            latitude=35.7188,
            longitude=139.7765,
        ),
    )

    assert attraction.name == "Tokyo National Museum"


def test_attraction_uses_value_equality() -> None:
    """Attractions with identical values should compare equally."""

    coordinates = GeoCoordinates(
        latitude=35.6586,
        longitude=139.7454,
    )

    first = Attraction(
        name="Tokyo Tower",
        category="landmark",
        coordinates=coordinates,
    )
    second = Attraction(
        name="Tokyo Tower",
        category="landmark",
        coordinates=coordinates,
    )

    assert first == second


def test_attraction_is_hashable() -> None:
    """An attraction should be usable in immutable collections."""

    attraction = Attraction(
        name="Tokyo Tower",
        category="landmark",
        coordinates=GeoCoordinates(
            latitude=35.6586,
            longitude=139.7454,
        ),
    )

    assert {attraction, attraction} == {attraction}


def test_attraction_is_immutable() -> None:
    """Attraction values must not change after construction."""

    attraction = Attraction(
        name="Tokyo Tower",
        category="landmark",
        coordinates=GeoCoordinates(
            latitude=35.6586,
            longitude=139.7454,
        ),
    )

    with pytest.raises(FrozenInstanceError):
        attraction.name = "Tokyo Skytree"