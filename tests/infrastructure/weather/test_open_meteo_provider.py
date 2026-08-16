"""Tests for the Open-Meteo historical-weather provider adapter."""

from datetime import date

import pytest

from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation
from solara_travel.infrastructure.weather.open_meteo import (
    OpenMeteoHistoricalWeatherProvider,
)
from solara_travel.ports.errors import (
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.ports.weather import HistoricalWeatherProvider


class FakeOpenMeteoClient:
    """Raw Open-Meteo client fake used by offline provider tests."""

    def __init__(
        self,
        *,
        response: object = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response if response is not None else _payload()
        self.error = error
        self.destination: Destination | None = None
        self.period: TravelPeriod | None = None

    def fetch_historical_weather(
        self,
        destination: Destination,
        period: TravelPeriod,
    ) -> object:
        """Record the original domain inputs and return configured behavior."""

        self.destination = destination
        self.period = period

        if self.error is not None:
            raise self.error

        return self.response


def _destination() -> Destination:
    return Destination(
        name="Kyoto",
        country="Japan",
        coordinates=GeoCoordinates(latitude=35.0116, longitude=135.7681),
    )


def _period() -> TravelPeriod:
    return TravelPeriod(start_date=date(2020, 4, 1), end_date=date(2020, 4, 2))


def _payload() -> dict[str, object]:
    return {
        "daily": {
            "time": ["2020-04-01", "2020-04-02"],
            "temperature_2m_mean": [13.2, 14.1],
            "relative_humidity_2m_mean": [61.0, 58.0],
            "precipitation_sum": [0.4, 0.0],
        }
    }


def test_provider_satisfies_historical_weather_contract() -> None:
    """The adapter should structurally satisfy Solara's weather port."""

    provider = OpenMeteoHistoricalWeatherProvider(FakeOpenMeteoClient())

    assert isinstance(provider, HistoricalWeatherProvider)


def test_provider_passes_original_domain_inputs_to_client() -> None:
    """The adapter should not replace or reshape destination and period values."""

    destination = _destination()
    period = _period()
    client = FakeOpenMeteoClient()
    provider = OpenMeteoHistoricalWeatherProvider(client)

    provider.get_historical_weather(destination, period)

    assert client.destination is destination
    assert client.period is period


def test_provider_normalizes_and_preserves_observation_order() -> None:
    """Raw daily arrays should become ordered domain weather observations."""

    provider = OpenMeteoHistoricalWeatherProvider(FakeOpenMeteoClient())

    result = provider.get_historical_weather(_destination(), _period())

    assert result == (
        WeatherObservation(date(2020, 4, 1), 13.2, 61.0, 0.4),
        WeatherObservation(date(2020, 4, 2), 14.1, 58.0, 0.0),
    )
    assert isinstance(result, tuple)


def test_provider_returns_empty_tuple_for_empty_response() -> None:
    """A valid response with empty arrays should remain an immutable empty result."""

    provider = OpenMeteoHistoricalWeatherProvider(
        FakeOpenMeteoClient(
            response={
                "daily": {
                    "time": [],
                    "temperature_2m_mean": [],
                    "relative_humidity_2m_mean": [],
                    "precipitation_sum": [],
                }
            }
        )
    )

    assert provider.get_historical_weather(_destination(), _period()) == ()


def test_provider_preserves_malformed_response_semantics() -> None:
    """Normalization failures should remain provider-response errors."""

    provider = OpenMeteoHistoricalWeatherProvider(
        FakeOpenMeteoClient(response={"daily": None})
    )

    with pytest.raises(ProviderResponseError, match="daily must be an object"):
        provider.get_historical_weather(_destination(), _period())


@pytest.mark.parametrize(
    "error",
    [
        ProviderRateLimitError("rate limited"),
        ProviderResponseError("bad response"),
        ProviderUnavailableError("unavailable"),
    ],
)
def test_provider_propagates_known_provider_error(error: ProviderError) -> None:
    """Known semantic provider failures should propagate unchanged."""

    provider = OpenMeteoHistoricalWeatherProvider(FakeOpenMeteoClient(error=error))

    with pytest.raises(type(error)) as exc_info:
        provider.get_historical_weather(_destination(), _period())

    assert exc_info.value is error


def test_provider_wraps_unexpected_client_failure_with_cause() -> None:
    """Unexpected client failures should become provider-unavailable errors."""

    error = TimeoutError("timed out")
    provider = OpenMeteoHistoricalWeatherProvider(FakeOpenMeteoClient(error=error))

    with pytest.raises(
        ProviderUnavailableError,
        match="Open-Meteo weather request failed",
    ) as exc_info:
        provider.get_historical_weather(_destination(), _period())

    assert exc_info.value.__cause__ is error
