"""Tests for deterministic temperature-comfort intelligence."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from solara_travel.analytics.climate import (
    TemperatureComfortAssessment,
    assess_temperature_comfort,
)
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.weather import WeatherObservation


def _observation(temperature_celsius: float) -> WeatherObservation:
    """Build a weather observation for temperature-comfort tests."""

    return WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=temperature_celsius,
        relative_humidity_percent=60.0,
        precipitation_mm=0.0,
    )


def _comfort_range() -> TemperatureComfortRange:
    """Return the standard preferred range used by comfort tests."""

    return TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=10.0,
    )


@pytest.mark.parametrize(
    "temperature_celsius",
    [
        18.0,
        20.0,
        23.0,
        26.0,
        28.0,
    ],
)
def test_temperature_inside_preferred_range_receives_full_score(
    temperature_celsius: float,
) -> None:
    """Temperatures inside the preferred range should be fully comfortable."""

    assessment = assess_temperature_comfort(
        observation=_observation(temperature_celsius),
        comfort_range=_comfort_range(),
    )

    assert assessment.score == 1.0
    assert assessment.deviation_celsius == 0.0
    assert assessment.within_preferred_range is True


def test_temperature_below_preferred_range_degrades_linearly() -> None:
    """Cooler temperatures should degrade according to configured tolerance."""

    assessment = assess_temperature_comfort(
        observation=_observation(13.0),
        comfort_range=_comfort_range(),
    )

    assert assessment.deviation_celsius == pytest.approx(5.0)
    assert assessment.score == pytest.approx(0.5)
    assert assessment.within_preferred_range is False


def test_temperature_above_preferred_range_degrades_linearly() -> None:
    """Warmer temperatures should degrade according to configured tolerance."""

    assessment = assess_temperature_comfort(
        observation=_observation(33.0),
        comfort_range=_comfort_range(),
    )

    assert assessment.deviation_celsius == pytest.approx(5.0)
    assert assessment.score == pytest.approx(0.5)
    assert assessment.within_preferred_range is False


def test_temperature_at_lower_tolerance_limit_receives_zero_score() -> None:
    """A full tolerance below the preferred range should score zero."""

    assessment = assess_temperature_comfort(
        observation=_observation(8.0),
        comfort_range=_comfort_range(),
    )

    assert assessment.deviation_celsius == pytest.approx(10.0)
    assert assessment.score == 0.0


def test_temperature_at_upper_tolerance_limit_receives_zero_score() -> None:
    """A full tolerance above the preferred range should score zero."""

    assessment = assess_temperature_comfort(
        observation=_observation(38.0),
        comfort_range=_comfort_range(),
    )

    assert assessment.deviation_celsius == pytest.approx(10.0)
    assert assessment.score == 0.0


def test_temperature_beyond_lower_tolerance_remains_zero() -> None:
    """Temperatures beyond the configured cool tolerance remain at zero."""

    assessment = assess_temperature_comfort(
        observation=_observation(0.0),
        comfort_range=_comfort_range(),
    )

    assert assessment.deviation_celsius == pytest.approx(18.0)
    assert assessment.score == 0.0


def test_temperature_beyond_upper_tolerance_remains_zero() -> None:
    """Temperatures beyond the configured warm tolerance remain at zero."""

    assessment = assess_temperature_comfort(
        observation=_observation(50.0),
        comfort_range=_comfort_range(),
    )

    assert assessment.deviation_celsius == pytest.approx(22.0)
    assert assessment.score == 0.0


def test_temperature_comfort_uses_nearest_preferred_boundary() -> None:
    """Deviation should be measured from the nearest preferred boundary."""

    below = assess_temperature_comfort(
        observation=_observation(17.0),
        comfort_range=_comfort_range(),
    )
    above = assess_temperature_comfort(
        observation=_observation(29.0),
        comfort_range=_comfort_range(),
    )

    assert below.deviation_celsius == pytest.approx(1.0)
    assert above.deviation_celsius == pytest.approx(1.0)
    assert below.score == pytest.approx(0.9)
    assert above.score == pytest.approx(0.9)


def test_temperature_comfort_supports_single_point_preference() -> None:
    """A zero-width preferred range should still degrade deterministically."""

    comfort_range = TemperatureComfortRange(
        minimum_celsius=22.0,
        maximum_celsius=22.0,
        tolerance_celsius=5.0,
    )

    exact = assess_temperature_comfort(
        observation=_observation(22.0),
        comfort_range=comfort_range,
    )
    nearby = assess_temperature_comfort(
        observation=_observation(24.5),
        comfort_range=comfort_range,
    )

    assert exact.score == 1.0
    assert exact.deviation_celsius == 0.0
    assert nearby.score == pytest.approx(0.5)
    assert nearby.deviation_celsius == pytest.approx(2.5)


def test_temperature_comfort_assessment_preserves_inputs() -> None:
    """The result should retain its source evidence and comfort policy."""

    observation = _observation(13.0)
    comfort_range = _comfort_range()

    assessment = assess_temperature_comfort(
        observation=observation,
        comfort_range=comfort_range,
    )

    assert assessment.observation is observation
    assert assessment.comfort_range is comfort_range


def test_temperature_comfort_assessment_exposes_temperature() -> None:
    """The assessed temperature should remain directly explainable."""

    assessment = assess_temperature_comfort(
        observation=_observation(13.0),
        comfort_range=_comfort_range(),
    )

    assert assessment.temperature_celsius == 13.0


def test_temperature_comfort_assessment_rejects_invalid_observation() -> None:
    """Comfort assessment requires normalized Solara weather evidence."""

    with pytest.raises(
        TypeError,
        match="observation must be a WeatherObservation",
    ):
        assess_temperature_comfort(
            observation="24.0",  # type: ignore[arg-type]
            comfort_range=_comfort_range(),
        )


def test_temperature_comfort_assessment_rejects_invalid_comfort_range() -> None:
    """Comfort assessment requires a Solara temperature-comfort policy."""

    with pytest.raises(
        TypeError,
        match="comfort_range must be a TemperatureComfortRange",
    ):
        assess_temperature_comfort(
            observation=_observation(24.0),
            comfort_range=(18.0, 28.0),  # type: ignore[arg-type]
        )


def test_temperature_comfort_assessment_uses_value_equality() -> None:
    """Equivalent evidence and policy should produce equivalent assessments."""

    first = assess_temperature_comfort(
        observation=_observation(13.0),
        comfort_range=_comfort_range(),
    )
    second = assess_temperature_comfort(
        observation=_observation(13.0),
        comfort_range=_comfort_range(),
    )

    assert first == second


def test_temperature_comfort_assessment_is_hashable() -> None:
    """Comfort assessments should be usable in immutable collections."""

    assessment = assess_temperature_comfort(
        observation=_observation(13.0),
        comfort_range=_comfort_range(),
    )

    assert {assessment, assessment} == {assessment}


def test_temperature_comfort_assessment_is_immutable() -> None:
    """Derived climate-comfort evidence must not change after calculation."""

    assessment = assess_temperature_comfort(
        observation=_observation(13.0),
        comfort_range=_comfort_range(),
    )

    with pytest.raises(FrozenInstanceError):
        assessment.score = 0.9


def test_temperature_comfort_returns_assessment_value_object() -> None:
    """The analytics function should return explicit explainable evidence."""

    assessment = assess_temperature_comfort(
        observation=_observation(24.0),
        comfort_range=_comfort_range(),
    )

    assert isinstance(assessment, TemperatureComfortAssessment)