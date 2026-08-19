"""Application service coordinating deterministic Solara recommendations."""

from dataclasses import dataclass

from solara_travel.analytics.scoring import ScoreComponent, SuitabilityScore
from solara_travel.analytics.seasonality import (
    assess_seasonal_temperature_comfort,
    build_seasonal_weather_profile,
    seasonal_temperature_comfort_score_component,
)
from solara_travel.application.results import (
    DestinationRecommendation,
    RecommendationEvidence,
    RecommendationResult,
)
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.destination import Destination
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.ports.places import PlacesProvider
from solara_travel.ports.weather import HistoricalWeatherProvider


@dataclass(frozen=True, slots=True)
class RecommendationService:
    """Coordinate providers and deterministic analytics into ranked results."""

    places_provider: PlacesProvider
    weather_provider: HistoricalWeatherProvider
    historical_period: TravelPeriod
    comfort_range: TemperatureComfortRange
    seasonal_weight: float = 1.0

    def __post_init__(self) -> None:
        """Validate application-service dependencies and explicit policy values."""

        if not isinstance(self.places_provider, PlacesProvider):
            raise TypeError("places_provider must satisfy PlacesProvider")

        if not isinstance(self.weather_provider, HistoricalWeatherProvider):
            raise TypeError(
                "weather_provider must satisfy HistoricalWeatherProvider"
            )

        if not isinstance(self.historical_period, TravelPeriod):
            raise TypeError("historical_period must be a TravelPeriod")

        if not isinstance(self.comfort_range, TemperatureComfortRange):
            raise TypeError("comfort_range must be a TemperatureComfortRange")

        # Reuse generic scoring validation rather than duplicating numeric rules.
        SuitabilityScore(
            (
                ScoreComponent(
                    name="seasonal_temperature_comfort",
                    score=1.0,
                    weight=self.seasonal_weight,
                ),
            )
        )

    def recommend(self, request: RecommendationRequest) -> RecommendationResult:
        """Return deterministic recommendations for one validated request."""

        if not isinstance(request, RecommendationRequest):
            raise TypeError("request must be a RecommendationRequest")

        candidates = self._candidate_destinations(request)
        recommendations = tuple(
            self._recommend_destination(destination, request)
            for destination in candidates
        )
        ranked = tuple(
            sorted(
                recommendations,
                key=lambda recommendation: recommendation.score,
                reverse=True,
            )
        )
        return RecommendationResult(request=request, recommendations=ranked)

    def _candidate_destinations(
        self,
        request: RecommendationRequest,
    ) -> tuple[Destination, ...]:
        """Return a preselected destination or discover provider candidates."""

        if request.destination is not None:
            return (request.destination,)

        candidates = self.places_provider.discover_destinations(request)
        if not isinstance(candidates, tuple):
            raise TypeError("destination provider must return a tuple")
        if not all(isinstance(candidate, Destination) for candidate in candidates):
            raise TypeError("destination provider must return Destination values")
        return candidates

    def _recommend_destination(
        self,
        destination: Destination,
        request: RecommendationRequest,
    ) -> DestinationRecommendation:
        """Collect evidence and build one deterministic destination result."""

        attractions = self.places_provider.discover_attractions(destination)
        observations = self.weather_provider.get_historical_weather(
            destination,
            self.historical_period,
        )
        profile = build_seasonal_weather_profile(
            observations,
            request.travel_period,
        )
        comfort = assess_seasonal_temperature_comfort(
            profile,
            self.comfort_range,
        )
        seasonal_component = seasonal_temperature_comfort_score_component(
            comfort,
            self.seasonal_weight,
        )
        evidence = RecommendationEvidence(
            attractions=attractions,
            seasonal_weather=profile,
            seasonal_temperature_comfort=comfort,
        )
        return DestinationRecommendation(
            destination=destination,
            suitability=SuitabilityScore((seasonal_component,)),
            evidence=evidence,
        )
