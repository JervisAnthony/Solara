"""Typed HTTP response schemas for Solara's FastAPI presentation."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Process-health response returned by the ASGI application."""

    status: Literal["ok"]
