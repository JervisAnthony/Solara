"""Contracts for the traveller-first Postcards and Wayfinder presentation."""

from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app


def _asset(path: str) -> str:
    response = TestClient(create_app()).get(path)
    assert response.status_code == 200
    return response.text


def test_root_contains_initially_hidden_semantic_results_region() -> None:
    html = _asset("/")
    results_start = html.index('id="recommendation-results"')
    principles_start = html.index('class="principles"')
    region = html[results_start:principles_start]

    assert results_start < principles_start
    assert 'aria-labelledby="results-title"' in region
    assert "hidden" in region[: region.index(">")]
    assert 'id="results-title"' in region
    assert 'id="recommendation-results-summary"' in region
    assert region.count("Seasonal guidance is based on historical patterns") == 1
    assert '<ol id="recommendation-list"' in region
    assert '<script src="/static/results.js" defer></script>' in html
    assert "AI-assisted explanation" not in region
    assert "Optional context" not in region


def test_static_html_contains_no_fixture_results_or_scores() -> None:
    html = _asset("/").casefold()
    for forbidden in ("sunspire bay", "mistral hollow", "frostglass vale", "1.00", "0.68"):
        assert forbidden not in html


def test_results_renderer_exposes_traveller_first_contract() -> None:
    script = _asset("/static/results.js")
    for marker in (
        "solara:recommendation-ready",
        "event.detail",
        "recommendation.rank",
        "recommendation.score",
        "recommendation.postcards",
        "wayfinder?.destination_notes",
        "seasonal_weather",
        "attractions",
        "Seasonal Fit",
        "The Wayfinder",
        "Places to see",
        "Seasonal feel",
        "Good to know",
        "Postcards",
        "Google Maps",
        "replaceChildren",
        "originLabel",
        "administrative_context",
        "recommendation-historical-note",
    ):
        assert marker in script


def test_renderer_preserves_authoritative_order_and_hides_technical_audit_language() -> None:
    script = _asset("/static/results.js")
    assert ".sort(" not in script
    assert ".reverse(" not in script
    assert "response.recommendations.forEach" in script
    assert "percentage(recommendation.score)" in script
    for forbidden in (
        "weighted_contribution",
        '"Weight"',
        '"Weighted contribution"',
        "comfort_range.minimum_celsius",
        "observation_count",
        "historical_year_count",
        "temperature_comfort",
        "component-list",
        "technical details",
    ):
        assert forbidden not in script


def test_postcards_are_manual_lazy_safe_and_have_a_premium_fallback() -> None:
    script = _asset("/static/results.js")
    for marker in (
        "image.dataset.src",
        'image.loading = "lazy"',
        'previous.addEventListener("click"',
        'next.addEventListener("click"',
        'track.addEventListener("touchstart"',
        'track.addEventListener("touchend"',
        "postcard-fallback",
        "author.profile_uri",
        "photo.google_maps_uri",
    ):
        assert marker in script
    assert "setInterval" not in script
    assert "fetch(" not in script
    assert 'googleAttribution.setAttribute("translate", "no")' in script


def test_places_are_locally_bounded_with_an_accessible_toggle() -> None:
    script = _asset("/static/results.js")
    for marker in (
        "index >= 6",
        "See more places",
        "See fewer places",
        'toggle.type = "button"',
        'toggle.setAttribute("aria-controls"',
        'toggle.setAttribute("aria-expanded"',
        'toggle.addEventListener("click"',
    ):
        assert marker in script


def test_results_renderer_uses_safe_same_origin_dom_apis() -> None:
    script = _asset("/static/results.js")
    assert "textContent" in script
    for forbidden in (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "document.write",
        "eval(",
        "new Function",
        "localStorage",
        "sessionStorage",
        "IndexedDB",
        "console.",
        "http://",
        "https://",
    ):
        assert forbidden not in script


def test_results_headings_are_mode_specific_without_internal_names() -> None:
    script = _asset("/static/results.js")
    for copy in (
        "Your shortlist",
        "Places that fit this trip",
        "worth considering",
        "for your trip",
    ):
        assert copy in script
    assert "global discovery mode" not in script
    assert "scope_discovery mode" not in script


def test_results_clear_only_when_a_valid_request_starts() -> None:
    script = _asset("/static/results.js")
    assert '"solara:recommendation-request-start"' in script
    assert 'form.addEventListener("submit", clearResults)' not in script
    assert "resultsSection.hidden = true" in script
    assert "recommendationList.replaceChildren()" in script
    assert "response.has_recommendations === false" in script
    assert "emptyTitle.focus()" in script


def test_editorial_fallback_avoids_repetitive_templates_and_omits_filler() -> None:
    script = _asset("/static/results.js")
    assert "Around this time of year" in script
    assert "Historically, these dates" not in script
    assert "Your dates fall into" not in script
    assert "this seasonal signal" not in script
    assert "if (goodToKnowCopy)" in script
    assert "historical patterns for your dates, not a live weather forecast" not in script
