"""Deterministic climate-comfort intelligence used by Solara."""

from dataclasses import dataclass

from solara_travel.analytics.scoring import ScoreComponent
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.weather import WeatherObservation


@dataclass(frozen=True, slots=True)
class TemperatureComfortAssessment:
    """Explainable result of assessing observed temperature comfort."""

    observation: WeatherObservation
    comfort_range: TemperatureComfortRange
    score: float
    deviation_celsius: float
    within_preferred_range: bool

    @property
    def temperature_celsius(self) -> float:
        """Return the observed temperature represented by this assessment."""

        return self.observation.temperature_celsius


def assess_temperature_comfort(
    observation: WeatherObservation,
    comfort_range: TemperatureComfortRange,
) -> TemperatureComfortAssessment:
    """Assess temperature comfort using deterministic linear degradation.

    Temperatures within the preferred range receive a score of 1.0. Outside
    the preferred range, comfort decreases linearly according to the configured
    tolerance until reaching 0.0.
    """

    if not isinstance(observation, WeatherObservation):
        raise TypeError("observation must be a WeatherObservation")

    if not isinstance(comfort_range, TemperatureComfortRange):
        raise TypeError(
            "comfort_range must be a TemperatureComfortRange"
        )

    temperature = observation.temperature_celsius

    if temperature < comfort_range.minimum_celsius:
        deviation = comfort_range.minimum_celsius - temperature
        within_preferred_range = False
    elif temperature > comfort_range.maximum_celsius:
        deviation = temperature - comfort_range.maximum_celsius
        within_preferred_range = False
    else:
        deviation = 0.0
        within_preferred_range = True

    score = max(
        0.0,
        1.0 - (deviation / comfort_range.tolerance_celsius),
    )

    return TemperatureComfortAssessment(
        observation=observation,
        comfort_range=comfort_range,
        score=score,
        deviation_celsius=deviation,
        within_preferred_range=within_preferred_range,
    )


def temperature_comfort_score_component(
    assessment: TemperatureComfortAssessment,
    weight: float,
) -> ScoreComponent:
    """Convert climate-comfort evidence into a generic scoring component.

    Score and weight validation remain the responsibility of ScoreComponent so
    all suitability contributions obey the same normalized scoring contract.
    """

    if not isinstance(assessment, TemperatureComfortAssessment):
        raise TypeError(
            "assessment must be a TemperatureComfortAssessment"
        )

    return ScoreComponent(
        name="temperature_comfort",
        score=assessment.score,
        weight=weight,
    )