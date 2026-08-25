"""Contracts for the editorial homepage inspiration experience."""

from pathlib import Path

from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app
from solara_travel.presentation.web.assets import STATIC_DIRECTORY

TRAVEL_FILES = (
    "bali.webp",
    "budapest.webp",
    "cape-town.webp",
    "cebu.webp",
    "istanbul.webp",
    "kyoto.webp",
)


def _client() -> TestClient:
    return TestClient(create_app())


def test_editorial_page_order_and_real_navigation_contract() -> None:
    html = _client().get("/").text

    hero = html.index('class="hero shell"')
    escapes = html.index('id="popular-escapes"')
    planner = html.index('id="recommendation-workspace"')
    results = html.index('id="recommendation-results"')
    assert hero < escapes < planner < results
    for target in ("how-solara-works", "popular-escapes", "recommendation-workspace"):
        assert f'href="#{target}"' in html
    for unsupported in ("Sign in", "Account", "Careers", "Blog", "Press"):
        assert unsupported not in html


def test_hero_and_popular_escape_images_are_local_and_sized() -> None:
    html = _client().get("/").text
    hero_start = html.index('class="hero-travel-image hero-slide')
    hero_tag = html[hero_start : html.index(">", hero_start)]
    assert 'src="/static/travel/cape-town.webp"' in hero_tag
    assert 'width="1280"' in hero_tag
    assert 'height="720"' in hero_tag
    assert 'fetchpriority="high"' in hero_tag
    assert 'loading="lazy"' not in hero_tag
    assert html.count('loading="lazy"') == len(TRAVEL_FILES)
    assert "http://" not in html
    assert "https://" not in html


def test_popular_escapes_are_curated_actions_not_popularity_claims() -> None:
    html = _client().get("/").text

    for destination in (
        "Budapest, Hungary",
        "Kyoto, Japan",
        "Cape Town, South Africa",
        "Bali, Indonesia",
        "Cebu, Philippines",
        "Istanbul, T&uuml;rkiye",
    ):
        assert destination in html
    assert html.count("Plan this escape") == len(TRAVEL_FILES)
    assert "most popular according to our data" not in html.casefold()


def test_travel_assets_are_packaged_webp_files_with_bounded_total_size() -> None:
    travel_directory = STATIC_DIRECTORY / "travel"

    assert travel_directory.is_dir()
    assert {path.name for path in travel_directory.iterdir()} == set(TRAVEL_FILES)
    assert sum(path.stat().st_size for path in travel_directory.iterdir()) < 4_000_000
    for filename in TRAVEL_FILES:
        path = travel_directory / filename
        assert path.read_bytes()[:4] == b"RIFF"
        response = _client().get(f"/static/travel/{filename}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"


def test_image_credits_cover_every_committed_travel_asset() -> None:
    credits = Path("docs/image-credits.md").read_text(encoding="utf-8")

    for filename in TRAVEL_FILES:
        assert f"`{filename}`" in credits
    assert "Wikimedia Commons" in credits
    assert "CC BY-SA 4.0" in credits
    assert "CC BY 4.0" in credits
    assert "CC0 1.0" in credits
    assert "Public-domain release" in credits


def test_inspiration_script_is_small_safe_and_provider_independent() -> None:
    script = _client().get("/static/inspiration.js").text
    html = _client().get("/").text

    for marker in (
        "scrollBy",
        "scrollIntoView",
        "prefers-reduced-motion",
        "solara:add-destination",
        "data-escape-destination",
    ):
        assert marker in script
    for forbidden in (
        "fetch(",
        "setTimeout",
        "localStorage",
        "sessionStorage",
        "innerHTML",
        "http://",
        "https://",
    ):
        assert forbidden not in script
    assert "setInterval" in script
    assert "visibilitychange" in script
    assert "Pause carousel" in html
    assert "Pause slideshow" in html
