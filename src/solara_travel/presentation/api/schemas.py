"""Typed HTTP response schemas for Solara's FastAPI presentation."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Process-health response returned by the ASGI application."""

    status: Literal["ok"]


class ApiErrorDetail(BaseModel):
    """Stable safe details for explicitly translated API failures."""

    code: str
    message: str


class ApiErrorResponse(BaseModel):
    """Envelope used for known presentation-boundary failures."""

    detail: ApiErrorDetail
