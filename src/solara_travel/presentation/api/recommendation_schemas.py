"""Typed HTTP schemas for Solara recommendation requests and responses."""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

FiniteStrictFloat = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class StrictRequestModel(BaseModel):
    """Base for request objects that reject unknown HTTP fields."""

    model_config = ConfigDict(extra="forbid")


class CoordinatesRequest(StrictRequestModel):
    """JSON coordinates accepted at the recommendation boundary."""

    latitude: FiniteStrictFloat
    longitude: FiniteStrictFloat


class DestinationRequest(StrictRequestModel):
    """Optional caller-selected destination input."""

    name: str
    country: str
    coordinates: CoordinatesRequest


class TravelPeriodRequest(StrictRequestModel):
    """Inclusive calendar period input."""

    start_date: date
    end_date: date


class TravellerPreferencesRequest(StrictRequestModel):
    """Optional free-form traveller preferences."""

    interests: list[str] | None = None
    preferred_pace: str | None = None
    preferred_climate: str | None = None


class RecommendationRequestBody(StrictRequestModel):
    """Public request body for deterministic recommendations."""

    travel_period: TravelPeriodRequest
    preferences: TravellerPreferencesRequest = Field(default_factory=TravellerPreferencesRequest)
    destination: DestinationRequest | None = None


class CoordinatesResponse(BaseModel):
    """Solara-owned normalized destination or attraction coordinates."""

    latitude: float
    longitude: float


class DestinationResponse(BaseModel):
    """Solara-owned destination identity."""

    name: str
    country: str
    coordinates: CoordinatesResponse


class TravelPeriodResponse(BaseModel):
    """Authoritative inclusive calendar period."""

    start_date: date
    end_date: date


class TravellerPreferencesResponse(BaseModel):
    """Authoritative optional traveller preferences."""

    interests: list[str] | None
    preferred_pace: str | None
    preferred_climate: str | None


class RecommendationRequestResponse(BaseModel):
    """Authoritative domain request used to produce the result."""

    travel_period: TravelPeriodResponse
    preferences: TravellerPreferencesResponse
    destination: DestinationResponse | None


class ScoreComponentResponse(BaseModel):
    """One authoritative contribution to the suitability score."""

    name: str
    score: float
    weight: float
    weighted_contribution: float


class AttractionResponse(BaseModel):
    """Selected normalized attraction evidence."""

    name: str
    category: str
    coordinates: CoordinatesResponse


class SeasonalWeatherResponse(BaseModel):
    """Aggregated historical evidence for the requested calendar period."""

    target_period: TravelPeriodResponse
    observation_count: int
    historical_years: list[int]
    historical_year_count: int
    mean_temperature_celsius: float
    minimum_temperature_celsius: float
    maximum_temperature_celsius: float
    mean_relative_humidity_percent: float
    mean_daily_precipitation_mm: float


class TemperatureComfortRangeResponse(BaseModel):
    """Configured range used by existing seasonal comfort analytics."""

    minimum_celsius: float
    maximum_celsius: float
    tolerance_celsius: float


class TemperatureComfortResponse(BaseModel):
    """Existing aggregate seasonal temperature-comfort evidence."""

    score: float
    comfort_range: TemperatureComfortRangeResponse
    within_preferred_fraction: float
    mean_deviation_celsius: float


class RecommendationEvidenceResponse(BaseModel):
    """Explicit compact evidence supporting one recommendation."""

    attractions: list[AttractionResponse]
    seasonal_weather: SeasonalWeatherResponse
    temperature_comfort: TemperatureComfortResponse


class DestinationRecommendationResponse(BaseModel):
    """One ranked deterministic recommendation."""

    rank: int
    destination: DestinationResponse
    score: float
    components: list[ScoreComponentResponse]
    evidence: RecommendationEvidenceResponse


class RecommendationResponse(BaseModel):
    """Complete deterministic result with optional narration enrichment."""

    request: RecommendationRequestResponse
    recommendation_count: int
    has_recommendations: bool
    recommendations: list[DestinationRecommendationResponse]
    has_narration: bool
    narration: str | None
