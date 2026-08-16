"""Tests for Open-Meteo historical-weather HTTP request behavior."""

from collections.abc import Mapping
from datetime import date

import pytest

from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.travel import TravelPeriod
from solara_travel.infrastructure.http import JsonHttpDecodeError, JsonHttpResponse
from solara_travel.infrastructure.weather.open_meteo import (
    OpenMeteoHistoricalWeatherHttpClient,
)
from solara_travel.ports.errors import (
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)

_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


class FakeGetTransport:
    """Injected GET transport that records calls and returns controlled behavior."""

    def __init__(
        self,
        *,
        response: JsonHttpResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response or JsonHttpResponse(200, {"daily": {}})
        self.error = error
        self.calls: list[dict[str, object]] = []

    def get_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        query: Mapping[str, str | int | float],
        timeout_seconds: float,
    ) -> JsonHttpResponse:
        """Record one GET call and return configured data or failure."""

        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "query": dict(query),
                "timeout_seconds": timeout_seconds,
            }
        )

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
    return TravelPeriod(start_date=date(2020, 4, 1), end_date=date(2020, 4, 3))


def test_http_client_accepts_valid_configuration() -> None:
    """A positive finite timeout should configure the client."""

    transport = FakeGetTransport()
    client = OpenMeteoHistoricalWeatherHttpClient(
        transport=transport,
        timeout_seconds=4.5,
    )

    assert client.transport is transport
    assert client.timeout_seconds == 4.5


def test_http_client_uses_default_timeout() -> None:
    """Open-Meteo should use the shared provider timeout default."""

    assert OpenMeteoHistoricalWeatherHttpClient(FakeGetTransport()).timeout_seconds == 10.0


@pytest.mark.parametrize("timeout", [None, "10", True, False])
def test_http_client_rejects_non_numeric_timeout(timeout: object) -> None:
    """Timeout configuration must be real-valued and exclude booleans."""

    with pytest.raises(TypeError, match="real number"):
        OpenMeteoHistoricalWeatherHttpClient(
            FakeGetTransport(),
            timeout_seconds=timeout,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), float("-inf")])
def test_http_client_rejects_non_finite_timeout(timeout: float) -> None:
    """Timeout configuration must be finite."""

    with pytest.raises(ValueError, match="finite number"):
        OpenMeteoHistoricalWeatherHttpClient(FakeGetTransport(), timeout)


@pytest.mark.parametrize("timeout", [0.0, -0.1])
def test_http_client_rejects_non_positive_timeout(timeout: float) -> None:
    """Timeout configuration must be strictly positive."""

    with pytest.raises(ValueError, match="greater than zero"):
        OpenMeteoHistoricalWeatherHttpClient(FakeGetTransport(), timeout)


def test_fetch_uses_official_archive_endpoint_and_empty_headers() -> None:
    """Public historical requests should use the official no-key endpoint."""

    transport = FakeGetTransport()
    client = OpenMeteoHistoricalWeatherHttpClient(transport)

    client.fetch_historical_weather(_destination(), _period())

    assert transport.calls[0]["url"] == _ARCHIVE_URL
    assert transport.calls[0]["headers"] == {}


def test_fetch_builds_exact_historical_query() -> None:
    """The client should request only normalized daily ERA5 evidence."""

    transport = FakeGetTransport()
    client = OpenMeteoHistoricalWeatherHttpClient(transport)

    client.fetch_historical_weather(_destination(), _period())

    assert transport.calls[0]["query"] == {
        "latitude": 35.0116,
        "longitude": 135.7681,
        "start_date": "2020-04-01",
        "end_date": "2020-04-03",
        "daily": (
            "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum"
        ),
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
        "timeformat": "iso8601",
        "timezone": "auto",
        "models": "era5",
    }


def test_fetch_propagates_configured_timeout() -> None:
    """The explicit timeout should reach the GET transport."""

    transport = FakeGetTransport()
    client = OpenMeteoHistoricalWeatherHttpClient(transport, timeout_seconds=6.25)

    client.fetch_historical_weather(_destination(), _period())

    assert transport.calls[0]["timeout_seconds"] == 6.25


def test_fetch_returns_success_payload_unchanged() -> None:
    """Raw successful payloads should pass unchanged to the provider adapter."""

    payload = {"daily": {"time": []}}
    client = OpenMeteoHistoricalWeatherHttpClient(
        FakeGetTransport(response=JsonHttpResponse(200, payload))
    )

    result = client.fetch_historical_weather(_destination(), _period())

    assert result is payload


def test_fetch_maps_invalid_json_with_cause() -> None:
    """Decode failures should remain response errors with their original cause."""

    error = JsonHttpDecodeError("invalid JSON")
    client = OpenMeteoHistoricalWeatherHttpClient(FakeGetTransport(error=error))

    with pytest.raises(
        ProviderResponseError,
        match="Open-Meteo returned invalid JSON",
    ) as exc_info:
        client.fetch_historical_weather(_destination(), _period())

    assert exc_info.value.__cause__ is error


def test_fetch_maps_rate_limit_status() -> None:
    """HTTP 429 should retain rate-limit semantics."""

    client = OpenMeteoHistoricalWeatherHttpClient(
        FakeGetTransport(response=JsonHttpResponse(429, {}))
    )

    with pytest.raises(ProviderRateLimitError, match="rate limit exceeded"):
        client.fetch_historical_weather(_destination(), _period())


@pytest.mark.parametrize("status_code", [400, 404])
def test_fetch_maps_other_client_error_status(status_code: int) -> None:
    """Other 4xx statuses should represent rejected requests."""

    client = OpenMeteoHistoricalWeatherHttpClient(
        FakeGetTransport(response=JsonHttpResponse(status_code, {}))
    )

    with pytest.raises(ProviderResponseError, match="rejected the request"):
        client.fetch_historical_weather(_destination(), _period())


@pytest.mark.parametrize("status_code", [500, 503])
def test_fetch_maps_server_error_status(status_code: int) -> None:
    """5xx statuses should represent provider unavailability."""

    client = OpenMeteoHistoricalWeatherHttpClient(
        FakeGetTransport(response=JsonHttpResponse(status_code, {}))
    )

    with pytest.raises(ProviderUnavailableError, match="service unavailable"):
        client.fetch_historical_weather(_destination(), _period())


@pytest.mark.parametrize("status_code", [199, 302, 600])
def test_fetch_maps_unexpected_status(status_code: int) -> None:
    """Statuses outside successful, client, and server ranges are malformed responses."""

    client = OpenMeteoHistoricalWeatherHttpClient(
        FakeGetTransport(response=JsonHttpResponse(status_code, {}))
    )

    with pytest.raises(ProviderResponseError, match="unexpected HTTP status"):
        client.fetch_historical_weather(_destination(), _period())


@pytest.mark.parametrize(
    "error",
    [TimeoutError("timed out"), OSError("network unavailable")],
)
def test_fetch_maps_transport_failure_with_cause(error: Exception) -> None:
    """Network and unexpected transport failures should become availability errors."""

    client = OpenMeteoHistoricalWeatherHttpClient(FakeGetTransport(error=error))

    with pytest.raises(
        ProviderUnavailableError,
        match="Open-Meteo weather request failed",
    ) as exc_info:
        client.fetch_historical_weather(_destination(), _period())

    assert exc_info.value.__cause__ is error
