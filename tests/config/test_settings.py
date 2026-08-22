"""Tests for immutable framework-independent deployment settings."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from solara_travel.config import (
    DeploymentSettings,
    GooglePlacesSettings,
    OpenAINarrationSettings,
    OpenMeteoSettings,
    PublicAlphaSafeguardSettings,
    RecommendationPolicySettings,
)
from solara_travel.presentation.api import PublicAlphaSafeguardSettings as ApiSafeguards


def _deployment_settings() -> DeploymentSettings:
    return DeploymentSettings(
        google_places=GooglePlacesSettings(" google-secret "),
        openai_narration=OpenAINarrationSettings(" openai-secret ", " model "),
    )


def test_settings_are_frozen_trim_text_and_keep_one_safeguard_class_identity() -> None:
    settings = _deployment_settings()

    assert settings.google_places.api_key == "google-secret"
    assert settings.openai_narration.api_key == "openai-secret"
    assert settings.openai_narration.model == "model"
    assert ApiSafeguards is PublicAlphaSafeguardSettings
    with pytest.raises(FrozenInstanceError):
        settings.docs_enabled = True  # type: ignore[misc]


def test_secret_values_are_hidden_from_nested_reprs() -> None:
    text = repr(_deployment_settings())

    assert "google-secret" not in text
    assert "openai-secret" not in text


@pytest.mark.parametrize("value", [None, 1])
def test_required_setting_text_must_be_string(value: object) -> None:
    with pytest.raises(TypeError, match="must be a string"):
        GooglePlacesSettings(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["", "   "])
def test_required_setting_text_must_not_be_blank(value: str) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        OpenAINarrationSettings("key", value)


@pytest.mark.parametrize("value", [True, "10"])
def test_timeout_must_be_real(value: object) -> None:
    with pytest.raises(TypeError, match="real number"):
        OpenMeteoSettings(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_timeout_must_be_finite(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        OpenMeteoSettings(value)


def test_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        OpenMeteoSettings(0.0)


@pytest.mark.parametrize("field_name", ["destination_page_size", "attraction_max_results"])
def test_google_result_counts_require_integers(field_name: str) -> None:
    with pytest.raises(TypeError, match=field_name):
        GooglePlacesSettings("key", **{field_name: True})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("destination_page_size", 0), ("attraction_max_results", 21)],
)
def test_google_result_counts_are_bounded(field_name: str, value: int) -> None:
    with pytest.raises(ValueError, match=field_name):
        GooglePlacesSettings("key", **{field_name: value})


def test_google_radius_has_provider_maximum() -> None:
    with pytest.raises(ValueError, match="must not exceed 50000"):
        GooglePlacesSettings("key", attraction_radius_meters=50_001)


@pytest.mark.parametrize("value", [True, 1.5])
def test_positive_integer_settings_reject_non_ints(value: object) -> None:
    with pytest.raises(TypeError, match="must be an int"):
        OpenAINarrationSettings("key", "model", max_output_tokens=value)  # type: ignore[arg-type]


def test_positive_integer_settings_reject_zero() -> None:
    with pytest.raises(ValueError, match="positive"):
        PublicAlphaSafeguardSettings(recommendation_rate_limit=0)


@pytest.mark.parametrize("value", ["2020-01-01", datetime(2020, 1, 1)])
def test_policy_dates_must_be_calendar_dates(value: object) -> None:
    with pytest.raises(TypeError, match="date values"):
        RecommendationPolicySettings(historical_start_date=value)  # type: ignore[arg-type]


def test_policy_end_must_not_precede_start() -> None:
    with pytest.raises(ValueError, match="end date"):
        RecommendationPolicySettings(
            historical_start_date=date(2024, 1, 2),
            historical_end_date=date(2024, 1, 1),
        )


@pytest.mark.parametrize("value", [True, "1"])
def test_policy_weight_must_be_real(value: object) -> None:
    with pytest.raises(TypeError, match="real number"):
        RecommendationPolicySettings(seasonal_weight=value)  # type: ignore[arg-type]


def test_policy_weight_must_be_finite() -> None:
    with pytest.raises(ValueError, match="finite"):
        RecommendationPolicySettings(seasonal_weight=float("nan"))


@pytest.mark.parametrize("value", [0.0, 1.1])
def test_policy_weight_is_positive_and_normalized(value: float) -> None:
    with pytest.raises(ValueError, match="greater than 0"):
        RecommendationPolicySettings(seasonal_weight=value)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("google_places", object()),
        ("openai_narration", object()),
        ("open_meteo", object()),
        ("recommendation_policy", object()),
        ("public_alpha_safeguards", object()),
    ],
)
def test_deployment_settings_validate_nested_types(field_name: str, value: object) -> None:
    values = {
        "google_places": GooglePlacesSettings("key"),
        "openai_narration": OpenAINarrationSettings("key", "model"),
        field_name: value,
    }
    with pytest.raises(TypeError, match=field_name):
        DeploymentSettings(**values)  # type: ignore[arg-type]


def test_deployment_docs_policy_requires_bool() -> None:
    with pytest.raises(TypeError, match="docs_enabled"):
        DeploymentSettings(
            GooglePlacesSettings("key"),
            OpenAINarrationSettings("key", "model"),
            docs_enabled=1,  # type: ignore[arg-type]
        )
