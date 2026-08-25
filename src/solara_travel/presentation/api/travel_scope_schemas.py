"""Typed HTTP schemas for geographic planner suggestions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from solara_travel.domain import DestinationQuery


class TravelScopeSuggestionRequest(BaseModel):
    """Small same-origin typeahead request."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=120)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        return DestinationQuery(value).value


class TravelScopeSuggestionItem(BaseModel):
    """Provider-independent geographic prediction."""

    display_name: str
    kind: Literal["locality", "region", "country"]


class TravelScopeSuggestionResponse(BaseModel):
    """Bounded suggestions plus required displayed-data attribution."""

    suggestions: list[TravelScopeSuggestionItem]
    attribution: Literal["Google Maps"] = "Google Maps"
