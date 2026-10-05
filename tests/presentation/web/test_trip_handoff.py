"""Packaged export/disclosure controls and secure presentation boundaries."""

from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app


def test_handoff_controls_are_explicit_and_private_by_default():
    client = TestClient(create_app())
    html = client.get("/").text
    assert 'value="exclude" checked' in html
    assert 'id="export-trip-json"' in html
    assert 'id="export-trip-text"' in html
    assert 'id="handoff-status" role="status" aria-live="polite"' in html
    script = client.get("/static/itinerary.js").text
    for required in (
        "new Blob",
        "URL.createObjectURL",
        "URL.revokeObjectURL",
        "link.download",
        "schema_version: 1",
        "requirements_included",
        "1000000",
        "text/plain;charset=utf-8",
        "application/json",
        "function tripSnapshot",
        "function dateForDay",
    ):
        assert required in script
    assert "fetch(" not in script[script.index("function downloadTrip") :]
    for forbidden in (
        "innerHTML",
        "localStorage",
        "sessionStorage",
        "indexedDB",
        "postMessage",
        "api_key",
        "trip_description",
    ):
        assert forbidden not in script


def test_brand_boundary_does_not_enable_embedding_or_change_runtime_brand():
    client = TestClient(create_app())
    response = client.get("/")
    assert "Solara" in response.text
    assert "Test agency fixture" not in response.text
    assert "<iframe" not in response.text
    assert "access-control-allow-origin" not in response.headers
