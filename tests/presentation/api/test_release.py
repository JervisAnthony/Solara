"""Operational release identity never needs provider availability or client identity."""

from importlib import metadata

import pytest
from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app
from solara_travel.presentation.api.routes import release


@pytest.mark.parametrize(
    "revision", [None, "", " ", "a" * 39, "a" * 41, "g" * 40, "sentinel-secret", " a" + "b" * 39]
)
def test_release_rejects_missing_or_invalid_deployment_revision(revision, monkeypatch, caplog):
    if revision is None:
        monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    else:
        monkeypatch.setenv("RENDER_GIT_COMMIT", revision)
    monkeypatch.setenv("SOLARA_OPENAI_API_KEY", "sentinel-private-key")
    client = TestClient(create_app())
    response = client.get(
        "/release", headers={"User-Agent": "sentinel-client", "X-Request-ID": "bad"}
    )
    assert response.status_code == 200
    assert response.json() == {"product": "Solara", "version": "0.1.0", "source_revision": None}
    assert "sentinel" not in response.text
    assert "x-request-id" not in response.headers
    assert "set-cookie" not in response.headers
    assert not caplog.records
    assert client.get("/health").json() == {"status": "ok"}
    assert "/release" not in client.get("/openapi.json").json()["paths"]


def test_release_normalizes_valid_sha_and_uses_installed_version(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "ABCDEF0123" * 4)
    response = TestClient(create_app()).get("/release")
    assert response.json()["source_revision"] == "abcdef0123" * 4
    assert response.json()["version"] == metadata.version("solara-travel-ai") == "0.1.0"


def test_release_has_safe_uninstalled_metadata_fallback(monkeypatch):
    def unavailable(_name):
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(release.metadata, "version", unavailable)
    assert release.get_release().version == "0.0.0+uninstalled"
