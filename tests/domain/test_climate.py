"""Tests for climate-comfort domain values."""

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from solara_travel.domain.climate import TemperatureComfortRange


def test_temperature_comfort_range_accepts_valid_values() -> None:
    """A comfort range should preserve its configured temperature boundaries."""

    comfort_range = TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=10.0,
    )

    assert comfort_range.minimum_celsius == 18.0
    assert comfort_range.maximum_celsius == 28.0
    assert comfort_range.tolerance_celsius == 10.0


@pytest.mark.parametrize(
    ("minimum_celsius", "maximum_celsius"),
    [
        (-100.0, -100.0),
        (-100.0, 60.0),
        (0.0, 0.0),
        (18.0, 28.0),
        (60.0, 60.0),
    ],
)
def test_temperature_comfort_range_accepts_supported_boundaries(
    minimum_celsius: float,
    maximum_celsius: float,
) -> None:
    """Comfort boundaries may span Solara's supported temperature domain."""

    comfort_range = TemperatureComfortRange(
        minimum_celsius=minimum_celsius,
        maximum_celsius=maximum_celsius,
        tolerance_celsius=10.0,
    )

    assert comfort_range.minimum_celsius == minimum_celsius
    assert comfort_range.maximum_celsius == maximum_celsius


@pytest.mark.parametrize(
    "minimum_celsius",
    [
        -100.0001,
        -150.0,
        60.0001,
        100.0,
    ],
)
def test_temperature_comfort_range_rejects_minimum_outside_supported_range(
    minimum_celsius: float,
) -> None:
    """Minimum comfort temperature must remain in the supported domain."""

    with pytest.raises(
        ValueError,
        match="minimum_celsius must be between -100 and 60",
    ):
        TemperatureComfortRange(
            minimum_celsius=minimum_celsius,
            maximum_celsius=28.0,
            tolerance_celsius=10.0,
        )


@pytest.mark.parametrize(
    "maximum_celsius",
    [
        -100.0001,
        -150.0,
        60.0001,
        100.0,
    ],
)
def test_temperature_comfort_range_rejects_maximum_outside_supported_range(
    maximum_celsius: float,
) -> None:
    """Maximum comfort temperature must remain in the supported domain."""

    with pytest.raises(
        ValueError,
        match="maximum_celsius must be between -100 and 60",
    ):
        TemperatureComfortRange(
            minimum_celsius=18.0,
            maximum_celsius=maximum_celsius,
            tolerance_celsius=10.0,
        )


@pytest.mark.parametrize(
    "minimum_celsius",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_temperature_comfort_range_rejects_non_finite_minimum(
    minimum_celsius: float,
) -> None:
    """A minimum comfort boundary must be finite."""

    with pytest.raises(
        ValueError,
        match="minimum_celsius must be a finite number",
    ):
        TemperatureComfortRange(
            minimum_celsius=minimum_celsius,
            maximum_celsius=28.0,
            tolerance_celsius=10.0,
        )


@pytest.mark.parametrize(
    "maximum_celsius",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_temperature_comfort_range_rejects_non_finite_maximum(
    maximum_celsius: float,
) -> None:
    """A maximum comfort boundary must be finite."""

    with pytest.raises(
        ValueError,
        match="maximum_celsius must be a finite number",
    ):
        TemperatureComfortRange(
            minimum_celsius=18.0,
            maximum_celsius=maximum_celsius,
            tolerance_celsius=10.0,
        )


@pytest.mark.parametrize(
    "minimum_celsius",
    [
        None,
        "18.0",
        [18.0],
        True,
    ],
)
def test_temperature_comfort_range_rejects_non_numeric_minimum(
    minimum_celsius: object,
) -> None:
    """Minimum comfort temperature must be a real numeric value."""

    with pytest.raises(
        TypeError,
        match="minimum_celsius must be a real number",
    ):
        TemperatureComfortRange(
            minimum_celsius=minimum_celsius,  # type: ignore[arg-type]
            maximum_celsius=28.0,
            tolerance_celsius=10.0,
        )


@pytest.mark.parametrize(
    "maximum_celsius",
    [
        None,
        "28.0",
        [28.0],
        True,
    ],
)
def test_temperature_comfort_range_rejects_non_numeric_maximum(
    maximum_celsius: object,
) -> None:
    """Maximum comfort temperature must be a real numeric value."""

    with pytest.raises(
        TypeError,
        match="maximum_celsius must be a real number",
    ):
        TemperatureComfortRange(
            minimum_celsius=18.0,
            maximum_celsius=maximum_celsius,  # type: ignore[arg-type]
            tolerance_celsius=10.0,
        )


def test_temperature_comfort_range_rejects_reversed_boundaries() -> None:
    """The minimum comfort boundary cannot exceed the maximum."""

    with pytest.raises(
        ValueError,
        match="minimum_celsius must not exceed maximum_celsius",
    ):
        TemperatureComfortRange(
            minimum_celsius=29.0,
            maximum_celsius=28.0,
            tolerance_celsius=10.0,
        )


@pytest.mark.parametrize(
    "tolerance_celsius",
    [
        0.0001,
        1.0,
        10.0,
        50.0,
        160.0,
    ],
)
def test_temperature_comfort_range_accepts_positive_tolerance(
    tolerance_celsius: float,
) -> None:
    """Tolerance may be any finite positive temperature distance."""

    comfort_range = TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=tolerance_celsius,
    )

    assert comfort_range.tolerance_celsius == tolerance_celsius


@pytest.mark.parametrize(
    "tolerance_celsius",
    [
        0.0,
        -0.0001,
        -1.0,
        -10.0,
    ],
)
def test_temperature_comfort_range_rejects_non_positive_tolerance(
    tolerance_celsius: float,
) -> None:
    """Comfort degradation requires a strictly positive tolerance."""

    with pytest.raises(
        ValueError,
        match="tolerance_celsius must be greater than zero",
    ):
        TemperatureComfortRange(
            minimum_celsius=18.0,
            maximum_celsius=28.0,
            tolerance_celsius=tolerance_celsius,
        )


@pytest.mark.parametrize(
    "tolerance_celsius",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_temperature_comfort_range_rejects_non_finite_tolerance(
    tolerance_celsius: float,
) -> None:
    """Tolerance must be finite."""

    with pytest.raises(
        ValueError,
        match="tolerance_celsius must be a finite number",
    ):
        TemperatureComfortRange(
            minimum_celsius=18.0,
            maximum_celsius=28.0,
            tolerance_celsius=tolerance_celsius,
        )


@pytest.mark.parametrize(
    "tolerance_celsius",
    [
        None,
        "10.0",
        [10.0],
        True,
    ],
)
def test_temperature_comfort_range_rejects_non_numeric_tolerance(
    tolerance_celsius: object,
) -> None:
    """Tolerance must be represented by a real numeric value."""

    with pytest.raises(
        TypeError,
        match="tolerance_celsius must be a real number",
    ):
        TemperatureComfortRange(
            minimum_celsius=18.0,
            maximum_celsius=28.0,
            tolerance_celsius=tolerance_celsius,  # type: ignore[arg-type]
        )


def test_temperature_comfort_range_uses_value_equality() -> None:
    """Equivalent comfort ranges should compare equally."""

    first = TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=10.0,
    )
    second = TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=10.0,
    )

    assert first == second


def test_temperature_comfort_range_is_hashable() -> None:
    """Comfort ranges should be usable in immutable collections."""

    comfort_range = TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=10.0,
    )

    assert {comfort_range, comfort_range} == {comfort_range}


def test_temperature_comfort_range_is_immutable() -> None:
    """Climate-comfort policy must not change after construction."""

    comfort_range = TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=10.0,
    )

    with pytest.raises(FrozenInstanceError):
        comfort_range.minimum_celsius = 20.0