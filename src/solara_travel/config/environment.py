"""Explicit environment mapping for hosted deployment settings."""

import os
from collections.abc import Mapping
from datetime import date
from math import isfinite

from solara_travel.config.settings import (
    DeploymentSettings,
    GooglePlacesSettings,
    OpenAINarrationSettings,
    OpenMeteoSettings,
    PublicAlphaSafeguardSettings,
    RecommendationPolicySettings,
)

_REQUIRED_VARIABLES = (
    "SOLARA_GOOGLE_PLACES_API_KEY",
    "SOLARA_OPENAI_API_KEY",
    "SOLARA_OPENAI_MODEL",
)
_MISSING = object()


class DeploymentConfigurationError(ValueError):
    """Report safe deployment configuration errors without exposing values."""


def load_deployment_settings(
    environ: Mapping[str, str] | None = None,
) -> DeploymentSettings:
    """Load and validate one immutable deployment configuration."""

    source = os.environ if environ is None else environ
    required = _load_required_text(source)
    return DeploymentSettings(
        google_places=GooglePlacesSettings(
            api_key=required["SOLARA_GOOGLE_PLACES_API_KEY"],
            timeout_seconds=_float(source, "SOLARA_GOOGLE_PLACES_TIMEOUT_SECONDS", 10.0),
            destination_page_size=_integer(
                source,
                "SOLARA_GOOGLE_PLACES_DESTINATION_PAGE_SIZE",
                10,
                minimum=1,
                maximum=20,
            ),
            attraction_max_results=_integer(
                source,
                "SOLARA_GOOGLE_PLACES_ATTRACTION_MAX_RESULTS",
                20,
                minimum=1,
                maximum=20,
            ),
            attraction_radius_meters=_float(
                source,
                "SOLARA_GOOGLE_PLACES_ATTRACTION_RADIUS_METERS",
                30_000.0,
                maximum=50_000.0,
            ),
        ),
        open_meteo=OpenMeteoSettings(
            timeout_seconds=_float(source, "SOLARA_OPEN_METEO_TIMEOUT_SECONDS", 10.0)
        ),
        openai_narration=OpenAINarrationSettings(
            api_key=required["SOLARA_OPENAI_API_KEY"],
            model=required["SOLARA_OPENAI_MODEL"],
            timeout_seconds=_float(source, "SOLARA_OPENAI_TIMEOUT_SECONDS", 30.0),
            max_output_tokens=_integer(
                source,
                "SOLARA_OPENAI_MAX_OUTPUT_TOKENS",
                1200,
            ),
        ),
        recommendation_policy=_recommendation_policy(source),
        public_alpha_safeguards=PublicAlphaSafeguardSettings(
            recommendation_rate_limit=_integer(source, "SOLARA_RECOMMENDATION_RATE_LIMIT", 12),
            recommendation_rate_window_seconds=_integer(
                source, "SOLARA_RECOMMENDATION_RATE_WINDOW_SECONDS", 60
            ),
            recommendation_budget_limit=_integer(source, "SOLARA_RECOMMENDATION_BUDGET_LIMIT", 60),
            recommendation_budget_window_seconds=_integer(
                source, "SOLARA_RECOMMENDATION_BUDGET_WINDOW_SECONDS", 3600
            ),
            recommendation_concurrency_limit=_integer(
                source, "SOLARA_RECOMMENDATION_CONCURRENCY_LIMIT", 2
            ),
            feedback_rate_limit=_integer(source, "SOLARA_FEEDBACK_RATE_LIMIT", 30),
            feedback_rate_window_seconds=_integer(
                source, "SOLARA_FEEDBACK_RATE_WINDOW_SECONDS", 60
            ),
            narration_budget_limit=_integer(source, "SOLARA_NARRATION_BUDGET_LIMIT", 30),
            narration_budget_window_seconds=_integer(
                source, "SOLARA_NARRATION_BUDGET_WINDOW_SECONDS", 3600
            ),
        ),
        docs_enabled=_boolean(source, "SOLARA_DOCS_ENABLED", False),
    )


def _recommendation_policy(source: Mapping[str, str]) -> RecommendationPolicySettings:
    start = _date(
        source,
        "SOLARA_HISTORICAL_START_DATE",
        date(2020, 1, 1),
    )
    end = _date(
        source,
        "SOLARA_HISTORICAL_END_DATE",
        date(2024, 12, 31),
    )
    if end < start:
        raise DeploymentConfigurationError(
            "SOLARA_HISTORICAL_END_DATE must not be before SOLARA_HISTORICAL_START_DATE"
        )
    comfort_minimum = _float(
        source,
        "SOLARA_COMFORT_MIN_CELSIUS",
        18.0,
        positive=False,
        minimum=-100.0,
        maximum=60.0,
    )
    comfort_maximum = _float(
        source,
        "SOLARA_COMFORT_MAX_CELSIUS",
        28.0,
        positive=False,
        minimum=-100.0,
        maximum=60.0,
    )
    if comfort_minimum > comfort_maximum:
        raise DeploymentConfigurationError(
            "SOLARA_COMFORT_MIN_CELSIUS must not exceed SOLARA_COMFORT_MAX_CELSIUS"
        )
    return RecommendationPolicySettings(
        historical_start_date=start,
        historical_end_date=end,
        comfort_min_celsius=comfort_minimum,
        comfort_max_celsius=comfort_maximum,
        comfort_tolerance_celsius=_float(
            source,
            "SOLARA_COMFORT_TOLERANCE_CELSIUS",
            10.0,
        ),
        seasonal_weight=_float(
            source,
            "SOLARA_SEASONAL_WEIGHT",
            1.0,
            maximum=1.0,
        ),
    )


def _load_required_text(source: Mapping[str, str]) -> dict[str, str]:
    missing = [
        name
        for name in _REQUIRED_VARIABLES
        if not isinstance(source.get(name), str) or not source.get(name, "").strip()
    ]
    if missing:
        names = ", ".join(missing)
        raise DeploymentConfigurationError(f"Missing required deployment variables: {names}")
    return {name: source[name].strip() for name in _REQUIRED_VARIABLES}


def _raw(source: Mapping[str, str], name: str) -> str | object:
    value = source.get(name, _MISSING)  # type: ignore[arg-type]
    if value is _MISSING:
        return _MISSING
    if not isinstance(value, str):
        raise DeploymentConfigurationError(f"{name} must be a string")
    return value.strip()


def _boolean(source: Mapping[str, str], name: str, default: bool) -> bool:
    raw = _raw(source, name)
    if raw is _MISSING:
        return default
    normalized = raw.casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise DeploymentConfigurationError(f"{name} must be true or false")


def _integer(
    source: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    raw = _raw(source, name)
    if raw is _MISSING:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise DeploymentConfigurationError(f"{name} must be an integer") from exc
    if value < minimum or (maximum is not None and value > maximum):
        expectation = f"between {minimum} and {maximum}" if maximum else "a positive integer"
        raise DeploymentConfigurationError(f"{name} must be {expectation}")
    return value


def _float(
    source: Mapping[str, str],
    name: str,
    default: float,
    *,
    positive: bool = True,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    raw = _raw(source, name)
    if raw is _MISSING:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise DeploymentConfigurationError(f"{name} must be a finite number") from exc
    if not isfinite(value):
        raise DeploymentConfigurationError(f"{name} must be a finite number")
    if positive and value <= 0:
        raise DeploymentConfigurationError(f"{name} must be greater than zero")
    if minimum is not None and value < minimum:
        raise DeploymentConfigurationError(f"{name} must be at least {minimum:g}")
    if maximum is not None and value > maximum:
        raise DeploymentConfigurationError(f"{name} must not exceed {maximum:g}")
    return value


def _date(source: Mapping[str, str], name: str, default: date) -> date:
    raw = _raw(source, name)
    if raw is _MISSING:
        return default
    try:
        value = date.fromisoformat(raw)
    except ValueError as exc:
        raise DeploymentConfigurationError(f"{name} must be an ISO date (YYYY-MM-DD)") from exc
    if value.isoformat() != raw:
        raise DeploymentConfigurationError(f"{name} must be an ISO date (YYYY-MM-DD)")
    return value
