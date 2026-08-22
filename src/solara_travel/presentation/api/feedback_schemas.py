"""Typed HTTP schemas for public-alpha tester feedback."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

FeedbackRating = Literal["helpful", "mixed", "not_helpful"]


class FeedbackRequestBody(BaseModel):
    """Strict privacy-conscious feedback explicitly submitted by a tester."""

    model_config = ConfigDict(extra="forbid")

    recommendation_request_id: UUID | None = None
    rating: FeedbackRating
    comment: Annotated[str, Field(max_length=1000)] | None = None

    @field_validator("comment", mode="before")
    @classmethod
    def normalize_comment(cls, value: object) -> object:
        """Trim surrounding whitespace and normalize a blank comment to null."""

        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class FeedbackAcceptedResponse(BaseModel):
    """Minimal receipt returned without echoing submitted feedback."""

    status: Literal["accepted"]
    feedback_id: UUID
