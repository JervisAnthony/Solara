"""Tests for explicit, safe deployment environment parsing."""

from datetime import date

import pytest

from solara_travel.config import (
    DeploymentConfigurationError,
    PublicAlphaSafeguardSettings,
    load_deployment_settings,
)

REQUIRED = {
    "SOLARA_GOOGLE_PLACES_API_KEY": " test-google-key ",
    "SOLARA_OPENAI_API_KEY": " test-openai-key ",
    "SOLARA_OPENAI_MODEL": " test-model ",
}


def test_defaults_are_typed_trimmed_and_match_the_hosted_contract() -> None:
    settings = load_deployment_settings(REQUIRED)

    assert settings.google_places.api_key == "test-google-key"
    assert settings.google_places.timeout_seconds == 10.0
    assert settings.google_places.destination_page_size == 10
    assert settings.google_places.attraction_max_results == 20
    assert settings.google_places.attraction_radius_meters == 30_000.0
    assert settings.open_meteo.timeout_seconds == 10.0
    assert settings.openai_narration.api_key == "test-openai-key"
    assert settings.openai_narration.model == "test-model"
    assert settings.openai_narration.timeout_seconds == 30.0
    assert settings.openai_narration.max_output_tokens == 1200
    assert settings.recommendation_policy.historical_start_date == date(2020, 1, 1)
    assert settings.recommendation_policy.historical_end_date == date(2024, 12, 31)
    assert settings.recommendation_policy.comfort_min_celsius == 18.0
    assert settings.recommendation_policy.comfort_max_celsius == 28.0
    assert settings.recommendation_policy.comfort_tolerance_celsius == 10.0
    assert settings.recommendation_policy.seasonal_weight == 1.0
    assert settings.public_alpha_safeguards == PublicAlphaSafeguardSettings()
    assert settings.docs_enabled is False


def test_every_optional_environment_override_is_mapped() -> None:
    environ = {
        **REQUIRED,
        "SOLARA_DOCS_ENABLED": " TrUe ",
        "SOLARA_GOOGLE_PLACES_TIMEOUT_SECONDS": "11.5",
        "SOLARA_GOOGLE_PLACES_DESTINATION_PAGE_SIZE": "8",
        "SOLARA_GOOGLE_PLACES_ATTRACTION_MAX_RESULTS": "9",
        "SOLARA_GOOGLE_PLACES_ATTRACTION_RADIUS_METERS": "1234.5",
        "SOLARA_OPEN_METEO_TIMEOUT_SECONDS": "12.5",
        "SOLARA_OPENAI_TIMEOUT_SECONDS": "31.5",
        "SOLARA_OPENAI_MAX_OUTPUT_TOKENS": "1300",
        "SOLARA_HISTORICAL_START_DATE": "2021-01-02",
        "SOLARA_HISTORICAL_END_DATE": "2023-12-30",
        "SOLARA_COMFORT_MIN_CELSIUS": "17.5",
        "SOLARA_COMFORT_MAX_CELSIUS": "29.5",
        "SOLARA_COMFORT_TOLERANCE_CELSIUS": "8.5",
        "SOLARA_SEASONAL_WEIGHT": "0.75",
        "SOLARA_RECOMMENDATION_RATE_LIMIT": "13",
        "SOLARA_RECOMMENDATION_RATE_WINDOW_SECONDS": "61",
        "SOLARA_RECOMMENDATION_BUDGET_LIMIT": "62",
        "SOLARA_RECOMMENDATION_BUDGET_WINDOW_SECONDS": "3601",
        "SOLARA_RECOMMENDATION_CONCURRENCY_LIMIT": "3",
        "SOLARA_FEEDBACK_RATE_LIMIT": "31",
        "SOLARA_FEEDBACK_RATE_WINDOW_SECONDS": "62",
        "SOLARA_NARRATION_BUDGET_LIMIT": "32",
        "SOLARA_NARRATION_BUDGET_WINDOW_SECONDS": "3602",
    }

    settings = load_deployment_settings(environ)

    assert settings.docs_enabled is True
    assert settings.google_places.timeout_seconds == 11.5
    assert settings.google_places.destination_page_size == 8
    assert settings.google_places.attraction_max_results == 9
    assert settings.google_places.attraction_radius_meters == 1234.5
    assert settings.open_meteo.timeout_seconds == 12.5
    assert settings.openai_narration.timeout_seconds == 31.5
    assert settings.openai_narration.max_output_tokens == 1300
    assert settings.recommendation_policy.historical_start_date == date(2021, 1, 2)
    assert settings.recommendation_policy.historical_end_date == date(2023, 12, 30)
    assert settings.recommendation_policy.comfort_min_celsius == 17.5
    assert settings.recommendation_policy.comfort_max_celsius == 29.5
    assert settings.recommendation_policy.comfort_tolerance_celsius == 8.5
    assert settings.recommendation_policy.seasonal_weight == 0.75
    assert settings.public_alpha_safeguards == PublicAlphaSafeguardSettings(
        recommendation_rate_limit=13,
        recommendation_rate_window_seconds=61,
        recommendation_budget_limit=62,
        recommendation_budget_window_seconds=3601,
        recommendation_concurrency_limit=3,
        feedback_rate_limit=31,
        feedback_rate_window_seconds=62,
        narration_budget_limit=32,
        narration_budget_window_seconds=3602,
    )


def test_false_boolean_is_accepted_case_insensitively() -> None:
    settings = load_deployment_settings({**REQUIRED, "SOLARA_DOCS_ENABLED": "FALSE"})

    assert settings.docs_enabled is False


def test_explicit_mapping_is_not_mutated_or_supplemented_from_os_environ(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environ = dict(REQUIRED)
    original = dict(environ)
    monkeypatch.setenv("SOLARA_DOCS_ENABLED", "true")

    settings = load_deployment_settings(environ)

    assert settings.docs_enabled is False
    assert environ == original


def test_omitted_mapping_reads_os_environ_only_when_called(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SOLARA_DOCS_ENABLED", "true")

    assert load_deployment_settings().docs_enabled is True


def test_all_missing_required_variables_are_reported_without_values() -> None:
    with pytest.raises(DeploymentConfigurationError) as caught:
        load_deployment_settings({})

    message = str(caught.value)
    assert all(name in message for name in REQUIRED)
    assert "test-google-key" not in message
    assert "test-openai-key" not in message


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SOLARA_GOOGLE_PLACES_API_KEY", "  "),
        ("SOLARA_OPENAI_API_KEY", None),
        ("SOLARA_OPENAI_MODEL", 1),
    ],
)
def test_blank_or_non_string_required_values_are_missing(name: str, value: object) -> None:
    environ: dict[str, object] = dict(REQUIRED)
    environ[name] = value

    with pytest.raises(DeploymentConfigurationError, match=name):
        load_deployment_settings(environ)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SOLARA_DOCS_ENABLED", "yes"),
        ("SOLARA_DOCS_ENABLED", 1),
        ("SOLARA_GOOGLE_PLACES_DESTINATION_PAGE_SIZE", "many"),
        ("SOLARA_GOOGLE_PLACES_DESTINATION_PAGE_SIZE", "0"),
        ("SOLARA_GOOGLE_PLACES_DESTINATION_PAGE_SIZE", "21"),
        ("SOLARA_GOOGLE_PLACES_ATTRACTION_MAX_RESULTS", "0"),
        ("SOLARA_OPENAI_MAX_OUTPUT_TOKENS", 1200),
        ("SOLARA_OPENAI_MAX_OUTPUT_TOKENS", "0"),
        ("SOLARA_OPENAI_TIMEOUT_SECONDS", "quick"),
        ("SOLARA_OPENAI_TIMEOUT_SECONDS", "nan"),
        ("SOLARA_OPENAI_TIMEOUT_SECONDS", "0"),
        ("SOLARA_GOOGLE_PLACES_ATTRACTION_RADIUS_METERS", "50001"),
        ("SOLARA_COMFORT_MIN_CELSIUS", "-101"),
        ("SOLARA_COMFORT_MAX_CELSIUS", "61"),
        ("SOLARA_SEASONAL_WEIGHT", "1.1"),
        ("SOLARA_HISTORICAL_START_DATE", "not-a-date"),
        ("SOLARA_HISTORICAL_START_DATE", "20200101"),
    ],
)
def test_invalid_optional_values_name_the_variable_without_echoing_it(
    name: str,
    value: object,
) -> None:
    environ: dict[str, object] = dict(REQUIRED)
    environ[name] = value

    with pytest.raises(DeploymentConfigurationError) as caught:
        load_deployment_settings(environ)  # type: ignore[arg-type]

    assert name in str(caught.value)
    if isinstance(value, str) and value not in {"0", "21"}:
        assert value not in str(caught.value)


def test_historical_date_order_names_both_variables() -> None:
    with pytest.raises(DeploymentConfigurationError) as caught:
        load_deployment_settings(
            {
                **REQUIRED,
                "SOLARA_HISTORICAL_START_DATE": "2024-01-01",
                "SOLARA_HISTORICAL_END_DATE": "2023-01-01",
            }
        )

    assert "SOLARA_HISTORICAL_START_DATE" in str(caught.value)
    assert "SOLARA_HISTORICAL_END_DATE" in str(caught.value)


def test_comfort_order_names_both_variables() -> None:
    with pytest.raises(DeploymentConfigurationError) as caught:
        load_deployment_settings(
            {
                **REQUIRED,
                "SOLARA_COMFORT_MIN_CELSIUS": "30",
                "SOLARA_COMFORT_MAX_CELSIUS": "20",
            }
        )

    assert "SOLARA_COMFORT_MIN_CELSIUS" in str(caught.value)
    assert "SOLARA_COMFORT_MAX_CELSIUS" in str(caught.value)
