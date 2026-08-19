"""Tests for immutable offline fixture and dataset values."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from solara_travel.domain import Attraction, Destination, GeoCoordinates, WeatherObservation
from solara_travel.infrastructure.offline import (
    DEFAULT_OFFLINE_DATASET,
    DEFAULT_OFFLINE_HISTORICAL_PERIOD,
    OfflineDestinationFixture,
    OfflineTravelDataset,
)


def _destination(name: str = "Test Haven", latitude: float = 1.0) -> Destination:
    return Destination(name, "Fixtureland", GeoCoordinates(latitude, 2.0))


def _attraction(name: str = "Test Gallery") -> Attraction:
    return Attraction(name, "synthetic museum", GeoCoordinates(1.1, 2.1))


def _weather(day: int, temperature: float = 22.0) -> WeatherObservation:
    return WeatherObservation(date(2020, 4, day), temperature, 55.0, 1.0)


def _fixture(
    *,
    destination: Destination | None = None,
    attractions: tuple[Attraction, ...] | None = None,
    historical_weather: tuple[WeatherObservation, ...] | None = None,
) -> OfflineDestinationFixture:
    return OfflineDestinationFixture(
        destination=destination or _destination(),
        attractions=attractions if attractions is not None else (_attraction(),),
        historical_weather=(
            historical_weather if historical_weather is not None else (_weather(10), _weather(11))
        ),
    )


def test_offline_destination_fixture_preserves_valid_values() -> None:
    destination = _destination()
    attractions = (_attraction("First"), _attraction("Second"))
    weather = (_weather(10), _weather(11))

    fixture = OfflineDestinationFixture(destination, attractions, weather)

    assert fixture.destination is destination
    assert fixture.attractions is attractions
    assert fixture.historical_weather is weather


def test_offline_destination_fixture_allows_empty_evidence() -> None:
    fixture = OfflineDestinationFixture(_destination(), (), ())

    assert fixture.attractions == ()
    assert fixture.historical_weather == ()


def test_offline_destination_fixture_requires_destination() -> None:
    with pytest.raises(TypeError, match="destination must be a Destination"):
        OfflineDestinationFixture(None, (), ())  # type: ignore[arg-type]


def test_offline_destination_fixture_requires_attraction_tuple() -> None:
    with pytest.raises(TypeError, match="attractions must be a tuple"):
        OfflineDestinationFixture(_destination(), [_attraction()], ())  # type: ignore[arg-type]


def test_offline_destination_fixture_requires_attraction_values() -> None:
    with pytest.raises(TypeError, match="every attraction must be an Attraction"):
        OfflineDestinationFixture(_destination(), ("gallery",), ())  # type: ignore[arg-type]


def test_offline_destination_fixture_rejects_duplicate_attractions() -> None:
    attraction = _attraction()

    with pytest.raises(ValueError, match="attractions must not contain duplicates"):
        OfflineDestinationFixture(_destination(), (attraction, attraction), ())


def test_offline_destination_fixture_requires_weather_tuple() -> None:
    with pytest.raises(TypeError, match="historical_weather must be a tuple"):
        OfflineDestinationFixture(_destination(), (), [_weather(10)])  # type: ignore[arg-type]


def test_offline_destination_fixture_requires_weather_values() -> None:
    with pytest.raises(TypeError, match="every historical observation"):
        OfflineDestinationFixture(_destination(), (), ("sunny",))  # type: ignore[arg-type]


def test_offline_destination_fixture_rejects_duplicate_weather_dates() -> None:
    with pytest.raises(ValueError, match="observation dates must be unique"):
        OfflineDestinationFixture(_destination(), (), (_weather(10), _weather(10, 23.0)))


def test_offline_destination_fixture_rejects_out_of_order_weather() -> None:
    with pytest.raises(ValueError, match="strictly increasing by date"):
        OfflineDestinationFixture(_destination(), (), (_weather(11), _weather(10)))


def test_offline_destination_fixture_is_frozen() -> None:
    fixture = _fixture()

    with pytest.raises(FrozenInstanceError):
        fixture.attractions = ()  # type: ignore[misc]


def test_offline_travel_dataset_preserves_fixture_order() -> None:
    first = _fixture(destination=_destination("First", 1.0))
    second = _fixture(destination=_destination("Second", 2.0))
    fixtures = (first, second)

    dataset = OfflineTravelDataset(fixtures)

    assert dataset.fixtures is fixtures


def test_offline_travel_dataset_allows_empty_dataset() -> None:
    assert OfflineTravelDataset(()).fixtures == ()


def test_offline_travel_dataset_requires_fixture_tuple() -> None:
    with pytest.raises(TypeError, match="fixtures must be a tuple"):
        OfflineTravelDataset([])  # type: ignore[arg-type]


def test_offline_travel_dataset_requires_fixture_values() -> None:
    with pytest.raises(TypeError, match="every fixture must be an OfflineDestinationFixture"):
        OfflineTravelDataset(("fixture",))  # type: ignore[arg-type]


def test_offline_travel_dataset_rejects_duplicate_destinations() -> None:
    destination = _destination()

    with pytest.raises(ValueError, match="fixture destinations must be unique"):
        OfflineTravelDataset((_fixture(destination=destination), _fixture(destination=destination)))


def test_offline_travel_dataset_is_frozen() -> None:
    dataset = OfflineTravelDataset(())

    with pytest.raises(FrozenInstanceError):
        dataset.fixtures = ()  # type: ignore[misc]


def test_default_offline_dataset_has_valid_synthetic_seasonal_evidence() -> None:
    fixtures = DEFAULT_OFFLINE_DATASET.fixtures

    assert len(fixtures) == 3
    assert len({fixture.destination for fixture in fixtures}) == 3
    assert all(fixture.destination.country == "Fixtureland" for fixture in fixtures)
    assert all(len(fixture.attractions) >= 2 for fixture in fixtures)
    assert all(len(fixture.historical_weather) == 15 for fixture in fixtures)
    assert all(
        tuple(observation.observed_on for observation in fixture.historical_weather)
        == tuple(sorted(observation.observed_on for observation in fixture.historical_weather))
        for fixture in fixtures
    )
    assert all(
        {observation.observed_on.year for observation in fixture.historical_weather}
        == {2020, 2021, 2022, 2023, 2024}
        for fixture in fixtures
    )
    assert all(
        {
            (observation.observed_on.month, observation.observed_on.day)
            for observation in fixture.historical_weather
        }
        == {(4, 10), (4, 11), (4, 12)}
        for fixture in fixtures
    )
    assert all(
        DEFAULT_OFFLINE_HISTORICAL_PERIOD.start_date
        <= observation.observed_on
        <= DEFAULT_OFFLINE_HISTORICAL_PERIOD.end_date
        for fixture in fixtures
        for observation in fixture.historical_weather
    )
