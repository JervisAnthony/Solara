"""Tests for live-provider composition without startup network access."""

import pytest

from solara_travel.config import (
    DeploymentSettings,
    GooglePlacesSettings,
    OpenAINarrationSettings,
    OpenMeteoSettings,
    RecommendationPolicySettings,
)
from solara_travel.infrastructure.http import UrllibJsonHttpTransport
from solara_travel.infrastructure.narration import OpenAIResponsesNarrationProvider
from solara_travel.infrastructure.places import GooglePlacesHttpClient, GooglePlacesProvider
from solara_travel.infrastructure.weather import (
    OpenMeteoHistoricalWeatherHttpClient,
    OpenMeteoHistoricalWeatherProvider,
)
from solara_travel.workflows import HostedServices, build_hosted_services


def _settings() -> DeploymentSettings:
    return DeploymentSettings(
        google_places=GooglePlacesSettings(
            "sentinel-google-secret",
            timeout_seconds=4.0,
            destination_page_size=7,
            attraction_max_results=8,
            attraction_radius_meters=9000.0,
        ),
        open_meteo=OpenMeteoSettings(timeout_seconds=5.0),
        openai_narration=OpenAINarrationSettings(
            "sentinel-openai-secret",
            "test-model",
            timeout_seconds=6.0,
            max_output_tokens=700,
        ),
        recommendation_policy=RecommendationPolicySettings(
            comfort_min_celsius=17.0,
            comfort_max_celsius=27.0,
            comfort_tolerance_celsius=9.0,
            seasonal_weight=0.8,
        ),
    )


def test_hosted_services_use_configured_live_providers_and_one_transport() -> None:
    services = build_hosted_services(_settings())
    recommendation = services.recommendation_service
    narration = services.narration_service

    assert isinstance(services, HostedServices)
    assert isinstance(recommendation.places_provider, GooglePlacesProvider)
    assert isinstance(recommendation.places_provider.client, GooglePlacesHttpClient)
    assert recommendation.places_provider.client.destination_page_size == 7
    assert recommendation.places_provider.client.attraction_max_results == 8
    assert recommendation.places_provider.client.attraction_radius_meters == 9000.0
    assert isinstance(recommendation.weather_provider, OpenMeteoHistoricalWeatherProvider)
    assert isinstance(
        recommendation.weather_provider.client,
        OpenMeteoHistoricalWeatherHttpClient,
    )
    assert recommendation.historical_period.start_date.isoformat() == "2020-01-01"
    assert recommendation.historical_period.end_date.isoformat() == "2024-12-31"
    assert recommendation.comfort_range.minimum_celsius == 17.0
    assert recommendation.comfort_range.maximum_celsius == 27.0
    assert recommendation.comfort_range.tolerance_celsius == 9.0
    assert recommendation.seasonal_weight == 0.8
    assert isinstance(narration.provider, OpenAIResponsesNarrationProvider)
    assert narration.provider.model == "test-model"
    assert narration.provider.timeout_seconds == 6.0
    assert narration.provider.max_output_tokens == 700

    transport = recommendation.places_provider.client.transport
    assert isinstance(transport, UrllibJsonHttpTransport)
    assert recommendation.weather_provider.client.transport is transport
    assert narration.provider.transport is transport


def test_hosted_dependency_repr_hides_both_secrets() -> None:
    text = repr(build_hosted_services(_settings()))

    assert "sentinel-google-secret" not in text
    assert "sentinel-openai-secret" not in text


def test_hosted_factory_requires_deployment_settings() -> None:
    with pytest.raises(TypeError, match="DeploymentSettings"):
        build_hosted_services(object())  # type: ignore[arg-type]
