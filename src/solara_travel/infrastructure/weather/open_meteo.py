"""Open-Meteo historical-weather retrieval and normalization."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from math import isfinite
from numbers import Real
from typing import Protocol

from solara_travel.domain.destination import Destination
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation
from solara_travel.infrastructure.http import (
    JsonHttpDecodeError,
    JsonHttpGetTransport,
)
from solara_travel.ports.errors import (
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)

_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
_DAILY_VARIABLES = (
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "precipitation_sum",
)
_REQUIRED_DAILY_FIELDS = ("time", *_DAILY_VARIABLES)
_EXPECTED_DAILY_UNITS = {
    "time": "iso8601",
    "temperature_2m_mean": "°C",
    "relative_humidity_2m_mean": "%",
    "precipitation_sum": "mm",
}


class OpenMeteoHistoricalWeatherClient(Protocol):
    """Raw-response client required by the Open-Meteo provider adapter."""

    def fetch_historical_weather(
        self,
        destination: Destination,
        period: TravelPeriod,
    ) -> object:
        """Return an Open-Meteo historical-weather response."""
        ...


@dataclass(slots=True)
class OpenMeteoHistoricalWeatherHttpClient:
    """Open-Meteo archive client using an injected JSON GET transport."""

    transport: JsonHttpGetTransport
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        """Validate client configuration."""

        if (
            not isinstance(self.timeout_seconds, Real)
            or isinstance(self.timeout_seconds, bool)
        ):
            raise TypeError("timeout_seconds must be a real number")

        if not isfinite(self.timeout_seconds):
            raise ValueError("timeout_seconds must be a finite number")

        if self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than zero")

    def fetch_historical_weather(
        self,
        destination: Destination,
        period: TravelPeriod,
    ) -> object:
        """Fetch daily ERA5 historical weather for a destination and period."""

        query: dict[str, str | int | float] = {
            "latitude": destination.coordinates.latitude,
            "longitude": destination.coordinates.longitude,
            "start_date": period.start_date.isoformat(),
            "end_date": period.end_date.isoformat(),
            "daily": ",".join(_DAILY_VARIABLES),
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
            "timeformat": "iso8601",
            "timezone": "auto",
            "models": "era5",
        }

        try:
            response = self.transport.get_json(
                url=_ARCHIVE_URL,
                headers={},
                query=query,
                timeout_seconds=self.timeout_seconds,
            )
        except JsonHttpDecodeError as exc:
            raise ProviderResponseError(
                "Open-Meteo returned invalid JSON"
            ) from exc
        except Exception as exc:
            raise ProviderUnavailableError(
                "Open-Meteo weather request failed"
            ) from exc

        if 200 <= response.status_code < 300:
            return response.payload

        if response.status_code == 429:
            raise ProviderRateLimitError(
                "Open-Meteo rate limit exceeded"
            )

        if 400 <= response.status_code < 500:
            raise ProviderResponseError(
                "Open-Meteo rejected the request"
            )

        if 500 <= response.status_code < 600:
            raise ProviderUnavailableError(
                "Open-Meteo service unavailable"
            )

        raise ProviderResponseError(
            "Open-Meteo returned unexpected HTTP status"
        )


@dataclass(slots=True)
class OpenMeteoHistoricalWeatherProvider:
    """Normalize historical weather returned by an injected Open-Meteo client."""

    client: OpenMeteoHistoricalWeatherClient

    def get_historical_weather(
        self,
        destination: Destination,
        period: TravelPeriod,
    ) -> tuple[WeatherObservation, ...]:
        """Return normalized historical observations for the requested period."""

        try:
            payload = self.client.fetch_historical_weather(destination, period)
            return normalize_open_meteo_historical_weather(payload)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                "Open-Meteo weather request failed"
            ) from exc


def normalize_open_meteo_historical_weather(
    payload: object,
) -> tuple[WeatherObservation, ...]:
    """Normalize a raw Open-Meteo daily response into domain observations."""

    if not isinstance(payload, Mapping):
        raise ProviderResponseError(
            "Open-Meteo response must be an object"
        )

    daily = payload.get("daily")

    if not isinstance(daily, Mapping):
        raise ProviderResponseError(
            "Open-Meteo response daily must be an object"
        )

    arrays = _extract_daily_arrays(daily)
    _validate_daily_units(payload)

    lengths = {len(values) for values in arrays.values()}

    if len(lengths) != 1:
        raise ProviderResponseError(
            "Open-Meteo daily arrays must have equal lengths"
        )

    observations: list[WeatherObservation] = []
    previous_date: date | None = None

    for raw_date, temperature, humidity, precipitation in zip(
        arrays["time"],
        arrays["temperature_2m_mean"],
        arrays["relative_humidity_2m_mean"],
        arrays["precipitation_sum"],
        strict=True,
    ):
        observed_on = _parse_observation_date(raw_date)

        if previous_date is not None and observed_on <= previous_date:
            raise ProviderResponseError(
                "Open-Meteo daily dates must be strictly increasing"
            )

        observations.append(
            _build_observation(
                observed_on=observed_on,
                temperature=temperature,
                humidity=humidity,
                precipitation=precipitation,
            )
        )
        previous_date = observed_on

    return tuple(observations)


def _extract_daily_arrays(
    daily: Mapping[object, object],
) -> dict[str, list[object]]:
    """Extract all required list-shaped daily response fields."""

    arrays: dict[str, list[object]] = {}

    for field in _REQUIRED_DAILY_FIELDS:
        values = daily.get(field)

        if not isinstance(values, list):
            raise ProviderResponseError(
                f"Open-Meteo daily {field} must be a list"
            )

        arrays[field] = values

    return arrays


def _validate_daily_units(payload: Mapping[object, object]) -> None:
    """Reject explicitly reported units outside Solara's requested contract."""

    if "daily_units" not in payload:
        return

    daily_units = payload["daily_units"]

    if not isinstance(daily_units, Mapping):
        raise ProviderResponseError(
            "Open-Meteo daily units must be an object"
        )

    if any(
        daily_units.get(field) != expected
        for field, expected in _EXPECTED_DAILY_UNITS.items()
    ):
        raise ProviderResponseError(
            "Open-Meteo daily units do not match the requested units"
        )


def _parse_observation_date(value: object) -> date:
    """Parse one strict ISO calendar date from provider data."""

    if not isinstance(value, str) or len(value) != 10:
        raise ProviderResponseError(
            "Open-Meteo daily time must be an ISO calendar date"
        )

    try:
        observed_on = date.fromisoformat(value)
    except ValueError as exc:
        raise ProviderResponseError(
            "Open-Meteo daily time must be an ISO calendar date"
        ) from exc

    if observed_on.isoformat() != value:
        raise ProviderResponseError(
            "Open-Meteo daily time must be an ISO calendar date"
        )

    return observed_on


def _build_observation(
    *,
    observed_on: date,
    temperature: object,
    humidity: object,
    precipitation: object,
) -> WeatherObservation:
    """Build a domain observation and normalize domain validation failures."""

    try:
        return WeatherObservation(
            observed_on=observed_on,
            temperature_celsius=temperature,  # type: ignore[arg-type]
            relative_humidity_percent=humidity,  # type: ignore[arg-type]
            precipitation_mm=precipitation,  # type: ignore[arg-type]
        )
    except (TypeError, ValueError) as exc:
        raise ProviderResponseError(
            "Open-Meteo daily weather values are invalid"
        ) from exc
