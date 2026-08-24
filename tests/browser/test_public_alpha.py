"""Deterministic Chromium smoke tests for the local public-alpha experience."""

from __future__ import annotations

import socket
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from threading import Thread
from urllib.request import urlopen

import pytest
import uvicorn

from solara_travel.application import RecommendationNarrationService, RecommendationService
from solara_travel.domain import (
    Attraction,
    Destination,
    DestinationQuery,
    GeoCoordinates,
    RecommendationRequest,
    TemperatureComfortRange,
    TravelPeriod,
    WeatherObservation,
)
from solara_travel.ports import NarrationPrompt, ProviderUnavailableError
from solara_travel.presentation.api import ApiDependencies, create_app

playwright = pytest.importorskip("playwright.sync_api")


def _destination(name: str, country: str, latitude: float, longitude: float) -> Destination:
    return Destination(name, country, GeoCoordinates(latitude, longitude))


@dataclass
class BrowserPlacesProvider:
    destinations: tuple[Destination, ...]
    resolution_requests: list[DestinationQuery] = field(default_factory=list)

    def discover_destinations(self, request: RecommendationRequest) -> tuple[Destination, ...]:
        return self.destinations

    def resolve_destination(self, query: DestinationQuery) -> Destination | None:
        self.resolution_requests.append(query)
        if query.value == "Slowtown":
            time.sleep(10.5)
            return self.destinations[0]
        normalized = query.value.split(",", 1)[0].strip().casefold()
        if normalized == "markdownville":
            return self.destinations[0]
        return next(
            (
                destination
                for destination in self.destinations
                if destination.name.casefold() == normalized
            ),
            None,
        )

    def discover_attractions(self, destination: Destination) -> tuple[Attraction, ...]:
        return tuple(
            Attraction(
                f"{destination.name} attraction {index}",
                "landmark",
                destination.coordinates,
            )
            for index in range(1, 9)
        )


@dataclass(frozen=True)
class BrowserNarrationProvider:
    def generate(self, prompt: NarrationPrompt) -> str:
        if "Markdownville" not in prompt.input_text:
            raise ProviderUnavailableError("deterministic narration fallback")
        return "## Overall\n\n**Seasonal fit**\n\n### Rankings\n\n`Budapest`"


@dataclass(frozen=True)
class BrowserWeatherProvider:
    temperatures: dict[Destination, float]

    def get_historical_weather(
        self, destination: Destination, period: TravelPeriod
    ) -> tuple[WeatherObservation, ...]:
        temperature = self.temperatures[destination]
        return tuple(
            WeatherObservation(date(year, 4, day), temperature, 55.0, 1.0)
            for year in range(2020, 2025)
            for day in range(10, 13)
        )


@pytest.fixture(scope="module")
def local_public_alpha() -> Iterator[tuple[str, BrowserPlacesProvider]]:
    destinations = (
        _destination("Budapest", "Hungary", 47.4979, 19.0402),
        _destination("Vienna", "Austria", 48.2082, 16.3738),
        _destination("Prague", "Czechia", 50.0755, 14.4378),
    )
    places = BrowserPlacesProvider(destinations)
    service = RecommendationService(
        places,
        BrowserWeatherProvider(
            {destinations[0]: 31.0, destinations[1]: 22.0, destinations[2]: 26.0}
        ),
        TravelPeriod(date(2020, 1, 1), date(2024, 12, 31)),
        TemperatureComfortRange(18.0, 28.0, 10.0),
    )
    application = create_app(
        dependencies=ApiDependencies(
            service,
            RecommendationNarrationService(BrowserNarrationProvider()),
        )
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(application, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            with urlopen(f"{base_url}/health", timeout=0.2) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.05)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.fail("local Solara browser server did not start")
    try:
        yield base_url, places
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def chromium_browser() -> Iterator[object]:
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(chromium_browser: object) -> Iterator[object]:
    context = chromium_browser.new_context(viewport={"width": 1440, "height": 1000})
    browser_page = context.new_page()
    failures: list[str] = []
    browser_page.on(
        "console",
        lambda message: (
            failures.append(f"console: {message.text}")
            if message.type == "error" and not message.text.startswith("Failed to load resource:")
            else None
        ),
    )

    def handle_dialog(dialog: object) -> None:
        failures.append(f"dialog: {dialog}")
        dialog.dismiss()

    browser_page.on("dialog", handle_dialog)
    browser_page.on("pageerror", lambda error: failures.append(f"pageerror: {error}"))
    browser_page.on(
        "requestfailed",
        lambda request: failures.append(f"requestfailed: {request.url}"),
    )
    browser_page.on(
        "response",
        lambda response: (
            failures.append(f"asset {response.status}: {response.url}")
            if "/static/" in response.url and response.status >= 400
            else None
        ),
    )
    yield browser_page
    context.close()
    assert failures == []


def _open(page: object, base_url: str) -> None:
    page.goto(base_url, wait_until="networkidle")


def _fill_dates(page: object) -> None:
    page.locator("#travel-start-date").fill("2027-04-10")
    page.locator("#travel-end-date").fill("2027-04-12")


def _add(page: object, query: str) -> None:
    page.locator("#destination-input").fill(query)
    page.locator("#destination-add").click()


def _synthetic_response(scores: list[float]) -> dict[str, object]:
    recommendations = []
    for rank, score in enumerate(scores, start=1):
        recommendations.append(
            {
                "rank": rank,
                "destination": {"name": f"City {rank}", "country": "Example"},
                "score": score,
                "components": [
                    {
                        "name": "seasonal_temperature_comfort",
                        "score": score,
                        "weight": 1.0,
                        "weighted_contribution": score,
                    }
                ],
                "evidence": {
                    "attractions": [],
                    "seasonal_weather": {
                        "target_period": {
                            "start_date": "2027-04-10",
                            "end_date": "2027-04-12",
                        },
                        "historical_years": [2020],
                        "historical_year_count": 1,
                        "observation_count": 3,
                        "mean_temperature_celsius": 22.1234,
                        "minimum_temperature_celsius": 20.9876,
                        "maximum_temperature_celsius": 23.4567,
                        "mean_relative_humidity_percent": 55.555,
                        "mean_daily_precipitation_mm": 1.2345,
                    },
                    "temperature_comfort": {
                        "score": score,
                        "comfort_range": {
                            "minimum_celsius": 18.0,
                            "maximum_celsius": 28.0,
                            "tolerance_celsius": 10.0,
                        },
                        "within_preferred_fraction": score,
                        "mean_deviation_celsius": 1.234,
                    },
                },
            }
        )
    return {
        "request": {
            "destination_mode": "discovery",
            "destination_queries": [],
            "travel_period": {"start_date": "2027-04-10", "end_date": "2027-04-12"},
        },
        "recommendation_count": len(recommendations),
        "has_recommendations": True,
        "recommendations": recommendations,
        "has_narration": False,
        "narration": None,
    }


def test_editorial_homepage_is_travel_led_before_any_request(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    recommendation_requests: list[object] = []
    page.on(
        "request",
        lambda request: (
            recommendation_requests.append(request)
            if request.url.endswith("/recommendations")
            else None
        ),
    )

    _open(page, base_url)

    assert page.get_by_role("navigation", name="Primary navigation").is_visible()
    assert page.get_by_role("heading", name="Popular escapes").is_visible()
    assert page.locator(".escape-card").count() == 6
    hero_image = page.locator(".hero-travel-image")
    assert hero_image.is_visible()
    assert hero_image.evaluate("image => image.complete && image.naturalWidth === 1280")
    assert hero_image.get_attribute("src") == "/static/travel/cape-town.webp"
    assert recommendation_requests == []

    page.get_by_role("link", name="Start planning", exact=False).click()
    page.wait_for_function(
        "document.querySelector('#recommendation-workspace').getBoundingClientRect().top "
        "< window.innerHeight"
    )
    assert page.locator("#recommendation-workspace").evaluate(
        "element => element.getBoundingClientRect().top < window.innerHeight"
    )
    page.get_by_role("link", name="See how it works").click()
    page.wait_for_function(
        "document.querySelector('#how-it-works').getBoundingClientRect().top < window.innerHeight"
    )
    assert page.locator("#how-it-works").evaluate(
        "element => element.getBoundingClientRect().top < window.innerHeight"
    )


def test_popular_escapes_carousel_has_manual_native_scrolling(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    track = page.locator("#popular-escapes-track")

    assert (
        track.evaluate("element => getComputedStyle(element).scrollSnapType") == "inline mandatory"
    )
    assert track.evaluate("element => element.scrollLeft") == 0
    page.get_by_role("button", name="Next popular escapes").click()
    page.wait_for_function(
        "element => element.scrollLeft > 0",
        arg=track.element_handle(),
    )
    page.wait_for_timeout(500)
    moved = track.evaluate("element => element.scrollLeft")
    page.wait_for_timeout(500)
    assert track.evaluate("element => element.scrollLeft") == pytest.approx(moved, abs=1)
    page.get_by_role("button", name="Previous popular escapes").click()
    page.wait_for_timeout(500)
    assert track.evaluate("element => element.scrollLeft") < moved


def test_escape_prefill_reuses_destination_state_without_request(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    recommendation_requests: list[object] = []
    page.on(
        "request",
        lambda request: (
            recommendation_requests.append(request)
            if request.url.endswith("/recommendations")
            else None
        ),
    )
    _open(page, base_url)
    actions = page.get_by_role("button", name="Plan this escape")

    actions.nth(0).click()
    assert page.locator(".destination-chip").all_inner_texts()[0].startswith("Budapest, Hungary")
    assert page.locator("#recommendation-submit").inner_text() == "EXPLORE BUDAPEST →"
    assert page.locator("#destination-input").evaluate(
        "element => element === document.activeElement"
    )
    assert recommendation_requests == []

    actions.nth(0).click()
    assert page.locator(".destination-chip").count() == 1
    assert "already included" in page.locator("#destination-error").inner_text()

    for index in range(1, 5):
        actions.nth(index).click()
    assert page.locator(".destination-chip").count() == 5
    actions.nth(5).click()
    assert page.locator(".destination-chip").count() == 5
    assert "up to five" in page.locator("#destination-error").inner_text()
    assert recommendation_requests == []


def test_discovery_mode_submits_and_renders_fake_ranked_results(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    assert page.locator("#recommendation-submit").inner_text() == "FIND DESTINATIONS →"

    page.locator("#recommendation-submit").click()

    page.locator(".recommendation-card").first.wait_for()
    assert page.locator(".recommendation-card").count() == 3
    assert page.locator("#results-title").inner_text() == "Recommended destinations"


def test_score_percentage_and_evidence_number_formatting(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    response = _synthetic_response([1.0, 0.99825, 0.7495, 0.6815, 0.0])

    page.evaluate(
        """response => document.querySelector('#recommendation-form').dispatchEvent(
          new CustomEvent('solara:recommendation-ready', {detail: response})
        )""",
        response,
    )

    assert page.locator(".suitability-score .metric-value").all_inner_texts() == [
        "100%",
        "99.8%",
        "75%",
        "68.2%",
        "0%",
    ]
    page.locator(".recommendation-card").first.locator(".evidence-summary").click()
    evidence = page.locator(".recommendation-card").first.locator(".evidence-content")
    assert "22.1 °C" in evidence.inner_text()
    assert "21 °C — 23.5 °C" in evidence.inner_text()
    assert "55.6%" in evidence.inner_text()
    assert "1.23 mm" in evidence.inner_text()


def test_single_destination_chip_cta_request_and_result(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    _add(page, "Budapest, Hungary")
    assert page.locator(".destination-chip").inner_text().startswith("Budapest, Hungary")
    assert page.locator("#recommendation-submit").inner_text() == "EXPLORE BUDAPEST →"

    with page.expect_request(lambda request: request.url.endswith("/recommendations")) as sent:
        page.locator("#recommendation-submit").click()

    assert sent.value.post_data_json["destination_queries"] == ["Budapest, Hungary"]
    page.locator(".recommendation-card").wait_for()
    assert page.locator("#results-title").inner_text() == "Budapest for your trip"


def test_comparison_ranks_once_and_remove_updates_mode(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    _add(page, "Budapest, Hungary")
    _add(page, "Vienna, Austria")
    assert page.locator("#recommendation-submit").inner_text() == "COMPARE DESTINATIONS →"

    page.locator("#recommendation-submit").click()
    page.locator(".recommendation-card").first.wait_for()
    assert page.locator(".destination-name").all_inner_texts() == ["Vienna", "Budapest"]
    assert page.locator("#results-title").inner_text() == "Your destination comparison"

    remove = page.get_by_role("button", name="Remove Vienna, Austria")
    remove.focus()
    remove.press("Enter")
    assert page.locator("#recommendation-submit").inner_text() == "EXPLORE BUDAPEST →"


def test_pending_destination_submits_once_without_add(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    page.locator("#destination-input").fill("Budapest, Hungary")
    requests: list[object] = []
    page.on(
        "request",
        lambda request: (
            requests.append(request) if request.url.endswith("/recommendations") else None
        ),
    )

    page.locator("#recommendation-submit").click()
    page.locator(".recommendation-card").wait_for()

    assert len(requests) == 1
    assert requests[0].post_data_json["destination_queries"] == ["Budapest, Hungary"]
    assert page.locator(".destination-chip").count() == 1


def test_duplicate_and_max_five_validation_are_visible(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _add(page, "Budapest")
    _add(page, "BUDAPEST")
    assert "already included" in page.locator("#destination-error").inner_text()
    for query in ("Vienna", "Prague", "Rome", "Paris"):
        _add(page, query)
    _add(page, "Lisbon")
    assert page.locator(".destination-chip").count() == 5
    assert "up to five" in page.locator("#destination-error").inner_text()


@pytest.mark.parametrize(
    ("status", "code", "title"),
    [
        (429, "recommendation_rate_limited", "Solara is taking a short pause"),
        (503, "provider_unavailable", "Travel data is temporarily unavailable"),
    ],
)
def test_server_failures_preserve_destination_state(
    page: object,
    local_public_alpha: tuple[str, BrowserPlacesProvider],
    status: int,
    code: str,
    title: str,
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    _add(page, "Budapest")
    page.route(
        "**/api/v1/recommendations",
        lambda route: route.fulfill(
            status=status,
            headers={"Retry-After": "1"} if status == 429 else {},
            json={"detail": {"code": code, "message": "not browser-visible"}},
        ),
    )

    page.locator("#recommendation-submit").click()

    page.locator("#recommendation-request-error").wait_for()
    assert page.locator("#recommendation-request-error-title").inner_text() == title
    assert page.locator(".destination-chip").count() == 1


def test_destination_not_found_identifies_city_contract_and_preserves_form(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    page.locator("#interests").fill("history")
    page.locator("#preferred-pace").fill("balanced")
    _add(page, "Budapest")
    _add(page, "Morocco")

    page.locator("#recommendation-submit").click()

    page.locator("#recommendation-request-error").wait_for()
    assert (
        page.locator("#recommendation-request-error-title").inner_text() == "Destination not found"
    )
    message = page.locator("#recommendation-request-error-message").inner_text()
    assert 'couldn\'t resolve "Morocco" as a city or locality' in message
    assert "Budapest, Hungary" in message
    assert page.locator(".destination-chip").count() == 2
    assert page.locator("#travel-start-date").input_value() == "2027-04-10"
    assert page.locator("#travel-end-date").input_value() == "2027-04-12"
    assert page.locator("#interests").input_value() == "history"
    assert page.locator("#preferred-pace").input_value() == "balanced"


def test_hostile_destination_is_rendered_only_as_text(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    hostile = "<svg onload=alert(1)>"
    _add(page, hostile)

    page.locator("#recommendation-submit").click()

    message = page.locator("#recommendation-request-error-message")
    message.wait_for()
    assert hostile in message.inner_text()
    assert message.locator("svg").count() == 0


def test_markdown_narration_is_clean_plain_text(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    _add(page, "Markdownville")

    page.locator("#recommendation-submit").click()

    narration = page.locator("#recommendation-narration-text")
    narration.wait_for()
    assert narration.inner_text() == "Overall\n\nSeasonal fit\n\nRankings\n\nBudapest"
    assert narration.locator("*").count() == 0


def test_seasonal_fit_cards_are_compact_and_attractions_expand_independently(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    requests: list[object] = []
    page.on(
        "request",
        lambda request: (
            requests.append(request) if request.url.endswith("/recommendations") else None
        ),
    )

    page.locator("#recommendation-submit").click()
    page.locator(".recommendation-card").first.wait_for()

    cards = page.locator(".recommendation-card")
    assert cards.count() == 3
    assert cards.locator(".suitability-score .metric-label").all_inner_texts() == [
        "SEASONAL FIT",
        "SEASONAL FIT",
        "SEASONAL FIT",
    ]
    traveller_text = "\n".join(cards.all_inner_texts())
    assert "WEIGHT" not in traveller_text
    assert "WEIGHTED CONTRIBUTION" not in traveller_text
    assert "SUITABILITY SCORE" not in traveller_text
    assert cards.locator(".suitability-score .metric-value").all_inner_texts() == [
        "100%",
        "100%",
        "70%",
    ]
    component = cards.first.locator(".component-section").bounding_box()
    evidence = cards.first.locator(".evidence-summary").bounding_box()
    assert component is not None and evidence is not None
    assert evidence["y"] - (component["y"] + component["height"]) < 2

    assert cards.locator(".attraction-toggle").count() == 3
    cards.nth(0).locator(".evidence-summary").click()
    cards.nth(1).locator(".evidence-summary").click()
    toggles = cards.get_by_role("button", name="Show all attractions")
    assert toggles.count() == 2
    assert cards.nth(0).locator(".attraction-list li:visible").count() == 6
    assert cards.nth(1).locator(".attraction-list li:visible").count() == 6
    toggles.nth(0).focus()
    toggles.nth(0).press("Enter")
    assert cards.nth(0).locator(".attraction-list li:visible").count() == 8
    assert cards.nth(1).locator(".attraction-list li:visible").count() == 6
    assert cards.nth(0).get_by_role("button", name="Show fewer attractions").is_visible()
    cards.nth(0).get_by_role("button", name="Show fewer attractions").press("Enter")
    assert cards.nth(0).locator(".attraction-list li:visible").count() == 6
    assert len(requests) == 1


def test_cold_start_message_and_repeated_submit_protection(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, places = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    _add(page, "Slowtown")
    before = len(places.resolution_requests)

    page.locator("#recommendation-submit").click()
    assert page.locator("#recommendation-submit").is_disabled()
    page.locator("#recommendation-form").press("Enter")
    page.get_by_text("Solara may be waking up", exact=False).wait_for(timeout=11000)
    page.locator(".recommendation-card").wait_for(timeout=15000)

    assert len(places.resolution_requests) == before + 1


def test_narration_fallback_and_feedback_remain_usable(
    page: object, local_public_alpha: tuple[str, BrowserPlacesProvider]
) -> None:
    base_url, _ = local_public_alpha
    _open(page, base_url)
    _fill_dates(page)
    page.locator("#recommendation-submit").click()
    page.locator(".recommendation-card").first.wait_for()
    assert page.locator("#recommendation-narration").is_hidden()

    page.get_by_role("radio", name="Helpful", exact=True).check()
    page.locator("#feedback-submit").click()
    page.get_by_text("Thanks — your feedback was received.").wait_for()

    page.route(
        "**/api/v1/feedback",
        lambda route: route.fulfill(
            status=429,
            headers={"Retry-After": "1"},
            json={"detail": {"code": "feedback_rate_limited", "message": "safe"}},
        ),
    )
    page.get_by_role("radio", name="Mixed", exact=True).check()
    page.locator("#feedback-comment").fill("Keep this feedback")
    page.locator("#feedback-submit").click()
    page.get_by_text("Solara is receiving a lot of feedback", exact=False).wait_for()
    assert page.locator("#feedback-comment").input_value() == "Keep this feedback"


@pytest.mark.parametrize("width", [1440, 1024, 768, 390])
def test_responsive_destination_and_results_smoke(
    page: object,
    local_public_alpha: tuple[str, BrowserPlacesProvider],
    width: int,
) -> None:
    base_url, _ = local_public_alpha
    page.set_viewport_size({"width": width, "height": 900})
    _open(page, base_url)
    _fill_dates(page)
    _add(page, "A very long destination name designed to wrap safely, Example Country")
    assert page.get_by_role(
        "button",
        name="Remove A very long destination name designed to wrap safely, Example Country",
    ).is_visible()

    overflowing = page.locator("*").evaluate_all(
        """elements => elements
          .filter(element => !element.closest('[aria-hidden="true"]'))
          .filter(element => !element.closest('#popular-escapes-track'))
          .filter(element => element.getBoundingClientRect().right > window.innerWidth + 1)
          .map(element => ({tag: element.tagName, id: element.id, className: element.className,
                            right: element.getBoundingClientRect().right}))"""
    )
    assert overflowing == []
    page.evaluate("window.scrollTo(9999, 0)")
    assert page.evaluate("window.scrollX") == 0
