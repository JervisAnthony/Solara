"""Versioned HTTP route for explicit public-alpha tester feedback."""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status

from solara_travel.presentation.api.feedback_schemas import (
    FeedbackAcceptedResponse,
    FeedbackRequestBody,
)
from solara_travel.presentation.api.observability import emit_event, request_id_from_request
from solara_travel.presentation.api.safeguards import ApiSafeguards
from solara_travel.presentation.api.schemas import ApiErrorResponse

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ApiErrorResponse,
            "description": "The process-local public-alpha feedback rate was exceeded.",
        }
    },
)
def accept_feedback(
    request: Request, request_body: FeedbackRequestBody
) -> FeedbackAcceptedResponse:
    """Record deliberately submitted tester feedback as a structured event."""

    safeguards: ApiSafeguards = request.app.state.api_safeguards
    rejection = safeguards.admit_feedback()
    if rejection is not None:
        emit_event(
            "feedback.rejected",
            request_id=request_id_from_request(request),
            code=rejection.code,
            stage="safeguard",
            retry_after_seconds=rejection.retry_after_seconds,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": rejection.code,
                "message": (
                    "This public preview is receiving too much feedback traffic. "
                    "Please try again shortly."
                ),
            },
            headers={"Retry-After": str(rejection.retry_after_seconds)},
        )

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
