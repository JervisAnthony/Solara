"""Tests for FastAPI application composition and HTTP surface."""

import importlib
from importlib import metadata

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from solara_travel.presentation.api import ApiDependencies, ApiSettings, create_app

app_module = importlib.import_module("solara_travel.presentation.api.app")


def test_factory_returns_distinct_fastapi_instances() -> None:
    first = create_app()
    second = create_app()

    assert isinstance(first, FastAPI)
    assert isinstance(second, FastAPI)
    assert first is not second
    assert isinstance(app_module.app, FastAPI)
    assert isinstance(first.state.api_dependencies, ApiDependencies)
    assert first.state.api_dependencies is not second.state.api_dependencies


def test_factory_uses_stable_distribution_metadata() -> None:
    application = create_app()

    assert application.title == "Solara Travel API"
    assert application.version == metadata.version("solara-travel-ai")
    assert application.version


def test_factory_uses_uninstalled_version_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_distribution(distribution_name: str) -> str:
        assert distribution_name == "solara-travel-ai"
        raise metadata.PackageNotFoundError(distribution_name)

    monkeypatch.setattr(app_module.metadata, "version", missing_distribution)

    assert create_app().version == "0.0.0+uninstalled"


@pytest.mark.parametrize("settings", [object(), {"docs_enabled": False}, False])
def test_factory_rejects_invalid_settings(settings: object) -> None:
    with pytest.raises(TypeError, match="settings must be ApiSettings or None"):
        create_app(settings)  # type: ignore[arg-type]


@pytest.mark.parametrize("dependencies", [object(), {}, False])
def test_factory_rejects_invalid_dependencies(dependencies: object) -> None:
    with pytest.raises(TypeError, match="dependencies must be ApiDependencies or None"):
        create_app(dependencies=dependencies)  # type: ignore[arg-type]


def test_factory_stores_only_supplied_dependencies_on_created_application() -> None:
    dependencies = ApiDependencies()

    application = create_app(ApiSettings(docs_enabled=False), dependencies=dependencies)

    assert application.state.api_dependencies is dependencies
    assert app_module.app.state.api_dependencies is not dependencies


def test_health_endpoint_returns_exact_typed_json_response() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")


def test_openapi_exposes_health_and_versioned_recommendation_contracts() -> None:
    response = TestClient(create_app()).get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"] == {
        "title": "Solara Travel API",
        "version": metadata.version("solara-travel-ai"),
    }
    assert set(schema["paths"]) == {"/health", "/api/v1/recommendations"}
    assert "get" in schema["paths"]["/health"]
    recommendation = schema["paths"]["/api/v1/recommendations"]["post"]
    assert recommendation["requestBody"]["content"]["application/json"]["schema"]
    assert recommendation["responses"]["200"]["content"]["application/json"]["schema"]
    assert recommendation["responses"]["502"]["content"]["application/json"]["schema"]
    assert recommendation["responses"]["503"]["content"]["application/json"]["schema"]
    assert "HealthResponse" in schema["components"]["schemas"]
    assert "RecommendationRequestBody" in schema["components"]["schemas"]
    assert "RecommendationResponse" in schema["components"]["schemas"]
    assert "ApiErrorResponse" in schema["components"]["schemas"]


def test_interactive_documentation_is_enabled_by_default() -> None:
    client = TestClient(create_app())

    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_interactive_documentation_can_be_disabled_without_disabling_openapi() -> None:
    client = TestClient(create_app(ApiSettings(docs_enabled=False)))

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/"),
        ("post", "/recommendations"),
        ("post", "/api/recommendations"),
    ],
)
def test_unimplemented_routes_remain_absent(method: str, path: str) -> None:
    response = TestClient(create_app()).request(method, path)

    assert response.status_code == 404
