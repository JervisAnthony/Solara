"""Tests for climate-comfort integration with suitability scoring."""

from datetime import date

import pytest

from solara_travel.analytics.climate import (
    assess_temperature_comfort,
    temperature_comfort_score_component,
)
from solara_travel.analytics.scoring import ScoreComponent
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.weather import WeatherObservation


def _assessment(
    temperature_celsius: float = 24.0,
):
    """Build a deterministic temperature-comfort assessment."""

    observation = WeatherObservation(
        observed_on=date(2026, 8, 8),
        temperature_celsius=temperature_celsius,
        relative_humidity_percent=60.0,
        precipitation_mm=0.0,
    )
    comfort_range = TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=10.0,
    )

    return assess_temperature_comfort(
        observation=observation,
        comfort_range=comfort_range,
    )


def test_temperature_comfort_score_component_returns_score_component() -> None:
    """Climate comfort should integrate through the generic scoring primitive."""

    component = temperature_comfort_score_component(
        assessment=_assessment(),
        weight=0.30,
    )

    assert isinstance(component, ScoreComponent)


def test_temperature_comfort_score_component_uses_explicit_name() -> None:
    """The scoring contribution should have a stable explanatory name."""

    component = temperature_comfort_score_component(
        assessment=_assessment(),
        weight=0.30,
    )

    assert component.name == "temperature_comfort"


def test_temperature_comfort_score_component_preserves_assessment_score() -> None:
    """The generic component must use the derived climate-comfort score."""

    assessment = _assessment(temperature_celsius=13.0)

    component = temperature_comfort_score_component(
        assessment=assessment,
        weight=0.30,
    )

    assert assessment.score == pytest.approx(0.50)
    assert component.score == pytest.approx(assessment.score)


def test_temperature_comfort_score_component_preserves_weight() -> None:
    """Climate contribution weight should remain explicit and caller-defined."""

    component = temperature_comfort_score_component(
        assessment=_assessment(),
        weight=0.35,
    )

    assert component.weight == pytest.approx(0.35)


def test_temperature_comfort_score_component_supports_zero_weight() -> None:
    """Climate comfort may be visible evidence without affecting aggregation."""

    component = temperature_comfort_score_component(
        assessment=_assessment(),
        weight=0.0,
    )

    assert component.weight == 0.0
    assert component.weighted_contribution == 0.0


def test_temperature_comfort_score_component_reports_weighted_contribution() -> None:
    """The converted component should participate in generic weighted scoring."""

    component = temperature_comfort_score_component(
        assessment=_assessment(temperature_celsius=13.0),
        weight=0.40,
    )

    assert component.score == pytest.approx(0.50)
    assert component.weighted_contribution == pytest.approx(0.20)


def test_temperature_comfort_score_component_rejects_invalid_assessment() -> None:
    """Conversion requires explicit Solara climate-comfort evidence."""

    with pytest.raises(
        TypeError,
        match="assessment must be a TemperatureComfortAssessment",
    ):
        temperature_comfort_score_component(
            assessment="comfortable",  # type: ignore[arg-type]
            weight=0.30,
        )


@pytest.mark.parametrize(
    "weight",
    [
        -0.01,
        1.01,
    ],
)
def test_temperature_comfort_score_component_rejects_invalid_weight(
    weight: float,
) -> None:
    """Generic ScoreComponent weight validation should remain authoritative."""

    with pytest.raises(
        ValueError,
        match="weight must be between 0 and 1",
    ):
        temperature_comfort_score_component(
            assessment=_assessment(),
            weight=weight,
        )


@pytest.mark.parametrize(
    "weight",
    [
        None,
        "0.30",
        True,
    ],
)
def test_temperature_comfort_score_component_rejects_non_numeric_weight(
    weight: object,
) -> None:
    """Climate integration should retain generic numeric weight validation."""

    with pytest.raises(
        TypeError,
        match="weight must be a real number",
    ):
        temperature_comfort_score_component(
            assessment=_assessment(),
            weight=weight,  # type: ignore[arg-type]
        )


def test_temperature_comfort_score_component_is_deterministic() -> None:
    """Equivalent assessments and weights should produce equal components."""

    first = temperature_comfort_score_component(
        assessment=_assessment(temperature_celsius=13.0),
        weight=0.30,
    )
    second = temperature_comfort_score_component(
        assessment=_assessment(temperature_celsius=13.0),
        weight=0.30,
    )

    assert first == second