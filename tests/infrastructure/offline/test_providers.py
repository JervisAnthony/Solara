"""Tests for deterministic offline provider adapters."""

from datetime import date

import pytest

from solara_travel.domain import (
    Attraction,
    Destination,
    GeoCoordinates,
    RecommendationRequest,
    TravelPeriod,
    WeatherObservation,
)
from solara_travel.infrastructure.offline import (
    OfflineDestinationFixture,
    OfflineHistoricalWeatherProvider,
    OfflinePlacesProvider,
    OfflineTravelDataset,
)
from solara_travel.ports import HistoricalWeatherProvider, PlacesProvider


def _destination(name: str, latitude: float) -> Destination:
    return Destination(name, "Fixtureland", GeoCoordinates(latitude, 10.0))


def _dataset() -> OfflineTravelDataset:
    first = _destination("First Haven", 1.0)
    second = _destination("Second Haven", 2.0)
    first_attractions = (
        Attraction("First Arch", "synthetic landmark", GeoCoordinates(1.1, 10.1)),
        Attraction("First Garden", "synthetic garden", GeoCoordinates(1.2, 10.2)),
    )
    observations = tuple(
        WeatherObservation(date(2020, 1, day), 20.0 + day, 50.0, 0.5) for day in range(1, 6)
    )
    return OfflineTravelDataset(
        (
            OfflineDestinationFixture(first, first_attractions, observations),
            OfflineDestinationFixture(second, (), ()),
        )
    )


def _request() -> RecommendationRequest:
    return RecommendationRequest(TravelPeriod(date(2026, 1, 1), date(2026, 1, 2)))


def test_offline_providers_satisfy_runtime_protocols() -> None:
    dataset = _dataset()

    assert isinstance(OfflinePlacesProvider(dataset), PlacesProvider)
    assert isinstance(OfflineHistoricalWeatherProvider(dataset), HistoricalWeatherProvider)


@pytest.mark.parametrize("provider_type", [OfflinePlacesProvider, OfflineHistoricalWeatherProvider])
def test_offline_providers_require_offline_dataset(provider_type: type[object]) -> None:
    with pytest.raises(TypeError, match="dataset must be an OfflineTravelDataset"):
        provider_type(None)  # type: ignore[call-arg]


def test_offline_places_provider_preserves_candidate_order() -> None:
    dataset = _dataset()
    provider = OfflinePlacesProvider(dataset)

    destinations = provider.discover_destinations(_request())

    assert destinations == tuple(fixture.destination for fixture in dataset.fixtures)
    assert provider.dataset is dataset


def test_offline_places_provider_returns_empty_candidates_for_empty_dataset() -> None:
    provider = OfflinePlacesProvider(OfflineTravelDataset(()))

    assert provider.discover_destinations(_request()) == ()


def test_offline_places_provider_requires_recommendation_request() -> None:
    provider = OfflinePlacesProvider(_dataset())

    with pytest.raises(TypeError, match="request must be a RecommendationRequest"):
        provider.discover_destinations(None)  # type: ignore[arg-type]


def test_offline_places_provider_returns_ordered_attractions() -> None:
    dataset = _dataset()
    provider = OfflinePlacesProvider(dataset)

    attractions = provider.discover_attractions(dataset.fixtures[0].destination)

    assert attractions is dataset.fixtures[0].attractions


def test_offline_places_provider_returns_empty_for_unknown_destination() -> None:
    provider = OfflinePlacesProvider(_dataset())
    unknown = _destination("Unknown Haven", 3.0)

    assert provider.discover_attractions(unknown) == ()


def test_offline_places_provider_uses_complete_destination_equality() -> None:
    dataset = _dataset()
    same_name_different_coordinates = _destination("First Haven", 8.0)

    assert (
        OfflinePlacesProvider(dataset).discover_attractions(same_name_different_coordinates) == ()
    )


def test_offline_places_provider_requires_destination() -> None:
    provider = OfflinePlacesProvider(_dataset())

    with pytest.raises(TypeError, match="destination must be a Destination"):
        provider.discover_attractions(None)  # type: ignore[arg-type]


def test_offline_weather_provider_filters_period_inclusively() -> None:
    dataset = _dataset()
    provider = OfflineHistoricalWeatherProvider(dataset)
    destination = dataset.fixtures[0].destination
    period = TravelPeriod(date(2020, 1, 2), date(2020, 1, 4))

    observations = provider.get_historical_weather(destination, period)

    assert tuple(observation.observed_on.day for observation in observations) == (2, 3, 4)
    assert observations == dataset.fixtures[0].historical_weather[1:4]
    assert provider.dataset is dataset


def test_offline_weather_provider_supports_exact_one_day_period() -> None:
    dataset = _dataset()
    destination = dataset.fixtures[0].destination
    period = TravelPeriod(date(2020, 1, 3), date(2020, 1, 3))

    observations = OfflineHistoricalWeatherProvider(dataset).get_historical_weather(
        destination, period
    )

    assert observations == (dataset.fixtures[0].historical_weather[2],)


def test_offline_weather_provider_returns_empty_for_uncovered_period() -> None:
    dataset = _dataset()
    period = TravelPeriod(date(2021, 1, 1), date(2021, 1, 2))

    assert (
        OfflineHistoricalWeatherProvider(dataset).get_historical_weather(
            dataset.fixtures[0].destination, period
        )
        == ()
    )


def test_offline_weather_provider_returns_empty_for_unknown_destination() -> None:
    provider = OfflineHistoricalWeatherProvider(_dataset())
    period = TravelPeriod(date(2020, 1, 1), date(2020, 1, 5))

    assert provider.get_historical_weather(_destination("Unknown", 9.0), period) == ()


def test_offline_weather_provider_requires_destination() -> None:
    provider = OfflineHistoricalWeatherProvider(_dataset())
    period = TravelPeriod(date(2020, 1, 1), date(2020, 1, 5))

    with pytest.raises(TypeError, match="destination must be a Destination"):
        provider.get_historical_weather(None, period)  # type: ignore[arg-type]


def test_offline_weather_provider_requires_travel_period() -> None:
    provider = OfflineHistoricalWeatherProvider(_dataset())
    destination = provider.dataset.fixtures[0].destination

    with pytest.raises(TypeError, match="period must be a TravelPeriod"):
        provider.get_historical_weather(destination, None)  # type: ignore[arg-type]
