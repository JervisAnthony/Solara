"""Deterministic travel-intelligence analytics exposed by Solara."""

from solara_travel.analytics.climate import (
    TemperatureComfortAssessment,
    assess_temperature_comfort,
    temperature_comfort_score_component,
)
from solara_travel.analytics.scoring import ScoreComponent, SuitabilityScore
from solara_travel.analytics.seasonality import (
    SeasonalTemperatureComfortAssessment,
    SeasonalWeatherProfile,
    assess_seasonal_temperature_comfort,
    build_seasonal_weather_profile,
    seasonal_temperature_comfort_score_component,
)

__all__ = [
    "ScoreComponent",
    "SeasonalTemperatureComfortAssessment",
    "SeasonalWeatherProfile",
    "SuitabilityScore",
    "TemperatureComfortAssessment",
    "assess_seasonal_temperature_comfort",
    "assess_temperature_comfort",
    "build_seasonal_weather_profile",
    "seasonal_temperature_comfort_score_component",
    "temperature_comfort_score_component",
]
