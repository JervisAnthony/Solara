"""Versioned HTTP route for Solara's recommendation use case."""

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
    request_body: RecommendationRequestBody,
    dependencies: Annotated[ApiDependencies, Depends(_configured_dependencies)],
) -> RecommendationResponse:
    """Run deterministic recommendation and optional grounded narration."""

    try:
        domain_request = to_domain_recommendation_request(request_body)
    except (TypeError, ValueError) as exc:
        raise _api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_recommendation_request",
            str(exc),
        ) from exc

    recommendation_service = dependencies.recommendation_service
    assert recommendation_service is not None
    try:
        result = recommendation_service.recommend(domain_request)
    except ProviderAuthenticationError as exc:
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_authentication_failed",
            "Required travel data is temporarily unavailable or misconfigured.",
        ) from exc
    except ProviderRateLimitError as exc:
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_rate_limited",
            "An upstream travel provider is temporarily rate limited.",
        ) from exc
    except ProviderResponseError as exc:
        raise _api_error(
            status.HTTP_502_BAD_GATEWAY,
            "provider_invalid_response",
            "An upstream travel provider returned unusable data.",
        ) from exc
    except ProviderUnavailableError as exc:
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_unavailable",
            "Required travel data is temporarily unavailable.",
        ) from exc
    except ProviderError as exc:
        raise _api_error(
            status.HTTP_502_BAD_GATEWAY,
            "provider_error",
            "An upstream travel provider failed.",
        ) from exc

    narration = None
    if dependencies.narration_service is not None:
        narrated = dependencies.narration_service.narrate(result)
        result = narrated.recommendation_result
        narration = narrated.narration

    return recommendation_result_to_response(result, narration)


def _api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
