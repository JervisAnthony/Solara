"""Tests for Solara's provider-independent historical-weather contract."""

from datetime import date

from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation
from solara_travel.ports.weather import HistoricalWeatherProvider


class FakeHistoricalWeatherProvider:
    """Conforming provider fake that records domain-owned inputs."""

    def __init__(
        self,
        observations: tuple[WeatherObservation, ...],
    ) -> None:
        self.observations = observations
        self.destination: Destination | None = None
        self.period: TravelPeriod | None = None

    def get_historical_weather(
        self,
        destination: Destination,
        period: TravelPeriod,
    ) -> tuple[WeatherObservation, ...]:
        """Record inputs and return configured normalized observations."""

        self.destination = destination
        self.period = period
        return self.observations


class NonWeatherProvider:
    """Object without the historical-weather provider behavior."""


def _destination() -> Destination:
    return Destination(
        name="Kyoto",
        country="Japan",
        coordinates=GeoCoordinates(latitude=35.0116, longitude=135.7681),
    )


def _period() -> TravelPeriod:
    return TravelPeriod(start_date=date(2020, 4, 1), end_date=date(2020, 4, 2))


def _observation() -> WeatherObservation:
    return WeatherObservation(
        observed_on=date(2020, 4, 1),
        temperature_celsius=13.2,
        relative_humidity_percent=61.0,
        precipitation_mm=0.4,
    )


def test_conforming_provider_satisfies_runtime_contract() -> None:
    """A structurally conforming implementation should satisfy the port."""

    assert isinstance(FakeHistoricalWeatherProvider(()), HistoricalWeatherProvider)


def test_nonconforming_object_does_not_satisfy_runtime_contract() -> None:
    """Objects without retrieval behavior should not satisfy the port."""

    assert not isinstance(NonWeatherProvider(), HistoricalWeatherProvider)


def test_provider_receives_solara_owned_inputs() -> None:
    """The port boundary should pass original domain destination and period values."""

    destination = _destination()
    period = _period()
    provider = FakeHistoricalWeatherProvider((_observation(),))

    provider.get_historical_weather(destination, period)

    assert provider.destination is destination
    assert provider.period is period


def test_provider_returns_immutable_observation_tuple() -> None:
    """Historical weather evidence should use an immutable tuple contract."""

    provider = FakeHistoricalWeatherProvider((_observation(),))

    result = provider.get_historical_weather(_destination(), _period())

    assert isinstance(result, tuple)
    assert result == (_observation(),)


def test_provider_supports_empty_observation_tuple() -> None:
    """A valid provider may return no historical observations."""

    provider = FakeHistoricalWeatherProvider(())

    assert provider.get_historical_weather(_destination(), _period()) == ()
