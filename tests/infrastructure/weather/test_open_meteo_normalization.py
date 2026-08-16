"""Tests for normalizing Open-Meteo daily historical weather."""

from copy import deepcopy
from datetime import date

import pytest

from solara_travel.domain.weather import WeatherObservation
from solara_travel.infrastructure.weather.open_meteo import (
    normalize_open_meteo_historical_weather,
)
from solara_travel.ports.errors import ProviderResponseError


def _payload() -> dict[str, object]:
    """Return a representative two-day Open-Meteo archive response."""

    return {
        "daily_units": {
            "time": "iso8601",
            "temperature_2m_mean": "°C",
            "relative_humidity_2m_mean": "%",
            "precipitation_sum": "mm",
        },
        "daily": {
            "time": ["2020-04-01", "2020-04-02"],
            "temperature_2m_mean": [13.2, 14.1],
            "relative_humidity_2m_mean": [61.0, 58.0],
            "precipitation_sum": [0.4, 0.0],
        },
    }


def _daily(payload: dict[str, object]) -> dict[str, object]:
    daily = payload["daily"]
    assert isinstance(daily, dict)
    return daily


def test_normalization_returns_ordered_observation_tuple() -> None:
    """Valid daily values should become ordered immutable domain evidence."""

    result = normalize_open_meteo_historical_weather(_payload())

    assert result == (
        WeatherObservation(
            observed_on=date(2020, 4, 1),
            temperature_celsius=13.2,
            relative_humidity_percent=61.0,
            precipitation_mm=0.4,
        ),
        WeatherObservation(
            observed_on=date(2020, 4, 2),
            temperature_celsius=14.1,
            relative_humidity_percent=58.0,
            precipitation_mm=0.0,
        ),
    )
    assert isinstance(result, tuple)


def test_normalization_returns_empty_tuple_for_empty_arrays() -> None:
    """Four present empty arrays should represent no observations."""

    payload = {"daily": {field: [] for field in (
        "time",
        "temperature_2m_mean",
        "relative_humidity_2m_mean",
        "precipitation_sum",
    )}}

    assert normalize_open_meteo_historical_weather(payload) == ()


@pytest.mark.parametrize("payload", [None, [], "weather", 42])
def test_normalization_rejects_non_object_response(payload: object) -> None:
    """The provider response must be object-shaped."""

    with pytest.raises(ProviderResponseError, match="response must be an object"):
        normalize_open_meteo_historical_weather(payload)


@pytest.mark.parametrize("daily", [None, [], "daily", 42])
def test_normalization_rejects_invalid_daily_object(daily: object) -> None:
    """The required daily member must be object-shaped."""

    payload: dict[str, object] = {} if daily is None else {"daily": daily}

    with pytest.raises(ProviderResponseError, match="daily must be an object"):
        normalize_open_meteo_historical_weather(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (field, value)
        for field in (
            "time",
            "temperature_2m_mean",
            "relative_humidity_2m_mean",
            "precipitation_sum",
        )
        for value in (None, 1, {}, "values")
    ],
)
def test_normalization_rejects_missing_or_non_list_daily_array(
    field: str,
    value: object,
) -> None:
    """Every required daily field must be represented by a list."""

    payload = _payload()
    daily = _daily(payload)

    if value is None:
        del daily[field]
    else:
        daily[field] = value

    with pytest.raises(ProviderResponseError, match=f"daily {field} must be a list"):
        normalize_open_meteo_historical_weather(payload)


@pytest.mark.parametrize(
    "field",
    [
        "temperature_2m_mean",
        "relative_humidity_2m_mean",
        "precipitation_sum",
    ],
)
def test_normalization_rejects_mismatched_array_lengths(field: str) -> None:
    """Daily arrays must align row-for-row with the time array."""

    payload = _payload()
    _daily(payload)[field] = [1.0]

    with pytest.raises(ProviderResponseError, match="equal lengths"):
        normalize_open_meteo_historical_weather(payload)


@pytest.mark.parametrize(
    "raw_date",
    [None, 20200401, "", "2020-4-1", "2020-04-01T12:00", "2020-02-30"],
)
def test_normalization_rejects_invalid_dates(raw_date: object) -> None:
    """Provider times must be strict, possible ISO calendar dates."""

    payload = _payload()
    _daily(payload)["time"] = [raw_date, "2020-04-02"]

    with pytest.raises(ProviderResponseError, match="ISO calendar date"):
        normalize_open_meteo_historical_weather(payload)


def test_normalization_rejects_non_calendar_iso_date_form() -> None:
    """Other date.fromisoformat forms must not enter the calendar-date contract."""

    payload = _payload()
    _daily(payload)["time"] = ["2020-W01-1", "2020-04-02"]

    with pytest.raises(ProviderResponseError, match="ISO calendar date"):
        normalize_open_meteo_historical_weather(payload)


@pytest.mark.parametrize(
    "dates",
    [
        ["2020-04-01", "2020-04-01"],
        ["2020-04-02", "2020-04-01"],
    ],
)
def test_normalization_rejects_duplicate_or_descending_dates(
    dates: list[str],
) -> None:
    """Historical evidence must already be strictly increasing."""

    payload = _payload()
    _daily(payload)["time"] = dates

    with pytest.raises(ProviderResponseError, match="strictly increasing"):
        normalize_open_meteo_historical_weather(payload)


@pytest.mark.parametrize(
    "temperature",
    ["13.2", True, None, float("nan"), float("inf"), -100.1, 60.1],
)
def test_normalization_rejects_invalid_temperature(temperature: object) -> None:
    """Invalid temperatures should become provider-response failures."""

    payload = _payload()
    _daily(payload)["temperature_2m_mean"] = [temperature, 14.1]

    with pytest.raises(ProviderResponseError, match="weather values are invalid"):
        normalize_open_meteo_historical_weather(payload)


@pytest.mark.parametrize(
    "humidity",
    ["61", True, None, float("nan"), float("inf"), -0.1, 100.1],
)
def test_normalization_rejects_invalid_humidity(humidity: object) -> None:
    """Invalid humidity should become provider-response failures."""

    payload = _payload()
    _daily(payload)["relative_humidity_2m_mean"] = [humidity, 58.0]

    with pytest.raises(ProviderResponseError, match="weather values are invalid"):
        normalize_open_meteo_historical_weather(payload)


@pytest.mark.parametrize(
    "precipitation",
    ["0.4", True, None, float("nan"), float("inf"), -0.1],
)
def test_normalization_rejects_invalid_precipitation(precipitation: object) -> None:
    """Invalid precipitation should become provider-response failures."""

    payload = _payload()
    _daily(payload)["precipitation_sum"] = [precipitation, 0.0]

    with pytest.raises(ProviderResponseError, match="weather values are invalid"):
        normalize_open_meteo_historical_weather(payload)


def test_normalization_preserves_valid_zero_values() -> None:
    """Zero temperature, humidity, and precipitation are legitimate evidence."""

    payload = _payload()
    daily = _daily(payload)
    daily["temperature_2m_mean"] = [0.0, 0.0]
    daily["relative_humidity_2m_mean"] = [0.0, 0.0]
    daily["precipitation_sum"] = [0.0, 0.0]

    result = normalize_open_meteo_historical_weather(payload)

    assert result[0].temperature_celsius == 0.0
    assert result[0].relative_humidity_percent == 0.0
    assert result[0].precipitation_mm == 0.0


def test_normalization_rejects_non_object_daily_units() -> None:
    """Reported units must be object-shaped when present."""

    payload = _payload()
    payload["daily_units"] = "metric"

    with pytest.raises(ProviderResponseError, match="daily units must be an object"):
        normalize_open_meteo_historical_weather(payload)


@pytest.mark.parametrize(
    ("field", "unit"),
    [
        ("time", "unixtime"),
        ("temperature_2m_mean", "°F"),
        ("relative_humidity_2m_mean", "fraction"),
        ("precipitation_sum", "inch"),
    ],
)
def test_normalization_rejects_unrequested_units(field: str, unit: str) -> None:
    """Explicit alternate provider units must never be treated as normalized values."""

    payload = deepcopy(_payload())
    units = payload["daily_units"]
    assert isinstance(units, dict)
    units[field] = unit

    with pytest.raises(ProviderResponseError, match="do not match"):
        normalize_open_meteo_historical_weather(payload)
