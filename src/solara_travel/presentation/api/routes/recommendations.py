"""Versioned HTTP route for Solara's recommendation use case."""

from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from solara_travel.ports import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.presentation.api.dependencies import ApiDependencies
from solara_travel.presentation.api.observability import (
    elapsed_milliseconds,
    emit_event,
    request_id_from_request,
)
from solara_travel.presentation.api.recommendation_mapping import (
    recommendation_result_to_response,
    to_domain_recommendation_request,
)
from solara_travel.presentation.api.recommendation_schemas import (
    RecommendationRequestBody,
    RecommendationResponse,
)
from solara_travel.presentation.api.schemas import ApiErrorResponse

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


def _configured_dependencies(request: Request) -> ApiDependencies:
    dependencies: ApiDependencies = request.app.state.api_dependencies
    if dependencies.recommendation_service is None:
        emit_event(
            "recommendation.rejected",
            request_id=request_id_from_request(request),
            code="recommendation_service_unconfigured",
            stage="configuration",
        )
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "recommendation_service_unconfigured",
            "Recommendation service is not configured.",
        )
    return dependencies


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_502_BAD_GATEWAY: {
            "model": ApiErrorResponse,
            "description": "An upstream provider returned unusable data.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ApiErrorResponse,
            "description": "A required service or upstream provider is unavailable.",
        },
    },
)
def recommend(
    request: Request,
    request_body: RecommendationRequestBody,
    dependencies: Annotated[ApiDependencies, Depends(_configured_dependencies)],
) -> RecommendationResponse:
    """Run deterministic recommendation and optional grounded narration."""

    try:
        domain_request = to_domain_recommendation_request(request_body)
    except (TypeError, ValueError) as exc:
        emit_event(
            "recommendation.rejected",
            request_id=request_id_from_request(request),
            code="invalid_recommendation_request",
            stage="validation",
        )
        raise _api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_recommendation_request",
            str(exc),
        ) from exc

    recommendation_service = dependencies.recommendation_service
    assert recommendation_service is not None
    recommendation_started_at = perf_counter()
    try:
        result = recommendation_service.recommend(domain_request)
    except ProviderAuthenticationError as exc:
        _emit_recommendation_failure(
            request, "provider_authentication_failed", recommendation_started_at
        )
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_authentication_failed",
            "Required travel data is temporarily unavailable or misconfigured.",
        ) from exc
    except ProviderRateLimitError as exc:
        _emit_recommendation_failure(request, "provider_rate_limited", recommendation_started_at)
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_rate_limited",
            "An upstream travel provider is temporarily rate limited.",
        ) from exc
    except ProviderResponseError as exc:
        _emit_recommendation_failure(
            request, "provider_invalid_response", recommendation_started_at
        )
        raise _api_error(
            status.HTTP_502_BAD_GATEWAY,
            "provider_invalid_response",
            "An upstream travel provider returned unusable data.",
        ) from exc
    except ProviderUnavailableError as exc:
        _emit_recommendation_failure(request, "provider_unavailable", recommendation_started_at)
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_unavailable",
            "Required travel data is temporarily unavailable.",
        ) from exc
    except ProviderError as exc:
        _emit_recommendation_failure(request, "provider_error", recommendation_started_at)
        raise _api_error(
            status.HTTP_502_BAD_GATEWAY,
            "provider_error",
            "An upstream travel provider failed.",
        ) from exc

    recommendation_duration_ms = elapsed_milliseconds(recommendation_started_at)
    narration = None
    narration_duration_ms = None
    narration_attempted = dependencies.narration_service is not None
    if dependencies.narration_service is not None:
        narration_started_at = perf_counter()
        narrated = dependencies.narration_service.narrate(result)
        narration_duration_ms = elapsed_milliseconds(narration_started_at)
        result = narrated.recommendation_result
        narration = narrated.narration

    response = recommendation_result_to_response(result, narration)
    emit_event(
        "recommendation.completed",
        request_id=request_id_from_request(request),
        recommendation_count=response.recommendation_count,
        has_narration=response.has_narration,
        recommendation_duration_ms=recommendation_duration_ms,
        narration_duration_ms=narration_duration_ms,
        narration_attempted=narration_attempted,
    )
    return response


def _emit_recommendation_failure(request: Request, code: str, started_at: float) -> None:
    emit_event(
        "recommendation.failed",
        request_id=request_id_from_request(request),
        code=code,
        stage="recommendation",
        duration_ms=elapsed_milliseconds(started_at),
    )


def _api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
