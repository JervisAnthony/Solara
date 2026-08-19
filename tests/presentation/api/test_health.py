"""Tests for the typed, side-effect-free health contract."""

import pytest
from pydantic import ValidationError

from solara_travel.presentation.api.routes.health import get_health
from solara_travel.presentation.api.schemas import HealthResponse


def test_health_response_contains_only_process_status() -> None:
    response = HealthResponse(status="ok")

    assert response.model_dump() == {"status": "ok"}


def test_health_response_rejects_other_status_values() -> None:
    with pytest.raises(ValidationError):
        HealthResponse(status="ready")  # type: ignore[arg-type]


def test_health_handler_is_deterministic_and_side_effect_free() -> None:
    first = get_health()
    second = get_health()

    assert first == second == HealthResponse(status="ok")
