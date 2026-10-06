"""Release fingerprints identify bytes, not version numbers or build clocks."""

import re
from hashlib import sha256
from shutil import copytree

import pytest
from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app
from solara_travel.presentation.web import assets


def test_every_functional_asset_is_versioned_and_delivered_with_matching_bytes():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.headers["cache-control"] == "no-cache"
    urls = re.findall(r'(?:src|href)="(/static/[^" ]+\.(?:js|css)\?v=[0-9a-f]{16})"', response.text)
    assert len(urls) == len(assets.FUNCTIONAL_ASSETS) == 8
    assert set(urls) == {assets.asset_url(name) for name in assets.FUNCTIONAL_ASSETS}
    for name in assets.FUNCTIONAL_ASSETS:
        assert f'/static/{name}"' not in response.text
        resource = client.get(assets.asset_url(name))
        assert resource.status_code == 200
        assert resource.content == (assets.STATIC_DIRECTORY / name).read_bytes()
        assert assets.asset_url(name).endswith(sha256(resource.content).hexdigest()[:16])
    assert 'href="/static/branding/solara-mark-gold.png"' in response.text
    assert "/static/travel/cape-town.webp" in response.text
    assert client.get("/static/travel/cape-town.webp").headers.get("cache-control") != "no-cache"


def test_new_html_never_references_old_functional_javascript_after_content_change(
    tmp_path, monkeypatch
):
    """Regression for mixed HTML/JS releases; deliberately keep package version fixed."""
    copytree(assets.STATIC_DIRECTORY, tmp_path / "assets")
    monkeypatch.setattr(assets, "STATIC_DIRECTORY", tmp_path / "assets")
    monkeypatch.setattr("solara_travel.presentation.api.app.STATIC_DIRECTORY", tmp_path / "assets")
    client = TestClient(create_app())
    original = client.get("/").text
    old_url = assets.asset_url("app.js")
    assert old_url in original
    (tmp_path / "assets/app.js").write_bytes(b"// Changed fixture bytes only\n")
    updated = client.get("/").text
    new_url = assets.asset_url("app.js")
    assert old_url != new_url
    assert new_url in updated and old_url not in updated
    assert client.get(new_url).content == b"// Changed fixture bytes only\n"
    assert assets.asset_url("results.js") in original and assets.asset_url("results.js") in updated


def test_fingerprint_is_deterministic_and_independent_of_path(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.write_bytes(b"same")
    second.write_bytes(b"same")
    assert assets.asset_fingerprint(first.read_bytes()) == assets.asset_fingerprint(
        second.read_bytes()
    )
    assert assets.asset_fingerprint(b"same") != assets.asset_fingerprint(b"changed")
    with pytest.raises(ValueError):
        assets.asset_url("../secret")
