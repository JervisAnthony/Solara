"""Provider contracts for destination and attraction discovery."""

from typing import Protocol, runtime_checkable

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.destination import Destination
from solara_travel.domain.recommendation import RecommendationRequest


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
class PlacesProvider(
    DestinationDiscoveryPort,
    AttractionDiscoveryPort,
    Protocol,
):
    """Combined contract for providers supporting place discovery."""