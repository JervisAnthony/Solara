"""Same-origin geographic typeahead route for the public planner."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from solara_travel.application import TravelScopeSuggestionService
from solara_travel.domain import DestinationQuery
from solara_travel.ports import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.presentation.api.dependencies import ApiDependencies
from solara_travel.presentation.api.observability import emit_event, request_id_from_request
from solara_travel.presentation.api.safeguards import (
    ApiSafeguards,
    SafeguardRejection,
    SuggestionLease,
)
from solara_travel.presentation.api.schemas import ApiErrorResponse
from solara_travel.presentation.api.travel_scope_schemas import (
    TravelScopeSuggestionItem,
    TravelScopeSuggestionRequest,
    TravelScopeSuggestionResponse,
)

router = APIRouter(prefix="/api/v1", tags=["travel scopes"])


def _configured_service(request: Request) -> TravelScopeSuggestionService:
    dependencies: ApiDependencies = request.app.state.api_dependencies
    if dependencies.travel_scope_suggestion_service is None:
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "travel_scope_suggestions_unconfigured",
            "Travel suggestions are not configured.",
        )
    return dependencies.travel_scope_suggestion_service


@router.post(
    "/travel-scope-suggestions",
    response_model=TravelScopeSuggestionResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiErrorResponse},
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": ApiErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ApiErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ApiErrorResponse},
    },
)
def suggest_travel_scopes(
    request: Request,
    request_body: TravelScopeSuggestionRequest,
    service: Annotated[TravelScopeSuggestionService, Depends(_configured_service)],
) -> TravelScopeSuggestionResponse:
    """Return bounded Google-validated geographic predictions without logging text."""

    safeguards: ApiSafeguards = request.app.state.api_safeguards
    admission = safeguards.admit_suggestion()
    if isinstance(admission, SafeguardRejection):
        emit_event(
            "travel_scope_suggestion.rejected",
            request_id=request_id_from_request(request),
            code=admission.code,
            stage="safeguard",
            retry_after_seconds=admission.retry_after_seconds,
        )
        raise _api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            admission.code,
            "Travel suggestions are receiving too many requests. Keep typing or try shortly.",
            retry_after_seconds=admission.retry_after_seconds,
        )
    assert isinstance(admission, SuggestionLease)
    try:
        with admission:
            suggestions = service.suggest(DestinationQuery(request_body.query))
    except ProviderRateLimitError as exc:
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_rate_limited",
            "Travel suggestions are temporarily busy.",
        ) from exc
    except (ProviderAuthenticationError, ProviderUnavailableError) as exc:
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_unavailable",
            "Travel suggestions are temporarily unavailable.",
        ) from exc
    except (ProviderResponseError, ProviderError) as exc:
        raise _api_error(
            status.HTTP_502_BAD_GATEWAY,
            "provider_invalid_response",
            "Travel suggestions could not be prepared.",
        ) from exc
    return TravelScopeSuggestionResponse(
        suggestions=[
            TravelScopeSuggestionItem(
                display_name=suggestion.display_name,
                kind=suggestion.kind.value,
            )
            for suggestion in suggestions
        ]
    )


def _api_error(
    status_code: int,
    code: str,
    message: str,
    *,
    retry_after_seconds: int | None = None,
) -> HTTPException:
    headers = {"Retry-After": str(retry_after_seconds)} if retry_after_seconds else None
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers=headers,
    )
