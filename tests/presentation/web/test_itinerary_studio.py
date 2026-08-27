"""Static accessibility, privacy, and product contracts for Itinerary Studio."""

from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app


def _asset(path: str) -> str:
    response = TestClient(create_app()).get(path)
    assert response.status_code == 200
    return response.text


def test_itinerary_studio_markup_exposes_guided_semantic_controls() -> None:
    html = _asset("/")
    for marker in (
        '<script src="/static/itinerary.js" defer></script>',
        'id="itinerary-studio"',
        'id="party-presets"',
        'data-pace="relaxed"',
        'data-pace="balanced"',
        'data-pace="active"',
        'data-requirement="wheelchair_access"',
        'data-requirement="reduced_walking"',
        'id="destination-route"',
        'id="itinerary-days"',
        'id="activity-options"',
        'aria-live="polite"',
    ):
        assert marker in html


def test_itinerary_script_owns_required_operations_and_truthful_language() -> None:
    script = _asset("/static/itinerary.js")
    for marker in (
        'const PERIODS = ["morning", "afternoon", "evening"]',
        "function updateAllocation",
        "function moveDestination",
        "function removeDestination",
        "function renderTravelLeg",
        "function assessment",
        "function addActivity",
        "function removeActivity",
        "function replaceActivity",
        "function moveActivity",
        "function reorderActivity",
        "category heuristic",
        "Accessibility information unavailable",
        "Travel duration is unknown",
        "prefers-reduced-motion: reduce",
    ):
        assert marker in script
    for forbidden in (
        "price",
        "checkout",
        "cart",
        "analytics",
        "geolocation",
        "localStorage",
        "sessionStorage",
        "innerHTML",
        "eval(",
        "http://",
        "https://",
    ):
        assert forbidden not in script


def test_itinerary_styles_are_responsive_and_reduced_motion_aware() -> None:
    styles = _asset("/static/styles.css")
    for marker in (
        ".itinerary-studio",
        ".studio-grid",
        ".route-card",
        ".travel-leg",
        ".day-periods",
        ".feasibility-fill",
        ".activity-option-card",
        "@media (max-width: 980px)",
        "@media (max-width: 720px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert marker in styles
