"""Tests for place-discovery provider contracts."""

from datetime import date

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.preferences import (
    TravellerInterests,
    TravellerPreferences,
)
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.ports.places import (
    AttractionDiscoveryPort,
    DestinationDiscoveryPort,
    PlacesProvider,
)


def make_recommendation_request() -> RecommendationRequest:
    """Return deterministic traveller context for provider-contract tests."""

    return RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
        ),
        preferences=TravellerPreferences(
            interests=TravellerInterests(
                interests=("history", "food"),
            ),
            preferred_pace="moderate",
            preferred_climate="mild",
        ),
    )


class StubDestinationDiscovery:
    """Minimal structurally compatible destination-discovery provider."""

    def discover_destinations(
        self,
        request: RecommendationRequest,
    ) -> tuple[Destination, ...]:
        """Return deterministic candidates for a recommendation request."""

        assert request.travel_period.duration_days == 7

        return (
            Destination(
                name="Kyoto",
                country="Japan",
                coordinates=GeoCoordinates(
                    latitude=35.0116,
                    longitude=135.7681,
                ),
            ),
        )


class StubAttractionDiscovery:
    """Minimal structurally compatible attraction-discovery provider."""

    def discover_attractions(
        self,
        destination: Destination,
    ) -> tuple[Attraction, ...]:
        """Return deterministic attractions for a destination."""

        return (
            Attraction(
                name=f"{destination.name} National Museum",
                category="museum",
                coordinates=destination.coordinates,
            ),
        )


class StubPlacesProvider:
    """Minimal provider implementing both place-discovery capabilities."""

    def discover_destinations(
        self,
        request: RecommendationRequest,
    ) -> tuple[Destination, ...]:
        """Return deterministic candidates for a recommendation request."""

        assert request.preferences.preferred_climate == "mild"

        return (
            Destination(
                name="Kyoto",
                country="Japan",
                coordinates=GeoCoordinates(
                    latitude=35.0116,
                    longitude=135.7681,
                ),
            ),
        )

    def discover_attractions(
        self,
        destination: Destination,
    ) -> tuple[Attraction, ...]:
        """Return deterministic attractions for a destination."""

        return (
            Attraction(
                name="Kiyomizu-dera",
                category="temple",
                coordinates=GeoCoordinates(
                    latitude=34.9949,
                    longitude=135.7850,
                ),
            ),
        )


def test_destination_discovery_port_supports_structural_typing() -> None:
    """Providers need not inherit from Solara classes to satisfy the port."""

    provider = StubDestinationDiscovery()

    assert isinstance(provider, DestinationDiscoveryPort)


def test_attraction_discovery_port_supports_structural_typing() -> None:
    """Attraction providers should satisfy the contract structurally."""

    provider = StubAttractionDiscovery()

    assert isinstance(provider, AttractionDiscoveryPort)


def test_places_provider_combines_destination_and_attraction_discovery() -> None:
    """A places provider may implement both discovery capabilities."""

    provider = StubPlacesProvider()

    assert isinstance(provider, DestinationDiscoveryPort)
    assert isinstance(provider, AttractionDiscoveryPort)
    assert isinstance(provider, PlacesProvider)


def test_destination_discovery_accepts_recommendation_request() -> None:
    """Destination discovery should receive Solara-owned traveller context."""

    request = make_recommendation_request()
    provider: DestinationDiscoveryPort = StubDestinationDiscovery()

    destinations = provider.discover_destinations(request)

    assert destinations == (
        Destination(
            name="Kyoto",
            country="Japan",
            coordinates=GeoCoordinates(
                latitude=35.0116,
                longitude=135.7681,
            ),
        ),
    )


def test_attraction_discovery_accepts_solara_destination() -> None:
    """Attraction discovery should use a Solara destination as its input."""

    destination = Destination(
        name="Kyoto",
        country="Japan",
        coordinates=GeoCoordinates(
            latitude=35.0116,
            longitude=135.7681,
        ),
    )
    provider: AttractionDiscoveryPort = StubAttractionDiscovery()

    attractions = provider.discover_attractions(destination)

    assert attractions == (
        Attraction(
            name="Kyoto National Museum",
            category="museum",
            coordinates=destination.coordinates,
        ),
    )


def test_places_provider_returns_only_domain_owned_models() -> None:
    """The combined places contract should expose domain-owned values."""

    request = make_recommendation_request()
    provider: PlacesProvider = StubPlacesProvider()

    destinations = provider.discover_destinations(request)
    attractions = provider.discover_attractions(destinations[0])

    assert all(isinstance(destination, Destination) for destination in destinations)
    assert all(isinstance(attraction, Attraction) for attraction in attractions)


def test_place_discovery_results_are_immutable_sequences() -> None:
    """Discovery contracts should return tuples rather than mutable lists."""

    request = make_recommendation_request()
    provider: PlacesProvider = StubPlacesProvider()

    destinations = provider.discover_destinations(request)
    attractions = provider.discover_attractions(destinations[0])

    assert isinstance(destinations, tuple)
    assert isinstance(attractions, tuple)