"""Provider contracts for destination and attraction discovery."""

from typing import Protocol, runtime_checkable

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.destination import Destination, DestinationQuery
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel_scope import TravelScope, TravelScopeSuggestion


@runtime_checkable
class DestinationDiscoveryPort(Protocol):
    """Contract for discovering candidate travel destinations."""

    def discover_destinations(
        self,
        request: RecommendationRequest,
    ) -> tuple[Destination, ...]:
        """Return candidate destinations for the supplied recommendation request."""
        ...


@runtime_checkable
class AttractionDiscoveryPort(Protocol):
    """Contract for discovering attractions within a destination."""

    def discover_attractions(
        self,
        destination: Destination,
    ) -> tuple[Attraction, ...]:
        """Return attractions for the supplied destination."""
        ...


@runtime_checkable
class DestinationResolutionPort(Protocol):
    """Contract for resolving an explicit human-entered destination."""

    def resolve_destination(self, query: DestinationQuery) -> Destination | None:
        """Return one normalized destination, or ``None`` for no match."""
        ...


@runtime_checkable
class TravelScopeResolutionPort(Protocol):
    """Contract for resolving locality, region, or country input."""

    def resolve_travel_scope(self, query: DestinationQuery) -> TravelScope | None:
        """Return normalized geographic meaning, or ``None`` for no match."""
        ...


@runtime_checkable
class TravelScopeSuggestionPort(Protocol):
    """Contract for bounded geographic typeahead suggestions."""

    def suggest_travel_scopes(
        self,
        query: DestinationQuery,
    ) -> tuple[TravelScopeSuggestion, ...]:
        """Return at most five display-safe locality/region/country suggestions."""
        ...


@runtime_checkable
class PlacesProvider(
    DestinationDiscoveryPort,
    AttractionDiscoveryPort,
    Protocol,
):
    """Combined backwards-compatible contract for place discovery."""
