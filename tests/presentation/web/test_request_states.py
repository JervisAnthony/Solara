"""Tests for accessible browser validation and request-state contracts."""

import re

from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app


def _asset(path: str) -> str:
    response = TestClient(create_app()).get(path)
    assert response.status_code == 200
    return response.text


def _root_html() -> str:
    return _asset("/")


def _tag_with_id(html: str, tag: str, element_id: str) -> str:
    match = re.search(rf'<{tag}[^>]*id="{element_id}"[^>]*>', html)
    assert match is not None
    return match.group()


def test_form_exposes_initially_hidden_accessible_validation_feedback() -> None:
    html = _root_html()
    form = _tag_with_id(html, "form", "recommendation-form")
    summary = _tag_with_id(html, "section", "recommendation-validation-summary")

    assert "novalidate" in form
    assert 'role="alert"' in summary
    assert 'tabindex="-1"' in summary
    assert "hidden" in summary
    assert 'id="recommendation-validation-list"' in html

    for field_id, error_id in (
        ("travel-start-date", "travel-start-date-error"),
        ("travel-end-date", "travel-end-date-error"),
        ("interests", "interests-error"),
        ("preferred-pace", "preferred-pace-error"),
        ("preferred-climate", "preferred-climate-error"),
    ):
        field = _tag_with_id(html, "input", field_id)
        error = _tag_with_id(html, "p", error_id)
        assert error_id in field
        assert "hidden" in error

    for field_id in ("travel-start-date", "travel-end-date"):
        assert "required" in _tag_with_id(html, "input", field_id)


def test_form_exposes_loading_and_request_error_controls() -> None:
    html = _root_html()
    submit = _tag_with_id(html, "button", "recommendation-submit")
    error = _tag_with_id(html, "section", "recommendation-request-error")
    retry = _tag_with_id(html, "button", "recommendation-request-retry")

    assert 'type="submit"' in submit
    assert "Compare destinations" in html[html.index(submit) :]
    assert 'role="alert"' in error
    assert 'tabindex="-1"' in error
    assert "hidden" in error
    assert 'id="recommendation-request-error-title"' in html
    assert 'id="recommendation-request-error-message"' in html
    assert 'type="button"' in retry
    assert "hidden" in retry


def test_results_expose_an_initially_hidden_semantic_empty_state() -> None:
    html = _root_html()
    results_start = html.index('id="recommendation-results"')
    results_end = html.index('class="principles"')
    results_html = html[results_start:results_end]
    empty = _tag_with_id(results_html, "article", "recommendation-empty")

    assert "hidden" in empty
    assert '<h3 id="recommendation-empty-title"' in results_html
    assert 'id="recommendation-empty-message"' in results_html
    assert 'role="alert"' not in empty


def test_app_script_protects_validation_and_loading_lifecycle() -> None:
    script = _asset("/static/app.js")

    for marker in (
        "requestInFlight",
        "aria-busy",
        ".disabled",
        "Compare destinations",
        "Comparing",
        "solara:recommendation-request-start",
        "solara:recommendation-ready",
        "form.requestSubmit()",
        "response.status",
        "detail.code",
        "endDate < startDate",
        'interest === ""',
        "normalizedInterests.has",
    ):
        assert marker in script


def test_app_script_maps_stable_api_errors_to_local_copy() -> None:
    script = _asset("/static/app.js")

    for code in (
        "recommendation_service_unconfigured",
        "provider_authentication_failed",
        "provider_rate_limited",
        "provider_invalid_response",
        "provider_unavailable",
        "provider_error",
        "invalid_recommendation_request",
        "recommendation_rate_limited",
        "recommendation_budget_exhausted",
        "recommendation_capacity_reached",
    ):
        assert code in script

    for safe_copy in (
        "Recommendations aren't available yet",
        "Travel data is busy right now",
        "Can't reach Solara right now",
        "Something went wrong",
        "Solara is taking a short pause",
        "Solara has reached its current preview allowance",
        "Solara is busy right now",
    ):
        assert safe_copy in script


def test_app_script_applies_a_safe_bounded_429_cooldown_without_auto_retry() -> None:
    script = _asset("/static/app.js")

    for marker in (
        'response.headers.get("Retry-After")',
        "Number.parseInt",
        "Number.isSafeInteger",
        "seconds <= 0",
        "maximumCooldownSeconds = 86400",
        "defaultCooldownSeconds = 60",
        "cooldownActive",
        "window.setTimeout",
        "submitButton.disabled = loading || cooldownActive",
        "retryButton.disabled = true",
        "retryButton.disabled = false",
        "requestInFlight || cooldownActive",
        "You can try again in about",
    ):
        assert marker in script
    assert "form.requestSubmit()" in script
    assert "setTimeout(() => form.requestSubmit" not in script
    assert "setInterval" not in script
    assert "detail.message" not in script[script.index("function classifyRequestError") :]


def test_browser_scripts_avoid_unsafe_dom_and_persistence_apis() -> None:
    for asset in ("/static/app.js", "/static/results.js", "/static/feedback.js"):
        script = _asset(asset)
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
            "document.cookie",
            "console.",
        ):
            assert forbidden not in script
