"""Tests for the deterministic recommendation application service."""

from dataclasses import FrozenInstanceError
from datetime import date
from math import inf, nan

import pytest

from solara_travel.application import RecommendationService
from solara_travel.domain.attraction import Attraction
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation
from solara_travel.ports.errors import ProviderUnavailableError


def _destination(
    name: str,
    latitude: float,
    longitude: float,
    country: str = "Japan",
) -> Destination:
    return Destination(
        name=name,
        country=country,
        coordinates=GeoCoordinates(latitude=latitude, longitude=longitude),
    )


def _attraction(name: str, latitude: float, longitude: float) -> Attraction:
    return Attraction(
        name=name,
        category="attraction",
        coordinates=GeoCoordinates(latitude=latitude, longitude=longitude),
    )


def _request(destination: Destination | None = None) -> RecommendationRequest:
    return RecommendationRequest(
        travel_period=TravelPeriod(date(2027, 4, 10), date(2027, 4, 12)),
        destination=destination,
    )


def _weather(*temperatures: float) -> tuple[WeatherObservation, ...]:
    return tuple(
        WeatherObservation(
            observed_on=date(2020 + index, 4, 10),
            temperature_celsius=temperature,
            relative_humidity_percent=60.0,
            precipitation_mm=1.0,
        )
        for index, temperature in enumerate(temperatures)
    )


class FakePlacesProvider:
    def __init__(
        self,
        destinations: tuple[Destination, ...],
        attractions: dict[Destination, tuple[Attraction, ...]] | None = None,
    ) -> None:
        self.destinations = destinations
        self.attractions = attractions or {}
        self.destination_requests: list[RecommendationRequest] = []
        self.attraction_requests: list[Destination] = []

    def discover_destinations(
        self,
        request: RecommendationRequest,
    ) -> tuple[Destination, ...]:
        self.destination_requests.append(request)
        return self.destinations

    def discover_attractions(
        self,
        destination: Destination,
    ) -> tuple[Attraction, ...]:
        self.attraction_requests.append(destination)
        return self.attractions.get(destination, ())


class FakeWeatherProvider:
    def __init__(
        self,
        observations: dict[Destination, tuple[WeatherObservation, ...]],
    ) -> None:
        self.observations = observations
        self.requests: list[tuple[Destination, TravelPeriod]] = []

    def get_historical_weather(
        self,
        destination: Destination,
        period: TravelPeriod,
    ) -> tuple[WeatherObservation, ...]:
        self.requests.append((destination, period))
        return self.observations[destination]


def _service(
    places: FakePlacesProvider,
    weather: FakeWeatherProvider,
    *,
    comfort_range: TemperatureComfortRange | None = None,
    seasonal_weight: float = 1.0,
) -> RecommendationService:
    return RecommendationService(
        places_provider=places,
        weather_provider=weather,
        historical_period=TravelPeriod(date(2020, 1, 1), date(2024, 12, 31)),
        comfort_range=comfort_range
        or TemperatureComfortRange(18.0, 28.0, 10.0),
        seasonal_weight=seasonal_weight,
    )


def test_service_discovers_candidates_and_builds_ranked_results() -> None:
    cool = _destination("Cool City", 35.0, 135.0)
    warm = _destination("Warm City", 34.0, 134.0)
    cool_attraction = _attraction("Cool Temple", 35.1, 135.1)
    warm_attraction = _attraction("Warm Market", 34.1, 134.1)
    places = FakePlacesProvider(
        (warm, cool),
        {cool: (cool_attraction,), warm: (warm_attraction,)},
    )
    weather = FakeWeatherProvider(
        {
            cool: _weather(22.0, 23.0, 24.0),
            warm: _weather(34.0, 35.0, 36.0),
        }
    )
    request = _request()

    result = _service(places, weather).recommend(request)

    assert result.request is request
    assert tuple(item.destination for item in result.recommendations) == (cool, warm)
    assert result.recommendations[0].score > result.recommendations[1].score
    assert result.recommendations[0].evidence.attractions == (cool_attraction,)
    assert result.recommendations[1].evidence.attractions == (warm_attraction,)
    assert places.destination_requests == [request]
    assert places.attraction_requests == [warm, cool]
    assert [destination for destination, _ in weather.requests] == [warm, cool]


def test_ranking_is_stable_when_scores_tie() -> None:
    first = _destination("First", 35.0, 135.0)
    second = _destination("Second", 34.0, 134.0)
    places = FakePlacesProvider((first, second))
    weather = FakeWeatherProvider({first: _weather(22.0), second: _weather(22.0)})

    result = _service(places, weather).recommend(_request())

    assert tuple(item.destination for item in result.recommendations) == (first, second)


def test_empty_candidate_discovery_returns_empty_result() -> None:
    places = FakePlacesProvider(())
    weather = FakeWeatherProvider({})
    request = _request()

    result = _service(places, weather).recommend(request)

    assert result.recommendations == ()
    assert result.recommendation_count == 0
    assert not result.has_recommendations
    assert places.destination_requests == [request]
    assert places.attraction_requests == []
    assert weather.requests == []


def test_preselected_destination_bypasses_destination_discovery() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    attraction = _attraction("Kiyomizu-dera", 34.9949, 135.7850)
    places = FakePlacesProvider(
        (_destination("Ignored", 36.0, 136.0),),
        {destination: (attraction,)},
    )
    weather = FakeWeatherProvider({destination: _weather(22.0, 23.0)})
    request = _request(destination)

    result = _service(places, weather).recommend(request)

    assert places.destination_requests == []
    assert places.attraction_requests == [destination]
    assert tuple(item.destination for item in result.recommendations) == (destination,)


def test_service_uses_explicit_historical_period_for_every_candidate() -> None:
    first = _destination("First", 35.0, 135.0)
    second = _destination("Second", 34.0, 134.0)
    places = FakePlacesProvider((first, second))
    weather = FakeWeatherProvider({first: _weather(22.0), second: _weather(23.0)})
    service = _service(places, weather)

    service.recommend(_request())

    assert weather.requests == [
        (first, service.historical_period),
        (second, service.historical_period),
    ]


def test_service_preserves_provider_attraction_order() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    first = _attraction("First", 35.0, 135.7)
    second = _attraction("Second", 35.1, 135.8)
    places = FakePlacesProvider((destination,), {destination: (second, first)})
    weather = FakeWeatherProvider({destination: _weather(22.0)})

    result = _service(places, weather).recommend(_request())

    assert result.recommendations[0].evidence.attractions == (second, first)


def test_service_builds_seasonal_component_with_configured_weight() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    places = FakePlacesProvider((destination,))
    weather = FakeWeatherProvider({destination: _weather(22.0)})

    result = _service(places, weather, seasonal_weight=0.4).recommend(_request())

    component = result.recommendations[0].components[0]
    assert component.name == "seasonal_temperature_comfort"
    assert component.weight == 0.4
    assert (
        component.score
        == result.recommendations[0].evidence.seasonal_temperature_comfort.score
    )


def test_service_uses_explicit_comfort_range() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    places = FakePlacesProvider((destination,))
    weather = FakeWeatherProvider({destination: _weather(30.0)})
    comfort_range = TemperatureComfortRange(18.0, 28.0, 10.0)

    result = _service(places, weather, comfort_range=comfort_range).recommend(_request())

    assessment = result.recommendations[0].evidence.seasonal_temperature_comfort
    assert assessment.comfort_range is comfort_range
    assert assessment.score == pytest.approx(0.8)


def test_provider_errors_propagate_without_application_translation() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)

    class FailingPlacesProvider(FakePlacesProvider):
        def discover_destinations(
            self,
            request: RecommendationRequest,
        ) -> tuple[Destination, ...]:
            raise ProviderUnavailableError("places unavailable")

    places = FailingPlacesProvider((destination,))
    weather = FakeWeatherProvider({destination: _weather(22.0)})

    with pytest.raises(ProviderUnavailableError, match="places unavailable"):
        _service(places, weather).recommend(_request())


def test_weather_provider_errors_propagate_without_application_translation() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    places = FakePlacesProvider((destination,))

    class FailingWeatherProvider(FakeWeatherProvider):
        def get_historical_weather(
            self,
            destination: Destination,
            period: TravelPeriod,
        ) -> tuple[WeatherObservation, ...]:
            raise ProviderUnavailableError("weather unavailable")

    weather = FailingWeatherProvider({destination: _weather(22.0)})

    with pytest.raises(ProviderUnavailableError, match="weather unavailable"):
        _service(places, weather).recommend(_request())


def test_invalid_request_type_is_rejected_before_provider_use() -> None:
    places = FakePlacesProvider(())
    weather = FakeWeatherProvider({})

    with pytest.raises(TypeError, match="request must be a RecommendationRequest"):
        _service(places, weather).recommend("Kyoto")  # type: ignore[arg-type]

    assert places.destination_requests == []


def test_destination_provider_must_return_tuple() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)

    class ListPlacesProvider(FakePlacesProvider):
        def discover_destinations(self, request: RecommendationRequest):
            return [destination]

    places = ListPlacesProvider((destination,))
    weather = FakeWeatherProvider({destination: _weather(22.0)})

    with pytest.raises(TypeError, match="destination provider must return a tuple"):
        _service(places, weather).recommend(_request())


def test_destination_provider_must_return_destination_values() -> None:
    class InvalidPlacesProvider(FakePlacesProvider):
        def discover_destinations(self, request: RecommendationRequest):
            return ("Kyoto",)

    places = InvalidPlacesProvider(())
    weather = FakeWeatherProvider({})

    with pytest.raises(TypeError, match="must return Destination values"):
        _service(places, weather).recommend(_request())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("places_provider", object(), "places_provider must satisfy PlacesProvider"),
        (
            "weather_provider",
            object(),
            "weather_provider must satisfy HistoricalWeatherProvider",
        ),
        ("historical_period", object(), "historical_period must be a TravelPeriod"),
        (
            "comfort_range",
            object(),
            "comfort_range must be a TemperatureComfortRange",
        ),
    ],
)
def test_service_rejects_invalid_dependencies_and_policy_types(
    field: str,
    value: object,
    message: str,
) -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    places = FakePlacesProvider((destination,))
    weather = FakeWeatherProvider({destination: _weather(22.0)})
    kwargs = {
        "places_provider": places,
        "weather_provider": weather,
        "historical_period": TravelPeriod(date(2020, 1, 1), date(2024, 12, 31)),
        "comfort_range": TemperatureComfortRange(18.0, 28.0, 10.0),
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match=message):
        RecommendationService(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("weight", [0.0, -0.1, 1.1, True, nan, inf])
def test_service_reuses_generic_scoring_validation_for_seasonal_weight(
    weight: object,
) -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    places = FakePlacesProvider((destination,))
    weather = FakeWeatherProvider({destination: _weather(22.0)})

    with pytest.raises((TypeError, ValueError)):
        _service(places, weather, seasonal_weight=weight)  # type: ignore[arg-type]


def test_service_configuration_is_immutable_after_validation() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    places = FakePlacesProvider((destination,))
    weather = FakeWeatherProvider({destination: _weather(22.0)})
    service = _service(places, weather)

    with pytest.raises(FrozenInstanceError):
        service.seasonal_weight = 0.5


def test_result_evidence_uses_only_matching_target_calendar_days() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    places = FakePlacesProvider((destination,))
    weather = FakeWeatherProvider(
        {
            destination: (
                WeatherObservation(date(2020, 4, 9), 22.0, 60.0, 0.0),
                WeatherObservation(date(2020, 4, 10), 23.0, 60.0, 0.0),
                WeatherObservation(date(2020, 4, 12), 24.0, 60.0, 0.0),
                WeatherObservation(date(2020, 4, 13), 25.0, 60.0, 0.0),
            )
        }
    )

    result = _service(places, weather).recommend(_request())

    assert tuple(
        observation.observed_on.day
        for observation in (
            result.recommendations[0].evidence.seasonal_weather.observations
        )
    ) == (10, 12)


def test_no_matching_historical_evidence_remains_visible_as_error() -> None:
    destination = _destination("Kyoto", 35.0116, 135.7681)
    places = FakePlacesProvider((destination,))
    weather = FakeWeatherProvider(
        {
            destination: (
                WeatherObservation(date(2020, 5, 1), 22.0, 60.0, 0.0),
            )
        }
    )

    with pytest.raises(ValueError, match="no historical observations match target period"):
        _service(places, weather).recommend(_request())
