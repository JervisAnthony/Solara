"""Tests for FastAPI application composition and HTTP surface."""

import importlib
from importlib import metadata

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from solara_travel.presentation.api import ApiSettings, create_app

app_module = importlib.import_module("solara_travel.presentation.api.app")


def test_factory_returns_distinct_fastapi_instances() -> None:
    first = create_app()
    second = create_app()

    assert isinstance(first, FastAPI)
    assert isinstance(second, FastAPI)
    assert first is not second
    assert isinstance(app_module.app, FastAPI)


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


def test_health_endpoint_returns_exact_typed_json_response() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")


def test_openapi_exposes_only_the_health_contract() -> None:
    response = TestClient(create_app()).get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"] == {
        "title": "Solara Travel API",
        "version": metadata.version("solara-travel-ai"),
    }
    assert set(schema["paths"]) == {"/health"}
    assert "get" in schema["paths"]["/health"]
    assert "HealthResponse" in schema["components"]["schemas"]


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
        ("post", "/api/v1/recommendations"),
    ],
)
def test_unimplemented_routes_remain_absent(method: str, path: str) -> None:
    response = TestClient(create_app()).request(method, path)

    assert response.status_code == 404
