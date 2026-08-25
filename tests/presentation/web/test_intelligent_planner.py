"""Static contracts for the Phase 2A traveller-first planner."""

from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app


def _asset(path: str) -> str:
    response = TestClient(create_app()).get(path)
    assert response.status_code == 200
    return response.text


def test_typeahead_markup_and_small_same_origin_script_are_accessible() -> None:
    html = _asset("/")
    script = _asset("/static/travel-scopes.js")

    assert html.index("/static/travel-scopes.js") < html.index("/static/app.js")
    for marker in (
        'role="combobox"',
        'aria-autocomplete="list"',
        'aria-controls="destination-suggestions"',
        'role="listbox"',
        'translate="no">Google Maps',
    ):
        assert marker in html
    for marker in (
        '"/api/v1/travel-scope-suggestions"',
        "debounceMilliseconds = 350",
        "AbortController",
        "requestSequence",
        'event.key === "ArrowDown"',
        'event.key === "ArrowUp"',
        'event.key === "Escape"',
        'role", "option"',
        "textContent",
    ):
        assert marker in script
    for forbidden in (
        "innerHTML",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "geolocation",
        "User-Agent",
        "X-Forwarded-For",
        "http://",
        "https://",
        "console.",
        "eval(",
    ):
        assert forbidden not in script


def test_guided_interests_pace_climate_and_trip_context_are_explicit() -> None:
    html = _asset("/")
    for value in (
        "beaches",
        "islands",
        "food",
        "history",
        "architecture",
        "art_and_culture",
        "nature",
        "adventure",
        "hiking",
        "diving_and_snorkelling",
        "wildlife",
        "nightlife",
        "wellness",
        "shopping",
        "photography",
        "local_experiences",
    ):
        assert f'name="guided-interest" value="{value}"' in html
    for value in ("slow", "relaxed", "balanced", "active", "fast_paced"):
        assert f'data-value="{value}"' in html
    for value in (
        "hot_tropical",
        "warm_sunny",
        "warm_dry",
        "mild",
        "cool",
        "cold_snowy",
    ):
        assert f'data-value="{value}"' in html
    assert "Describe where you're looking to vacation" in html
    assert 'id="trip-description"' in html
    assert 'maxlength="1000"' in html
    assert 'id="trip-description-count"' in html
    assert 'rows="5"' in html
    assert 'role="combobox"' in html
    assert 'role="option"' in html
    assert '<script src="/static/selects.js" defer></script>' in html


def test_how_solara_works_is_a_dedicated_four_step_traveller_section() -> None:
    html = _asset("/")
    start = html.index('id="how-solara-works"')
    end = html.index('id="recommendation-workspace"')
    section = html[start:end]

    assert 'href="#how-solara-works"' in html
    assert section.count("<li>") == 4
    assert "Set the map" in section
    assert "Share your rhythm" in section
    assert "Discover a shortlist" in section
    assert "Choose confidently" in section
    for internal_term in ("LLM", "weighted contribution", "configured tolerance"):
        assert internal_term not in section


def test_motion_scripts_are_isolated_from_recommendation_logic() -> None:
    inspiration = _asset("/static/inspiration.js")
    planner = _asset("/static/app.js")

    assert "intervalMilliseconds = 3000" in inspiration
    assert "visibilitychange" in inspiration
    assert "prefers-reduced-motion" in inspiration
    assert "Pause slideshow" in inspiration
    assert "Pause carousel" in inspiration
    assert "setInterval" not in planner
    assert "data-hero-slideshow" not in planner
