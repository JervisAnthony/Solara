"""Deterministic travel-intelligence analytics exposed by Solara."""

from solara_travel.analytics.climate import (
    TemperatureComfortAssessment,
    assess_temperature_comfort,
    temperature_comfort_score_component,
)
from solara_travel.analytics.scoring import ScoreComponent, SuitabilityScore

__all__ = [
    "ScoreComponent",
    "SuitabilityScore",
    "TemperatureComfortAssessment",
    "assess_temperature_comfort",
    "temperature_comfort_score_component",
]