"""Immutable structured results for Solara recommendation workflows."""

from dataclasses import dataclass

from solara_travel.analytics.scoring import ScoreComponent, SuitabilityScore
from solara_travel.analytics.seasonality import (
    SeasonalTemperatureComfortAssessment,
    SeasonalWeatherProfile,
)
from solara_travel.domain.attraction import Attraction
from solara_travel.domain.destination import Destination
from solara_travel.domain.recommendation import RecommendationRequest

_SEASONAL_TEMPERATURE_COMFORT_COMPONENT = "seasonal_temperature_comfort"


@dataclass(frozen=True, slots=True)
class RecommendationEvidence:
    """Immutable evidence supporting one destination recommendation."""

    attractions: tuple[Attraction, ...]
    seasonal_weather: SeasonalWeatherProfile
    seasonal_temperature_comfort: SeasonalTemperatureComfortAssessment

    def __post_init__(self) -> None:
        """Validate evidence types, uniqueness, and internal consistency."""

        if not isinstance(self.attractions, tuple):
            raise TypeError("attractions must be a tuple")

        if not all(isinstance(attraction, Attraction) for attraction in self.attractions):
            raise TypeError("every attraction must be an Attraction")

        if len(self.attractions) != len(set(self.attractions)):
            raise ValueError("attractions must not contain duplicates")

        if not isinstance(self.seasonal_weather, SeasonalWeatherProfile):
            raise TypeError("seasonal_weather must be a SeasonalWeatherProfile")

        if not isinstance(
            self.seasonal_temperature_comfort,
            SeasonalTemperatureComfortAssessment,
        ):
            raise TypeError(
                "seasonal_temperature_comfort must be a "
                "SeasonalTemperatureComfortAssessment"
            )

        if self.seasonal_temperature_comfort.profile != self.seasonal_weather:
            raise ValueError(
                "seasonal temperature comfort must describe seasonal weather"
            )


@dataclass(frozen=True, slots=True)
class DestinationRecommendation:
    """Immutable scored destination with its supporting evidence."""

    destination: Destination
    suitability: SuitabilityScore
    evidence: RecommendationEvidence

    def __post_init__(self) -> None:
        """Validate result types and evidence-backed seasonal scoring."""

        if not isinstance(self.destination, Destination):
            raise TypeError("destination must be a Destination")

        if not isinstance(self.suitability, SuitabilityScore):
            raise TypeError("suitability must be a SuitabilityScore")

        if not isinstance(self.evidence, RecommendationEvidence):
            raise TypeError("evidence must be RecommendationEvidence")

        seasonal_component = self._seasonal_temperature_comfort_component()
        if (
            seasonal_component is not None
            and seasonal_component.score
            != self.evidence.seasonal_temperature_comfort.score
        ):
            raise ValueError(
                "seasonal temperature comfort component score must match evidence"
            )

    @property
    def score(self) -> float:
        """Return the aggregate suitability score."""

        return self.suitability.score

    @property
    def components(self) -> tuple[ScoreComponent, ...]:
        """Return the immutable suitability components in their original order."""

        return self.suitability.components

    def _seasonal_temperature_comfort_component(self) -> ScoreComponent | None:
        """Return the owned seasonal component when the generic score contains it."""

        return next(
            (
                component
                for component in self.suitability.components
                if component.name.strip().casefold()
                == _SEASONAL_TEMPERATURE_COMFORT_COMPONENT
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    """Immutable structured recommendations produced for one request."""

    request: RecommendationRequest
    recommendations: tuple[DestinationRecommendation, ...]

    def __post_init__(self) -> None:
        """Validate result types, identity, and request/evidence consistency."""

        if not isinstance(self.request, RecommendationRequest):
            raise TypeError("request must be a RecommendationRequest")

        if not isinstance(self.recommendations, tuple):
            raise TypeError("recommendations must be a tuple")

        if not all(
            isinstance(recommendation, DestinationRecommendation)
            for recommendation in self.recommendations
        ):
            raise TypeError(
                "every recommendation must be a DestinationRecommendation"
            )

        destinations = tuple(
            recommendation.destination for recommendation in self.recommendations
        )
        if len(destinations) != len(set(destinations)):
            raise ValueError("recommendation destinations must be unique")

        for recommendation in self.recommendations:
            if (
                recommendation.evidence.seasonal_weather.target_period
                != self.request.travel_period
            ):
                raise ValueError(
                    "recommendation evidence target period must match request"
                )

            if (
                self.request.destination is not None
                and recommendation.destination != self.request.destination
            ):
                raise ValueError(
                    "recommendation destination must match requested destination"
                )

    @property
    def recommendation_count(self) -> int:
        """Return the number of recommendations in the result."""

        return len(self.recommendations)

    @property
    def has_recommendations(self) -> bool:
        """Return whether the result contains any recommendations."""

        return bool(self.recommendations)
