"""Tests for normalized weather-domain values."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime
from math import inf, nan

import pytest

from solara_travel.domain.weather import WeatherObservation


def test_weather_observation_accepts_valid_values() -> None:
    """A daily weather observation should preserve normalized weather values."""

    observation = WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=24.5,
        relative_humidity_percent=68.0,
        precipitation_mm=3.2,
    )

    assert observation.observed_on == date(2026, 8, 8)
    assert observation.temperature_celsius == 24.5
    assert observation.relative_humidity_percent == 68.0
    assert observation.precipitation_mm == 3.2


@pytest.mark.parametrize(
    "observed_on",
    [
        None,
        "2026-08-08",
        20260808,
        datetime(2026, 8, 8, 12, 30),
    ],
)
def test_weather_observation_rejects_invalid_date(
    observed_on: object,
) -> None:
    """Weather observations require a pure calendar date."""

    with pytest.raises(
        TypeError,
        match="observed_on must be a date",
    ):
        WeatherObservation(
            observed_on=observed_on,  # type: ignore[arg-type]
            temperature_celsius=24.5,
            relative_humidity_percent=68.0,
            precipitation_mm=3.2,
        )


@pytest.mark.parametrize(
    "temperature_celsius",
    [
        -100.0,
        -50.0,
        0.0,
        25.0,
        60.0,
    ],
)
def test_weather_observation_accepts_temperature_boundaries(
    temperature_celsius: float,
) -> None:
    """Normalized air temperature may span Solara's supported range."""

    observation = WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=temperature_celsius,
        relative_humidity_percent=68.0,
        precipitation_mm=3.2,
    )

    assert observation.temperature_celsius == temperature_celsius


@pytest.mark.parametrize(
    "temperature_celsius",
    [
        -100.0001,
        -150.0,
        60.0001,
        100.0,
    ],
)
def test_weather_observation_rejects_temperature_outside_supported_range(
    temperature_celsius: float,
) -> None:
    """Temperatures outside plausible terrestrial travel conditions are invalid."""

    with pytest.raises(
        ValueError,
        match="temperature_celsius must be between -100 and 60",
    ):
        WeatherObservation(
            observed_on=date(2026, 8, 8),
            temperature_celsius=temperature_celsius,
            relative_humidity_percent=68.0,
            precipitation_mm=3.2,
        )


@pytest.mark.parametrize(
    "temperature_celsius",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_weather_observation_rejects_non_finite_temperature(
    temperature_celsius: float,
) -> None:
    """NaN and infinite temperatures are not meaningful weather evidence."""

    with pytest.raises(
        ValueError,
        match="temperature_celsius must be a finite number",
    ):
        WeatherObservation(
            observed_on=date(2026, 8, 8),
            temperature_celsius=temperature_celsius,
            relative_humidity_percent=68.0,
            precipitation_mm=3.2,
        )


@pytest.mark.parametrize(
    "temperature_celsius",
    [
        None,
        "24.5",
        [24.5],
        True,
    ],
)
def test_weather_observation_rejects_non_numeric_temperature(
    temperature_celsius: object,
) -> None:
    """Temperature must be represented by a real numeric value."""

    with pytest.raises(
        TypeError,
        match="temperature_celsius must be a real number",
    ):
        WeatherObservation(
            observed_on=date(2026, 8, 8),
            temperature_celsius=temperature_celsius,  # type: ignore[arg-type]
            relative_humidity_percent=68.0,
            precipitation_mm=3.2,
        )


@pytest.mark.parametrize(
    "relative_humidity_percent",
    [
        0.0,
        25.0,
        50.0,
        75.0,
        100.0,
    ],
)
def test_weather_observation_accepts_humidity_boundaries(
    relative_humidity_percent: float,
) -> None:
    """Relative humidity may span the inclusive percentage range."""

    observation = WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=24.5,
        relative_humidity_percent=relative_humidity_percent,
        precipitation_mm=3.2,
    )

    assert observation.relative_humidity_percent == relative_humidity_percent


@pytest.mark.parametrize(
    "relative_humidity_percent",
    [
        -0.0001,
        -1.0,
        100.0001,
        101.0,
    ],
)
def test_weather_observation_rejects_humidity_outside_percentage_range(
    relative_humidity_percent: float,
) -> None:
    """Relative humidity must remain between zero and one hundred percent."""

    with pytest.raises(
        ValueError,
        match="relative_humidity_percent must be between 0 and 100",
    ):
        WeatherObservation(
            observed_on=date(2026, 8, 8),
            temperature_celsius=24.5,
            relative_humidity_percent=relative_humidity_percent,
            precipitation_mm=3.2,
        )


@pytest.mark.parametrize(
    "relative_humidity_percent",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_weather_observation_rejects_non_finite_humidity(
    relative_humidity_percent: float,
) -> None:
    """NaN and infinite humidity values are invalid weather evidence."""

    with pytest.raises(
        ValueError,
        match="relative_humidity_percent must be a finite number",
    ):
        WeatherObservation(
            observed_on=date(2026, 8, 8),
            temperature_celsius=24.5,
            relative_humidity_percent=relative_humidity_percent,
            precipitation_mm=3.2,
        )


@pytest.mark.parametrize(
    "relative_humidity_percent",
    [
        None,
        "68.0",
        [68.0],
        True,
    ],
)
def test_weather_observation_rejects_non_numeric_humidity(
    relative_humidity_percent: object,
) -> None:
    """Relative humidity must be represented by a real numeric value."""

    with pytest.raises(
        TypeError,
        match="relative_humidity_percent must be a real number",
    ):
        WeatherObservation(
            observed_on=date(2026, 8, 8),
            temperature_celsius=24.5,
            relative_humidity_percent=relative_humidity_percent,  # type: ignore[arg-type]
            precipitation_mm=3.2,
        )


@pytest.mark.parametrize(
    "precipitation_mm",
    [
        0.0,
        0.1,
        3.2,
        50.0,
        500.0,
    ],
)
def test_weather_observation_accepts_non_negative_precipitation(
    precipitation_mm: float,
) -> None:
    """Daily precipitation may be zero or any finite non-negative amount."""

    observation = WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=24.5,
        relative_humidity_percent=68.0,
        precipitation_mm=precipitation_mm,
    )

    assert observation.precipitation_mm == precipitation_mm


@pytest.mark.parametrize(
    "precipitation_mm",
    [
        -0.0001,
        -1.0,
        -100.0,
    ],
)
def test_weather_observation_rejects_negative_precipitation(
    precipitation_mm: float,
) -> None:
    """Accumulated precipitation cannot be negative."""

    with pytest.raises(
        ValueError,
        match="precipitation_mm must not be negative",
    ):
        WeatherObservation(
            observed_on=date(2026, 8, 8),
            temperature_celsius=24.5,
            relative_humidity_percent=68.0,
            precipitation_mm=precipitation_mm,
        )


@pytest.mark.parametrize(
    "precipitation_mm",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_weather_observation_rejects_non_finite_precipitation(
    precipitation_mm: float,
) -> None:
    """NaN and infinite precipitation values are invalid weather evidence."""

    with pytest.raises(
        ValueError,
        match="precipitation_mm must be a finite number",
    ):
        WeatherObservation(
            observed_on=date(2026, 8, 8),
            temperature_celsius=24.5,
            relative_humidity_percent=68.0,
            precipitation_mm=precipitation_mm,
        )


@pytest.mark.parametrize(
    "precipitation_mm",
    [
        None,
        "3.2",
        [3.2],
        True,
    ],
)
def test_weather_observation_rejects_non_numeric_precipitation(
    precipitation_mm: object,
) -> None:
    """Precipitation must be represented by a real numeric value."""

    with pytest.raises(
        TypeError,
        match="precipitation_mm must be a real number",
    ):
        WeatherObservation(
            observed_on=date(2026, 8, 8),
            temperature_celsius=24.5,
            relative_humidity_percent=68.0,
            precipitation_mm=precipitation_mm,  # type: ignore[arg-type]
        )


def test_weather_observation_uses_value_equality() -> None:
    """Equivalent observations should compare equally."""

    first = WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=24.5,
        relative_humidity_percent=68.0,
        precipitation_mm=3.2,
    )
    second = WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=24.5,
        relative_humidity_percent=68.0,
        precipitation_mm=3.2,
    )

    assert first == second


def test_weather_observation_is_hashable() -> None:
    """Weather observations should be usable in immutable collections."""

    observation = WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=24.5,
        relative_humidity_percent=68.0,
        precipitation_mm=3.2,
    )

    assert {observation, observation} == {observation}


def test_weather_observation_is_immutable() -> None:
    """Normalized weather evidence must not change after construction."""

    observation = WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=24.5,
        relative_humidity_percent=68.0,
        precipitation_mm=3.2,
    )

    with pytest.raises(FrozenInstanceError):
        observation.temperature_celsius = 30.0