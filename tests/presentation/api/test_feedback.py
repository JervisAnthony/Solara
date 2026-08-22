"""HTTP tests for typed privacy-conscious tester feedback."""

import json
import logging
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from solara_travel.presentation.api import create_app
from solara_travel.presentation.api.observability import (
    OBSERVABILITY_LOGGER_NAME,
    REQUEST_ID_HEADER,
)


class FeedbackEventHandler(logging.Handler):
    """Collect structured feedback messages for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())

    def feedback_events(self) -> list[dict[str, object]]:
        return [
            event
            for event in map(json.loads, self.messages)
            if event["event"] == "feedback.accepted"
        ]


@pytest.fixture
def feedback_events() -> Iterator[FeedbackEventHandler]:
    logger = logging.getLogger(OBSERVABILITY_LOGGER_NAME)
    handler = FeedbackEventHandler()
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)


@pytest.mark.parametrize("rating", ["helpful", "mixed", "not_helpful"])
def test_feedback_accepts_each_rating_without_recommendation_service(
    rating: str, feedback_events: FeedbackEventHandler
) -> None:
    response = TestClient(create_app()).post(
        "/api/v1/feedback",
        json={"recommendation_request_id": None, "rating": rating, "comment": None},
    )

    assert response.status_code == 202
    assert set(response.json()) == {"status", "feedback_id"}
    assert response.json()["status"] == "accepted"
    assert str(UUID(response.json()["feedback_id"])) == response.json()["feedback_id"]
    assert str(UUID(response.headers[REQUEST_ID_HEADER])) == response.headers[REQUEST_ID_HEADER]
    event = feedback_events.feedback_events()[-1]
    assert event["feedback_id"] == response.json()["feedback_id"]
    assert event["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert event["recommendation_request_id"] is None
    assert event["rating"] == rating
    assert event["has_comment"] is False
    assert event["comment"] is None


def test_feedback_links_three_distinct_ids_and_does_not_echo_input(
    feedback_events: FeedbackEventHandler,
) -> None:
    recommendation_request_id = uuid4()
    response = TestClient(create_app()).post(
        "/api/v1/feedback",
        json={
            "recommendation_request_id": str(recommendation_request_id),
            "rating": "helpful",
            "comment": "The evidence view was clear.",
        },
    )

    event = feedback_events.feedback_events()[-1]
    feedback_id = response.json()["feedback_id"]
    request_id = response.headers[REQUEST_ID_HEADER]
    assert event["recommendation_request_id"] == str(recommendation_request_id)
    assert event["feedback_id"] == feedback_id
    assert event["request_id"] == request_id
    assert len({str(recommendation_request_id), feedback_id, request_id}) == 3
    assert response.json() == {"status": "accepted", "feedback_id": feedback_id}


def test_feedback_comment_is_trimmed_and_json_escaped_on_one_physical_line(
    feedback_events: FeedbackEventHandler,
) -> None:
    comment = '  A "clear" view.\nThe evidence helped.  '
    response = TestClient(create_app()).post(
        "/api/v1/feedback",
        json={"rating": "mixed", "comment": comment},
    )

    event = feedback_events.feedback_events()[-1]
    raw_event = next(
        message for message in feedback_events.messages if '"feedback.accepted"' in message
    )
    assert response.status_code == 202
    assert event["comment"] == 'A "clear" view.\nThe evidence helped.'
    assert event["has_comment"] is True
    assert "\\n" in raw_event
    assert "\n" not in raw_event
    assert json.loads(raw_event) == event


@pytest.mark.parametrize("comment", [None, "   ", "x" * 1000])
def test_feedback_accepts_optional_blank_and_boundary_comments(
    comment: str | None, feedback_events: FeedbackEventHandler
) -> None:
    response = TestClient(create_app()).post(
        "/api/v1/feedback", json={"rating": "not_helpful", "comment": comment}
    )

    assert response.status_code == 202
    event = feedback_events.feedback_events()[-1]
    expected = None if comment is None or not comment.strip() else comment
    assert event["comment"] == expected
    assert event["has_comment"] is (expected is not None)


@pytest.mark.parametrize(
    "payload",
    [
        {"rating": "great"},
        {"rating": "helpful", "recommendation_request_id": "not-a-uuid"},
        {"rating": "helpful", "comment": "x" * 1001},
        {"rating": "helpful", "unknown": True},
        {"rating": "helpful", "comment": 3},
    ],
)
def test_feedback_rejects_invalid_payloads_without_recording_them(
    payload: dict[str, object], feedback_events: FeedbackEventHandler
) -> None:
    response = TestClient(create_app()).post("/api/v1/feedback", json=payload)

    assert response.status_code == 422
    assert response.headers[REQUEST_ID_HEADER]
    assert feedback_events.feedback_events() == []


def test_feedback_events_contain_only_intended_explicit_fields(
    feedback_events: FeedbackEventHandler,
) -> None:
    response = TestClient(create_app()).post(
        "/api/v1/feedback",
        json={"rating": "helpful", "comment": "Benign explicit tester comment."},
        headers={"User-Agent": "private-agent", "Cookie": "private-cookie=value"},
    )

    assert response.status_code == 202
    event = feedback_events.feedback_events()[-1]
    assert set(event) == {
        "schema_version",
        "timestamp",
        "event",
        "feedback_id",
        "request_id",
        "recommendation_request_id",
        "rating",
        "has_comment",
        "comment",
    }
    serialized = json.dumps(event)
    for forbidden in (
        "private-agent",
        "private-cookie",
        "travel_period",
        "interests",
        "recommendations",
    ):
        assert forbidden not in serialized
