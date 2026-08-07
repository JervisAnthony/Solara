"""Tests for geographic coordinate domain values."""

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from solara_travel.domain.geography import GeoCoordinates


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (0.0, 0.0),
        (12.9716, 77.5946),
        (-33.8688, 151.2093),
        (90.0, 180.0),
        (-90.0, -180.0),
    ],
)
def test_geo_coordinates_accept_valid_values(
    latitude: float,
    longitude: float,
) -> None:
    """Coordinates within geographic bounds should be accepted."""

    coordinates = GeoCoordinates(
        latitude=latitude,
        longitude=longitude,
    )

    assert coordinates.latitude == latitude
    assert coordinates.longitude == longitude


@pytest.mark.parametrize(
    "latitude",
    [
        -90.0001,
        90.0001,
        -180.0,
        180.0,
    ],
)
def test_geo_coordinates_reject_latitude_outside_valid_range(
    latitude: float,
) -> None:
    """Latitude must remain between -90 and 90 degrees inclusive."""

    with pytest.raises(
        ValueError,
        match="latitude must be between -90 and 90 degrees",
    ):
        GeoCoordinates(latitude=latitude, longitude=0.0)


@pytest.mark.parametrize(
    "longitude",
    [
        -180.0001,
        180.0001,
        -360.0,
        360.0,
    ],
)
def test_geo_coordinates_reject_longitude_outside_valid_range(
    longitude: float,
) -> None:
    """Longitude must remain between -180 and 180 degrees inclusive."""

    with pytest.raises(
        ValueError,
        match="longitude must be between -180 and 180 degrees",
    ):
        GeoCoordinates(latitude=0.0, longitude=longitude)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (nan, 0.0),
        (inf, 0.0),
        (-inf, 0.0),
        (0.0, nan),
        (0.0, inf),
        (0.0, -inf),
    ],
)
def test_geo_coordinates_reject_non_finite_values(
    latitude: float,
    longitude: float,
) -> None:
    """NaN and infinite coordinates are not meaningful geographic values."""

    with pytest.raises(
        ValueError,
        match="coordinates must be finite numbers",
    ):
        GeoCoordinates(
            latitude=latitude,
            longitude=longitude,
        )


def test_geo_coordinates_use_value_equality() -> None:
    """Coordinates with equal component values should compare equally."""

    first = GeoCoordinates(latitude=12.9716, longitude=77.5946)
    second = GeoCoordinates(latitude=12.9716, longitude=77.5946)

    assert first == second


def test_geo_coordinates_are_hashable() -> None:
    """Coordinates should be usable as immutable domain values."""

    coordinates = GeoCoordinates(latitude=12.9716, longitude=77.5946)

    assert {coordinates, coordinates} == {coordinates}


def test_geo_coordinates_are_immutable() -> None:
    """A geographic coordinate value must not change after construction."""

    coordinates = GeoCoordinates(latitude=12.9716, longitude=77.5946)

    with pytest.raises(FrozenInstanceError):
        coordinates.latitude = 13.0