"""Tests for the packaged Solara web shell."""

import re

from fastapi.testclient import TestClient

from solara_travel.presentation.api import ApiSettings, create_app
from solara_travel.presentation.web.assets import INDEX_DOCUMENT, STATIC_DIRECTORY

BRANDING_FILENAMES = (
    "solara-logo-horizontal.png",
    "solara-logo-stacked.png",
    "solara-mark-gold.png",
    "solara-logo-monochrome.png",
)


def test_packaged_web_resources_resolve_from_the_web_package() -> None:
    assert INDEX_DOCUMENT.is_file()
    assert INDEX_DOCUMENT.name == "index.html"
    assert INDEX_DOCUMENT.parent.name == "templates"
    assert STATIC_DIRECTORY.is_dir()
    assert (STATIC_DIRECTORY / "styles.css").is_file()
    assert (STATIC_DIRECTORY / "app.js").is_file()
    assert (STATIC_DIRECTORY / "results.js").is_file()
    assert (STATIC_DIRECTORY / "feedback.js").is_file()
    branding_directory = STATIC_DIRECTORY / "branding"
    assert branding_directory.is_dir()
    assert {path.name for path in branding_directory.iterdir()} == set(BRANDING_FILENAMES)


def test_root_returns_semantic_solara_html_shell() -> None:
    response = TestClient(create_app()).get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert html.casefold().startswith("<!doctype html>")
    assert '<html lang="en">' in html
    assert '<meta name="viewport"' in html
    assert re.search(r"<title>[^<]*Solara[^<]*</title>", html)
    assert 'href="/static/styles.css"' in html
    assert 'href="#main-content"' in html
    assert '<main id="main-content"' in html
    assert 'id="recommendation-workspace"' in html
    assert html.count("<h1") == 1
    assert "Solara" in html
    assert "Development preview" in html
    assert "Season-smart travel intelligence" in html
    assert "Travel that fits the season &mdash; and you." in html
    assert "A clearer starting point" in html
    assert 'href="#recommendation-workspace"' in html


def test_shell_uses_every_approved_local_brand_asset() -> None:
    html = TestClient(create_app()).get("/").text

    for filename in BRANDING_FILENAMES:
        assert f'/static/branding/{filename}' in html
    assert 'rel="icon"' in html
    assert 'href="/static/branding/solara-mark-gold.png"' in html
    assert "<picture" not in html
    assert "data:image" not in html


def test_shell_preserves_the_recommendation_results_milestone_boundary() -> None:
    html = TestClient(create_app()).get("/").text.casefold()

    assert "http://" not in html
    assert "https://" not in html
    assert "sunspire bay" not in html
    assert "mistral hollow" not in html
    assert "frostglass vale" not in html


def test_packaged_stylesheet_is_served_with_stable_design_foundations() -> None:
    response = TestClient(create_app()).get("/static/styles.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    css = response.text
    assert css.strip()
    assert ":root" in css
    assert "--color-accent" in css
    assert ".recommendation-workspace" in css
    assert ":focus-visible" in css
    assert "@media" in css
    assert "@import" not in css
    assert "http://" not in css
    assert "https://" not in css
    for marker in (
        "--color-canvas",
        "--font-display",
        ".hero-visual",
        ".brand-lockup",
        ".feedback-shell",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert marker in css


def test_approved_brand_assets_are_served_as_png_files() -> None:
    client = TestClient(create_app())

    for filename in BRANDING_FILENAMES:
        response = client.get(f"/static/branding/{filename}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_static_mount_returns_404_for_unknown_asset() -> None:
    response = TestClient(create_app()).get("/static/does-not-exist.css")

    assert response.status_code == 404


def test_web_shell_and_assets_are_independent_of_api_documentation_policy() -> None:
    client = TestClient(create_app(ApiSettings(docs_enabled=False)))

    assert client.get("/").status_code == 200
    assert client.get("/static/styles.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/results.js").status_code == 200
    assert client.get("/static/feedback.js").status_code == 200
    for filename in BRANDING_FILENAMES:
        assert client.get(f"/static/branding/{filename}").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 200


def test_root_and_static_mount_are_excluded_from_openapi() -> None:
    paths = TestClient(create_app()).get("/openapi.json").json()["paths"]

    assert set(paths) == {"/health", "/api/v1/recommendations", "/api/v1/feedback"}
    assert "/" not in paths
    assert all(not path.startswith("/static") for path in paths)
