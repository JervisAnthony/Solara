"""Versioned HTTP route for Solara's recommendation use case."""

from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from solara_travel.application import (
    BroadScopeCombinationError,
    DestinationDiscoveryUnavailableError,
    DestinationNotFoundError,
)
from solara_travel.domain import RecommendationRequest
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
from solara_travel.presentation.api.safeguards import (
    ApiSafeguards,
    RecommendationLease,
    SafeguardRejection,
    SuggestionLease,
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
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ApiErrorResponse,
            "description": "The request is invalid or an explicit destination was not found.",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ApiErrorResponse,
            "description": "A process-local public-alpha safeguard rejected the request.",
        },
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

    safeguards: ApiSafeguards = request.app.state.api_safeguards
    admission = safeguards.admit_recommendation()
    if isinstance(admission, SafeguardRejection):
        _reject_for_safeguard(request, admission)
    assert isinstance(admission, RecommendationLease)

    with admission:
        return _run_recommendation(request, domain_request, dependencies, safeguards)


def _run_recommendation(
    request: Request,
    domain_request: RecommendationRequest,
    dependencies: ApiDependencies,
    safeguards: ApiSafeguards,
) -> RecommendationResponse:
    recommendation_service = dependencies.recommendation_service
    assert recommendation_service is not None
    recommendation_started_at = perf_counter()
    try:
        plan = recommendation_service.prepare(domain_request)
        if plan.requires_candidate_proposal:
            discovery_admission = safeguards.admit_discovery()
            if isinstance(discovery_admission, SafeguardRejection):
                emit_event(
                    "recommendation.rejected",
                    request_id=request_id_from_request(request),
                    code=discovery_admission.code,
                    stage="discovery_safeguard",
                    retry_after_seconds=discovery_admission.retry_after_seconds,
                )
                raise _api_error(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    discovery_admission.code,
                    "Solara has reached its current destination-discovery allowance.",
                    retry_after_seconds=discovery_admission.retry_after_seconds,
                )
        result = recommendation_service.recommend_plan(plan)
    except DestinationNotFoundError as exc:
        emit_event(
            "recommendation.failed",
            request_id=request_id_from_request(request),
            code="destination_not_found",
            stage="destination_resolution",
            duration_ms=elapsed_milliseconds(recommendation_started_at),
            destination_count=len(domain_request.destination_queries),
        )
        suggestions = _correction_suggestions(exc, dependencies, safeguards)
        raise _api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "destination_not_found",
            (
                f'Solara couldn\'t find "{exc.query.value}" as a city, country or region. '
                "Review the spelling or choose one of the suggested places."
            ),
            suggestions=suggestions or None,
        ) from exc
    except BroadScopeCombinationError as exc:
        emit_event(
            "recommendation.failed",
            request_id=request_id_from_request(request),
            code="broad_scope_combination_not_supported",
            stage="destination_resolution",
            duration_ms=elapsed_milliseconds(recommendation_started_at),
        )
        raise _api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "broad_scope_combination_not_supported",
            "For now, choose one country or region at a time, or compare individual cities.",
        ) from exc
    except DestinationDiscoveryUnavailableError as exc:
        _emit_recommendation_failure(
            request, "destination_discovery_unavailable", recommendation_started_at
        )
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "destination_discovery_unavailable",
            "Solara couldn't explore new destinations just now. Your trip details are still here.",
        ) from exc
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
    narration_attempted = (
        dependencies.narration_service is not None and safeguards.admit_narration()
    )
    if narration_attempted:
        assert dependencies.narration_service is not None
        narration_started_at = perf_counter()
        narrated = dependencies.narration_service.narrate(result)
        narration_duration_ms = elapsed_milliseconds(narration_started_at)
        result = narrated.recommendation_result
        narration = narrated.narration
    elif dependencies.narration_service is not None:
        emit_event(
            "narration.skipped",
            request_id=request_id_from_request(request),
            code="narration_budget_exhausted",
            stage="safeguard",
        )

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


_SAFEGUARD_MESSAGES = {
    "recommendation_rate_limited": (
        "This public preview is receiving too many recommendation requests. "
        "Please try again shortly."
    ),
    "recommendation_budget_exhausted": (
        "This public preview has reached its current recommendation allowance. "
        "Please try again later."
    ),
    "recommendation_capacity_reached": (
        "Solara is already processing the maximum number of recommendation requests. "
        "Please try again shortly."
    ),
    "discovery_budget_exhausted": (
        "This public preview has reached its destination-discovery allowance. "
        "Please try again later."
    ),
}


def _reject_for_safeguard(request: Request, rejection: SafeguardRejection) -> None:
    emit_event(
        "recommendation.rejected",
        request_id=request_id_from_request(request),
        code=rejection.code,
        stage="safeguard",
        retry_after_seconds=rejection.retry_after_seconds,
    )
    raise _api_error(
        status.HTTP_429_TOO_MANY_REQUESTS,
        rejection.code,
        _SAFEGUARD_MESSAGES[rejection.code],
        retry_after_seconds=rejection.retry_after_seconds,
    )


def _emit_recommendation_failure(request: Request, code: str, started_at: float) -> None:
    emit_event(
        "recommendation.failed",
        request_id=request_id_from_request(request),
        code=code,
        stage="recommendation",
        duration_ms=elapsed_milliseconds(started_at),
    )


def _api_error(
    status_code: int,
    code: str,
    message: str,
    *,
    retry_after_seconds: int | None = None,
    suggestions: tuple[str, ...] | None = None,
) -> HTTPException:
    headers = {"Retry-After": str(retry_after_seconds)} if retry_after_seconds is not None else None
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            **({"suggestions": list(suggestions)} if suggestions else {}),
        },
        headers=headers,
    )


def _correction_suggestions(
    error: DestinationNotFoundError,
    dependencies: ApiDependencies,
    safeguards: ApiSafeguards,
) -> tuple[str, ...]:
    """Attempt bounded spelling assistance without exposing provider failures."""

    if error.suggestions:
        return error.suggestions
    service = dependencies.travel_scope_suggestion_service
    if service is None:
        return ()
    admission = safeguards.admit_suggestion()
    if isinstance(admission, SafeguardRejection):
        return ()
    assert isinstance(admission, SuggestionLease)
    try:
        with admission:
            return tuple(item.display_name for item in service.suggest(error.query))
    except (ProviderError, TypeError, ValueError):
        return ()
