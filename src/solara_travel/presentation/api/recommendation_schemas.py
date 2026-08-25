"""Typed HTTP schemas for Solara recommendation requests and responses."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from solara_travel.domain import DestinationQuery
from solara_travel.domain.preferences import TRIP_DESCRIPTION_MAX_LENGTH

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
    """Optional traveller preferences and untrusted natural-language context."""

    interests: list[str] | None = None
    preferred_pace: str | None = None
    preferred_climate: str | None = None
    trip_description: str | None = Field(
        default=None,
        max_length=TRIP_DESCRIPTION_MAX_LENGTH,
        description=(
            "Optional traveller-provided trip context. Treated as untrusted data, not instructions."
        ),
    )


class RecommendationRequestBody(StrictRequestModel):
    """Public request body for deterministic recommendations."""

    travel_period: TravelPeriodRequest
    preferences: TravellerPreferencesRequest = Field(default_factory=TravellerPreferencesRequest)
    destination: DestinationRequest | None = None
    destination_queries: list[str] | None = Field(default=None, max_length=5)

    @field_validator("destination_queries")
    @classmethod
    def validate_destination_queries(cls, values: list[str] | None) -> list[str] | None:
        """Normalize and validate public destination query strings."""

        if values is None:
            return None
        return [DestinationQuery(value).value for value in values]

    @model_validator(mode="after")
    def validate_destination_input_mode(self) -> "RecommendationRequestBody":
        """Reject simultaneous structured and free-text destination input."""

        if self.destination is not None and self.destination_queries:
            raise ValueError("destination and destination_queries are mutually exclusive")
        return self


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
    trip_description: str | None


class TravelScopeResponse(BaseModel):
    """Selected broad discovery scope without provider implementation detail."""

    display_name: str
    kind: Literal["region", "country"]


class RecommendationRequestResponse(BaseModel):
    """Authoritative domain request used to produce the result."""

    travel_period: TravelPeriodResponse
    preferences: TravellerPreferencesResponse
    destination: DestinationResponse | None
    destination_queries: list[str]
    destination_mode: Literal["discovery", "pre_resolved", "explicit_queries", "scope_discovery"]
    travel_scope: TravelScopeResponse | None = None


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
