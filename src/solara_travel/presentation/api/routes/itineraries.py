"""Provider-bounded activity discovery for the Itinerary Studio."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from solara_travel.application import ActivityDiscoveryService, DestinationNotFoundError
from solara_travel.domain import DestinationQuery, TravelScopeKind
from solara_travel.ports import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.ports.places import TravelScopeResolutionPort
from solara_travel.presentation.api.dependencies import ApiDependencies
from solara_travel.presentation.api.itinerary_schemas import (
    ActivityOptionResponse,
    ActivityPaletteRequest,
    ActivityPaletteResponse,
    DurationEstimateResponse,
    ItineraryCoordinatesResponse,
    ItineraryDestinationResponse,
)
from solara_travel.presentation.api.safeguards import (
    ApiSafeguards,
    SafeguardRejection,
    SuggestionLease,
)
from solara_travel.presentation.api.schemas import ApiErrorResponse

router = APIRouter(prefix="/api/v1", tags=["itineraries"])


def _configured_services(
    request: Request,
) -> tuple[ActivityDiscoveryService, TravelScopeResolutionPort]:
    dependencies: ApiDependencies = request.app.state.api_dependencies
    recommendation_service = dependencies.recommendation_service
    if recommendation_service is None:
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "itinerary_studio_unconfigured",
            "Itinerary Studio travel data is not configured.",
        )
    resolver = recommendation_service.scope_resolver
    if resolver is None and isinstance(
        recommendation_service.places_provider, TravelScopeResolutionPort
    ):
        resolver = recommendation_service.places_provider
    if resolver is None:
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "itinerary_studio_unconfigured",
            "Validated destination resolution is not configured.",
        )
    return ActivityDiscoveryService(recommendation_service.places_provider), resolver


@router.post(
    "/itinerary-activities",
    response_model=ActivityPaletteResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiErrorResponse},
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": ApiErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ApiErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ApiErrorResponse},
    },
)
def discover_itinerary_activities(
    request: Request,
    request_body: ActivityPaletteRequest,
    services: Annotated[
        tuple[ActivityDiscoveryService, TravelScopeResolutionPort],
        Depends(_configured_services),
    ],
) -> ActivityPaletteResponse:
    """Resolve a locality and return at most twelve trusted activity options."""

    safeguards: ApiSafeguards = request.app.state.api_safeguards
    admission = safeguards.admit_suggestion()
    if isinstance(admission, SafeguardRejection):
        raise _api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            admission.code,
            "Itinerary discovery is receiving too many requests. Please try shortly.",
        )
    assert isinstance(admission, SuggestionLease)
    discovery, resolver = services
    try:
        with admission:
            scope = resolver.resolve_travel_scope(DestinationQuery(request_body.destination_query))
            if scope is None or scope.kind is not TravelScopeKind.LOCALITY:
                raise DestinationNotFoundError(DestinationQuery(request_body.destination_query))
            destination = scope.to_destination()
            options = discovery.discover(destination)
    except DestinationNotFoundError as exc:
        raise _api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "destination_not_found",
            "Choose a validated city or locality before discovering activities.",
        ) from exc
    except (
        ProviderAuthenticationError,
        ProviderRateLimitError,
        ProviderUnavailableError,
    ) as exc:
        raise _api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_unavailable",
            "Activity ideas are temporarily unavailable; the itinerary remains usable.",
        ) from exc
    except (ProviderResponseError, ProviderError, TypeError, ValueError) as exc:
        raise _api_error(
            status.HTTP_502_BAD_GATEWAY,
            "activity_discovery_failed",
            "Activity ideas could not be prepared safely.",
        ) from exc

    return ActivityPaletteResponse(
        destination=ItineraryDestinationResponse(
            name=destination.name,
            country=destination.country,
            coordinates=ItineraryCoordinatesResponse(
                latitude=destination.coordinates.latitude,
                longitude=destination.coordinates.longitude,
            ),
        ),
        activities=[
            ActivityOptionResponse(
                identity=option.identity,
                name=option.name,
                category=option.category,
                coordinates=(
                    None
                    if option.coordinates is None
                    else ItineraryCoordinatesResponse(
                        latitude=option.coordinates.latitude,
                        longitude=option.coordinates.longitude,
                    )
                ),
                duration=(
                    None
                    if option.duration is None
                    else DurationEstimateResponse(
                        minimum_minutes=option.duration.minimum_minutes,
                        maximum_minutes=option.duration.maximum_minutes,
                        typical_minutes=option.duration.typical_minutes,
                        provenance=option.duration.provenance.value,
                        confidence=option.duration.confidence.value,
                    )
                ),
                accessibility=option.accessibility.value,
            )
            for option in options
        ],
        maximum_options=discovery.maximum_options,
    )


def _api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
