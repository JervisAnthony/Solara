"""Strongly typed HTTP contracts for provider-backed Itinerary Studio options."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from solara_travel.domain import DestinationQuery


class ActivityPaletteRequest(BaseModel):
    """A canonical-suggestion value to resolve before activity discovery."""

    model_config = ConfigDict(extra="forbid")

    destination_query: str = Field(min_length=1, max_length=120)

    @field_validator("destination_query")
    @classmethod
    def normalize_destination_query(cls, value: str) -> str:
        return DestinationQuery(value).value


class ItineraryCoordinatesResponse(BaseModel):
    latitude: float
    longitude: float


class ItineraryDestinationResponse(BaseModel):
    name: str
    country: str
    coordinates: ItineraryCoordinatesResponse


class DurationEstimateResponse(BaseModel):
    """Traveller-safe approximate range and trust metadata."""

    minimum_minutes: int
    maximum_minutes: int
    typical_minutes: int
    provenance: Literal["provider", "category_heuristic", "traveller_selected"]
    confidence: Literal["low", "medium", "high"]
    is_estimate: Literal[True] = True


class ActivityOptionResponse(BaseModel):
    identity: str
    name: str
    category: str
    coordinates: ItineraryCoordinatesResponse | None
    duration: DurationEstimateResponse | None
    accessibility: Literal["confirmed", "unavailable", "unknown"]


class ActivityPaletteResponse(BaseModel):
    destination: ItineraryDestinationResponse
    activities: list[ActivityOptionResponse]
    maximum_options: int
    duration_notice: str = (
        "Visit durations are planning estimates, not live opening-hours or booking data."
    )
    accessibility_notice: str = (
        "Unknown means accessibility information was not available; it is not a claim of access."
    )
