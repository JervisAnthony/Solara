"""Tests for the recommendation-results presentation contract."""

from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_root_contains_initially_hidden_semantic_results_region() -> None:
    html = _client().get("/").text
    results_start = html.index('id="recommendation-results"')
    principles_start = html.index('class="principles"')

    assert results_start < principles_start
    assert '<section\n        id="recommendation-results"' in html
    assert 'aria-labelledby="results-title"' in html[results_start:]
    assert "hidden" in html[results_start : html.index(">", results_start)]
    for marker in (
        'id="results-title"',
        'id="recommendation-results-summary"',
        'id="recommendation-list"',
        'id="recommendation-narration"',
        'id="recommendation-narration-text"',
    ):
        assert marker in html[results_start:principles_start]
    assert '<ol id="recommendation-list"' in html
    assert '<script src="/static/results.js" defer></script>' in html


def test_static_html_contains_no_fixture_results_or_scores() -> None:
    html = _client().get("/").text.casefold()

    for forbidden in (
        "sunspire bay",
        "mistral hollow",
        "frostglass vale",
        "1.00",
        "0.68",
        "0.00",
    ):
        assert forbidden not in html


def test_results_javascript_asset_exposes_authoritative_response_contract() -> None:
    response = _client().get("/static/results.js")

    assert response.status_code == 200
    assert response.headers["content-type"].split(";", 1)[0] in {
        "application/javascript",
        "text/javascript",
    }
    script = response.text
    assert script.strip()
    for marker in (
        "solara:recommendation-ready",
        "event.detail",
        "recommendations",
        "recommendation.rank",
        "recommendation.score",
        "components",
        "evidence",
        "attractions",
        "seasonal_weather",
        "temperature_comfort",
        "narration",
        "recommendation_count",
        "destination_mode",
        "destination_queries",
        "replaceChildren",
    ):
        assert marker in script


def test_results_renderer_preserves_order_and_zero_scores() -> None:
    script = _client().get("/static/results.js").text

    assert ".sort(" not in script
    assert ".reverse(" not in script
    assert "String(recommendation.rank)" in script
    assert "formatPercentage(recommendation.score)" in script
    assert "if (recommendation.score)" not in script
    assert "index + 1" not in script


def test_results_renderer_formats_seasonal_fit_without_exposing_weighting() -> None:
    script = _client().get("/static/results.js").text

    assert 'appendMetric(score, "Seasonal fit", formatPercentage(recommendation.score))' in script
    assert "maximumFractionDigits" in script
    assert "Number.EPSILON" in script
    for forbidden_label in (
        '"Suitability score"',
        '"Weight"',
        '"Weighted contribution"',
    ):
        assert forbidden_label not in script
    assert "weighted_contribution" not in script


def test_results_renderer_limits_attractions_with_an_accessible_local_toggle() -> None:
    script = _client().get("/static/results.js").text

    for marker in (
        "index >= 6",
        '"Show all attractions"',
        '"Show fewer attractions"',
        'toggle.type = "button"',
        'toggle.setAttribute("aria-controls"',
        'toggle.setAttribute("aria-expanded"',
        'toggle.addEventListener("click"',
    ):
        assert marker in script
    assert "fetch(" not in script


def test_results_renderer_uses_safe_dom_apis_for_response_text() -> None:
    script = _client().get("/static/results.js").text

    assert "textContent" in script
    assert "narrationText.textContent" in script
    for forbidden in (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "document.write",
        "eval(",
        "new Function",
        "fetch(",
        "localStorage",
        "sessionStorage",
        "IndexedDB",
        "console.",
        "http://",
        "https://",
    ):
        assert forbidden not in script


def test_results_renderer_clears_only_when_a_valid_request_starts() -> None:
    script = _client().get("/static/results.js").text

    assert '"solara:recommendation-request-start"' in script
    assert 'form.addEventListener("submit", clearResults)' not in script
    assert "resultsSection.hidden = true" in script
    assert "recommendationList.replaceChildren()" in script
    assert "narrationText.replaceChildren()" in script


def test_results_renderer_reveals_successful_empty_responses() -> None:
    script = _client().get("/static/results.js").text

    assert "response.has_recommendations === false" in script
    assert "emptyState.hidden = false" in script
    assert "resultsSection.hidden = false" in script
    assert "emptyTitle.focus()" in script
    assert '"No recommendations returned this time"' not in script


def test_results_renderer_uses_one_pipeline_with_mode_specific_copy() -> None:
    script = _client().get("/static/results.js").text

    for copy in (
        "Recommended destinations",
        "Destination for your trip",
        "Your destination comparison",
    ):
        assert copy in script
    assert script.count("function renderRecommendationResponse") == 1
