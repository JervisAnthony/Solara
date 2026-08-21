"""Tests for the traveller recommendation form and local browser script."""

import re

from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app


def _root_html() -> str:
    return TestClient(create_app()).get("/").text


def test_root_contains_one_accessible_recommendation_form() -> None:
    html = _root_html()
    workspace_start = html.index('id="recommendation-workspace"')
    form_id = html.index('id="recommendation-form"')
    form_start = html.rfind("<form", 0, form_id)

    assert html.count("<form") == 1
    assert workspace_start < form_start
    assert 'aria-labelledby="workspace-title"' in html[form_start:]
    assert 'type="submit"' in html[form_start:]
    assert "Compare destinations" in html[form_start:]


def test_form_has_required_dates_and_optional_preference_fields() -> None:
    html = _root_html()

    for field_id in (
        "travel-start-date",
        "travel-end-date",
        "interests",
        "preferred-pace",
        "preferred-climate",
    ):
        assert f'<label for="{field_id}"' in html
        assert f'id="{field_id}"' in html

    for field_id in ("travel-start-date", "travel-end-date"):
        date_input = re.search(rf'<input[^>]+id="{field_id}"[^>]*>', html)
        assert date_input is not None
        assert 'type="date"' in date_input.group()
        assert "required" in date_input.group()

    assert 'aria-describedby="interests-help interests-error"' in html
    assert 'aria-describedby="preferred-pace-help preferred-pace-error"' in html
    assert 'aria-describedby="preferred-climate-help preferred-climate-error"' in html


def test_form_loads_local_script_and_exposes_polite_status() -> None:
    html = _root_html()

    assert '<script src="/static/app.js" defer></script>' in html
    assert 'id="recommendation-form-status"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html


def test_form_copy_is_truthful_about_current_season_led_scoring() -> None:
    html = _root_html().casefold()

    assert "current preview scoring focuses on seasonal fit" in html
    assert "every preference changes your ranking" not in html


def test_javascript_asset_submits_the_existing_request_contract() -> None:
    response = TestClient(create_app()).get("/static/app.js")

    assert response.status_code == 200
    assert response.headers["content-type"].split(";", 1)[0] in {
        "application/javascript",
        "text/javascript",
    }
    script = response.text
    assert script.strip()
    for marker in (
        "/api/v1/recommendations",
        "fetch(",
        'method: "POST"',
        "application/json",
        "travel_period",
        "start_date",
        "end_date",
        "preferences",
        "interests",
        "preferred_pace",
        "preferred_climate",
        "destination: null",
        "solara:recommendation-ready",
        "textContent",
    ):
        assert marker in script
    assert "http://" not in script
    assert "https://" not in script


def test_javascript_does_not_render_or_persist_response_data() -> None:
    script = TestClient(create_app()).get("/static/app.js").text

    for forbidden in (
        "innerHTML",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "eval(",
        "new Function",
        "console.",
    ):
        assert forbidden not in script
