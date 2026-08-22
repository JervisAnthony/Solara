"""Tests for the environment-driven hosted FastAPI factory."""

import importlib

from fastapi.testclient import TestClient

from solara_travel.config import DeploymentConfigurationError
from solara_travel.infrastructure.narration import OpenAIResponsesNarrationProvider
from solara_travel.infrastructure.places import GooglePlacesProvider
from solara_travel.infrastructure.weather import OpenMeteoHistoricalWeatherProvider
from solara_travel.presentation.api.deployment import create_deployment_app

FAKE_ENV = {
    "SOLARA_GOOGLE_PLACES_API_KEY": "test-google-key",
    "SOLARA_OPENAI_API_KEY": "test-openai-key",
    "SOLARA_OPENAI_MODEL": "test-model",
}


def test_deployment_module_import_is_safe_without_configuration() -> None:
    module = importlib.import_module("solara_travel.presentation.api.deployment")

    assert module.create_deployment_app is create_deployment_app


def test_deployment_factory_requires_hosted_configuration_only_when_invoked() -> None:
    try:
        create_deployment_app(environ={})
    except DeploymentConfigurationError as exc:
        assert "SOLARA_GOOGLE_PLACES_API_KEY" in str(exc)
    else:  # pragma: no cover - documents the required startup failure
        raise AssertionError("missing deployment configuration was accepted")


def test_deployment_factory_builds_provider_graph_without_network_calls() -> None:
    app = create_deployment_app(environ=FAKE_ENV)
    dependencies = app.state.api_dependencies

    assert isinstance(dependencies.recommendation_service.places_provider, GooglePlacesProvider)
    assert isinstance(
        dependencies.recommendation_service.weather_provider,
        OpenMeteoHistoricalWeatherProvider,
    )
    assert isinstance(dependencies.narration_service.provider, OpenAIResponsesNarrationProvider)
    assert "test-google-key" not in repr(dependencies)
    assert "test-openai-key" not in repr(dependencies)


def test_hosted_docs_default_off_preserves_root_health_and_openapi() -> None:
    with TestClient(create_deployment_app(environ=FAKE_ENV)) as client:
        assert client.get("/").status_code == 200
        assert client.get("/health").status_code == 200
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 200


def test_deployment_factory_applies_overrides_to_independent_app_state() -> None:
    first = create_deployment_app(
        environ={
            **FAKE_ENV,
            "SOLARA_DOCS_ENABLED": "true",
            "SOLARA_RECOMMENDATION_RATE_LIMIT": "2",
        }
    )
    second = create_deployment_app(environ=FAKE_ENV)

    assert first.docs_url == "/docs"
    assert second.docs_url is None
    assert first.state.api_safeguards is not second.state.api_safeguards
    assert first.state.api_dependencies is not second.state.api_dependencies
