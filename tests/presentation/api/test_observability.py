"""Tests for privacy-conscious structured events and request tracing."""

import asyncio
import json
import logging
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from solara_travel.application import RecommendationNarrationService
from solara_travel.domain import TemperatureComfortRange
from solara_travel.ports import ProviderUnavailableError
from solara_travel.presentation.api import ApiDependencies, create_app
from solara_travel.presentation.api.observability import (
    OBSERVABILITY_LOGGER_NAME,
    REQUEST_ID_HEADER,
    RequestTracingMiddleware,
    configure_structured_logging,
    elapsed_milliseconds,
    request_id_from_request,
)
from solara_travel.workflows import build_offline_recommendation_service


class EventHandler(logging.Handler):
    """Collect serialized product events without an external backend."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())

    def events(self, event: str | None = None) -> list[dict[str, object]]:
        parsed = [json.loads(message) for message in self.messages]
        return [item for item in parsed if event is None or item["event"] == event]


@pytest.fixture
def event_handler() -> Iterator[EventHandler]:
    logger = logging.getLogger(OBSERVABILITY_LOGGER_NAME)
    handler = EventHandler()
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)


def _payload() -> dict[str, object]:
    return {
        "travel_period": {"start_date": "2026-04-10", "end_date": "2026-04-12"},
        "preferences": {
            "interests": ["Recognizable private interest"],
            "preferred_pace": "Recognizable private pace",
            "preferred_climate": "Recognizable private climate",
        },
        "destination": None,
    }


def _offline_dependencies(
    narration_service: RecommendationNarrationService | None = None,
) -> ApiDependencies:
    service = build_offline_recommendation_service(
        comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0)
    )
    return ApiDependencies(service, narration_service)


class NarrationProvider:
    """Return one fixed narration or let the narration service suppress failure."""

    def __init__(self, outcome: str | BaseException) -> None:
        self.outcome = outcome

    def generate(self, prompt: object) -> str:
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def test_handled_responses_receive_distinct_server_owned_uuid_request_ids() -> None:
    client = TestClient(create_app())

    health = client.get("/health")
    web = client.get("/")
    unavailable = client.post(
        "/api/v1/recommendations",
        json=_payload(),
        headers={REQUEST_ID_HEADER: "attacker-controlled"},
    )

    ids = {
        health.headers[REQUEST_ID_HEADER],
        web.headers[REQUEST_ID_HEADER],
        unavailable.headers[REQUEST_ID_HEADER],
    }
    assert len(ids) == 3
    assert unavailable.status_code == 503
    assert "attacker-controlled" not in ids
    assert all(str(UUID(value)) == value for value in ids)


def test_completed_event_matches_header_and_excludes_private_request_metadata(
    event_handler: EventHandler,
) -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/recommendations?private-query=recognizable",
        json=_payload(),
        headers={
            "User-Agent": "recognizable-private-agent",
            "Cookie": "recognizable-private-cookie=value",
        },
    )

    completed = event_handler.events("http.request.completed")[-1]
    assert completed == {
        "schema_version": 1,
        "timestamp": completed["timestamp"],
        "event": "http.request.completed",
        "request_id": response.headers[REQUEST_ID_HEADER],
        "method": "POST",
        "path": "/api/v1/recommendations",
        "status_code": 503,
        "duration_ms": completed["duration_ms"],
    }
    assert str(completed["timestamp"]).endswith("Z")
    assert isinstance(completed["duration_ms"], (int, float))
    assert completed["duration_ms"] >= 0
    serialized = json.dumps(event_handler.events())
    for private_value in (
        "recognizable",
        "Recognizable private interest",
        "Recognizable private pace",
        "Recognizable private climate",
        "recognizable-private-agent",
        "recognizable-private-cookie",
    ):
        assert private_value not in serialized


def test_health_and_static_receive_headers_without_request_event_noise(
    event_handler: EventHandler,
) -> None:
    client = TestClient(create_app())

    health = client.get("/health")
    static = client.get("/static/app.js")

    assert health.headers[REQUEST_ID_HEADER]
    assert static.headers[REQUEST_ID_HEADER]
    assert event_handler.events("http.request.completed") == []


def test_unhandled_exception_is_logged_safely_and_reraised(event_handler: EventHandler) -> None:
    application = create_app()

    @application.get("/test-only-programming-defect")
    def programming_defect() -> None:
        raise RuntimeError("recognizable raw programming detail")

    with pytest.raises(RuntimeError, match="recognizable raw programming detail"):
        TestClient(application).get("/test-only-programming-defect")

    exception_event = event_handler.events("http.request.exception")[-1]
    assert exception_event["method"] == "GET"
    assert exception_event["path"] == "/test-only-programming-defect"
    assert exception_event["error_kind"] == "unhandled"
    assert "recognizable raw programming detail" not in event_handler.messages[-1]


def test_configured_logger_is_idempotent_and_respects_host_handlers() -> None:
    logger = logging.getLogger(OBSERVABILITY_LOGGER_NAME)
    original_handlers = list(logger.handlers)
    host_handler = EventHandler()
    try:
        logger.handlers.clear()
        first = configure_structured_logging()
        assert len(first.handlers) == 1
        first_handler = first.handlers[0]
        assert configure_structured_logging().handlers == [first_handler]

        logger.handlers[:] = [host_handler]
        assert configure_structured_logging().handlers == [host_handler]
        assert logger.propagate is False
    finally:
        logger.handlers[:] = original_handlers


def test_elapsed_duration_never_becomes_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("solara_travel.presentation.api.observability.perf_counter", lambda: 1.0)

    assert elapsed_milliseconds(2.0) == 0.0


def test_request_id_helper_reads_middleware_state() -> None:
    request = Request({"type": "http", "state": {"request_id": "server-id"}})

    assert request_id_from_request(request) == "server-id"


def test_middleware_passes_through_non_http_scopes() -> None:
    calls: list[str] = []

    async def app(scope: object, receive: object, send: object) -> None:
        calls.append(scope["type"])  # type: ignore[index]

    async def receive() -> dict[str, object]:
        return {}

    async def send(message: object) -> None:
        raise AssertionError(message)

    middleware = RequestTracingMiddleware(app)
    asyncio.run(middleware({"type": "lifespan"}, receive, send))  # type: ignore[arg-type]

    assert calls == ["lifespan"]


def test_middleware_tolerates_an_http_app_that_sends_no_response(
    event_handler: EventHandler,
) -> None:
    async def app(scope: object, receive: object, send: object) -> None:
        return None

    async def receive() -> dict[str, object]:
        return {}

    async def send(message: object) -> None:
        raise AssertionError(message)

    scope = {"type": "http", "method": "GET", "path": "/no-response"}
    asyncio.run(RequestTracingMiddleware(app)(scope, receive, send))  # type: ignore[arg-type]

    assert UUID(scope["state"]["request_id"])  # type: ignore[index]
    assert event_handler.events() == []


def test_static_exception_is_reraised_without_noisy_request_event(
    event_handler: EventHandler,
) -> None:
    async def app(scope: object, receive: object, send: object) -> None:
        raise RuntimeError("static failure")

    async def receive() -> dict[str, object]:
        return {}

    async def send(message: object) -> None:
        raise AssertionError(message)

    scope = {"type": "http", "method": "GET", "path": "/static/broken.js"}
    with pytest.raises(RuntimeError, match="static failure"):
        asyncio.run(RequestTracingMiddleware(app)(scope, receive, send))  # type: ignore[arg-type]

    assert event_handler.events() == []


def test_recommendation_success_events_include_safe_stage_timings(
    event_handler: EventHandler,
) -> None:
    response = TestClient(create_app(dependencies=_offline_dependencies())).post(
        "/api/v1/recommendations", json=_payload()
    )

    completed = event_handler.events("recommendation.completed")[-1]
    assert response.status_code == 200
    assert completed["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert completed["recommendation_count"] == 3
    assert completed["has_narration"] is False
    assert completed["narration_attempted"] is False
    assert completed["narration_duration_ms"] is None
    assert completed["recommendation_duration_ms"] >= 0
    serialized = event_handler.messages[-2]
    assert "Sunspire Bay" not in serialized
    assert "Recognizable private interest" not in serialized


@pytest.mark.parametrize(
    ("outcome", "has_narration"),
    [
        ("Fixed narration", True),
        (ProviderUnavailableError("private narration failure"), False),
    ],
)
def test_recommendation_narration_timing_covers_success_and_suppressed_failure(
    outcome: str | BaseException,
    has_narration: bool,
    event_handler: EventHandler,
) -> None:
    narration_service = RecommendationNarrationService(NarrationProvider(outcome))
    response = TestClient(create_app(dependencies=_offline_dependencies(narration_service))).post(
        "/api/v1/recommendations", json=_payload()
    )

    completed = event_handler.events("recommendation.completed")[-1]
    assert response.status_code == 200
    assert completed["has_narration"] is has_narration
    assert completed["narration_attempted"] is True
    assert completed["narration_duration_ms"] >= 0
    assert "private narration failure" not in json.dumps(completed)
