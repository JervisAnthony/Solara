"""Versioned HTTP route for explicit public-alpha tester feedback."""

from uuid import uuid4

from fastapi import APIRouter, Request, status

from solara_travel.presentation.api.feedback_schemas import (
    FeedbackAcceptedResponse,
    FeedbackRequestBody,
)
from solara_travel.presentation.api.observability import emit_event, request_id_from_request

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def accept_feedback(
    request: Request, request_body: FeedbackRequestBody
) -> FeedbackAcceptedResponse:
    """Record deliberately submitted tester feedback as a structured event."""

    feedback_id = uuid4()
    emit_event(
        "feedback.accepted",
        feedback_id=str(feedback_id),
        request_id=request_id_from_request(request),
        recommendation_request_id=(
            str(request_body.recommendation_request_id)
            if request_body.recommendation_request_id is not None
            else None
        ),
        rating=request_body.rating,
        has_comment=request_body.comment is not None,
        comment=request_body.comment,
    )
    return FeedbackAcceptedResponse(status="accepted", feedback_id=feedback_id)
