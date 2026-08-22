"""Tests for browser request references and tester-feedback contracts."""

import re

from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def _root_html() -> str:
    return _client().get("/").text


def _tag_with_id(html: str, tag: str, element_id: str) -> str:
    match = re.search(rf'<{tag}\b[^>]*\bid="{re.escape(element_id)}"[^>]*>', html)
    assert match is not None
    return match.group(0)


def test_root_exposes_an_initially_hidden_opaque_request_reference() -> None:
    html = _root_html()
    reference = _tag_with_id(html, "p", "recommendation-request-reference")

    assert "hidden" in reference
    assert "Request reference:" in html
    assert '<code id="recommendation-request-reference-value"></code>' in html
    assert not re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        html,
        re.IGNORECASE,
    )


def test_feedback_section_uses_accessible_semantic_controls() -> None:
    html = _root_html()
    feedback_start = html.index('id="tester-feedback"')
    principles_start = html.index('class="principles"')
    feedback_html = html[feedback_start:principles_start]

    assert feedback_start < principles_start
    assert '<h2 id="tester-feedback-title">Help improve Solara</h2>' in feedback_html
    assert _tag_with_id(feedback_html, "form", "tester-feedback-form")
    assert "<fieldset>" in feedback_html
    assert "<legend>How useful was this experience?</legend>" in feedback_html
    for value in ("helpful", "mixed", "not_helpful"):
        assert f'value="{value}"' in feedback_html
    assert "required" in feedback_html
    assert '<label for="feedback-comment">' in feedback_html
    comment = _tag_with_id(feedback_html, "textarea", "feedback-comment")
    assert 'maxlength="1000"' in comment
    assert 'aria-describedby="feedback-comment-help feedback-privacy-note"' in comment
    assert "Please don't include names, contact details, passwords" in feedback_html
    submit = _tag_with_id(feedback_html, "button", "feedback-submit")
    status = _tag_with_id(feedback_html, "p", "feedback-status")
    assert 'type="submit"' in submit
    assert 'role="status"' in status
    assert 'aria-live="polite"' in status
    assert 'aria-atomic="true"' in status
    assert "tabindex=" not in feedback_html


def test_feedback_script_is_packaged_and_loaded_after_recommendation_scripts() -> None:
    html = _root_html()
    response = _client().get("/static/feedback.js")

    assert response.status_code == 200
    assert response.text.strip()
    assert '<script src="/static/feedback.js" defer></script>' in html
    assert html.index("/static/app.js") < html.index("/static/results.js")
    assert html.index("/static/results.js") < html.index("/static/feedback.js")
    assert _client().get("/static/not-real.js").status_code == 404


def test_app_script_captures_handled_request_ids_transiently() -> None:
    script = _client().get("/static/app.js").text

    for marker in (
        'response.headers.get("X-Request-ID")',
        "requestId",
        "recommendationRequestId",
        "recommendation-request-reference",
        "clearRequestReference",
        "showRequestReference",
        "delete form.dataset.recommendationRequestId",
        "{ payload: responsePayload, requestId }",
    ):
        assert marker in script
    assert "uuid" not in script.casefold()


def test_feedback_script_posts_only_the_typed_payload_and_manages_submission_state() -> None:
    script = _client().get("/static/feedback.js").text

    for marker in (
        '"/api/v1/feedback"',
        "recommendation_request_id",
        "rating:",
        "comment:",
        "feedbackInFlight",
        "Sending",
        "response.ok",
        "response.status !== 202",
        "feedbackForm.reset()",
        "recommendationForm.dataset.recommendationRequestId",
        'Accept: "application/json"',
        '"Content-Type": "application/json"',
    ):
        assert marker in script
    assert "fetch(recommendation" not in script


def test_feedback_429_preserves_input_and_applies_safe_bounded_cooldown() -> None:
    script = _client().get("/static/feedback.js").text

    for marker in (
        "response.status === 429",
        'response.headers.get("Retry-After")',
        "Number.parseInt",
        "Number.isSafeInteger",
        "seconds <= 0",
        "maximumCooldownSeconds = 86400",
        "defaultCooldownSeconds = 60",
        "feedbackInFlight || cooldownActive",
        "feedbackSubmit.disabled = loading || cooldownActive",
        "window.setTimeout",
        "Solara is receiving a lot of feedback right now",
        "You can try again in about",
    ):
        assert marker in script
    rate_limit_branch = script[
        script.index("if (response.status === 429)") : script.index(
            "if (!response.ok || response.status !== 202)"
        )
    ]
    assert "feedbackForm.reset()" not in rate_limit_branch
    assert "response.json" not in script
    assert "setInterval" not in script
    assert "fetch(feedbackEndpoint" in script


def test_all_browser_scripts_avoid_unsafe_dom_tracking_and_external_requests() -> None:
    for path in ("/static/app.js", "/static/results.js", "/static/feedback.js"):
        script = _client().get(path).text
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
            "indexedDB",
            "document.cookie",
            "navigator.userAgent",
            "navigator.geolocation",
            "screen.",
            "http://",
            "https://",
            "console.",
        ):
            assert forbidden not in script


def test_feedback_styles_include_responsive_wrapping_and_touch_friendly_controls() -> None:
    styles = _client().get("/static/styles.css").text

    for marker in (
        ".request-reference code",
        "overflow-wrap: anywhere",
        ".tester-feedback",
        ".feedback-rating",
        ".feedback-comment-field textarea",
        "width: 100%",
        "min-height: 3rem",
        "@media (max-width: 48rem)",
        "@media (max-width: 32rem)",
    ):
        assert marker in styles
