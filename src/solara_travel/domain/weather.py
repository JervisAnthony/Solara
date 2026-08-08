"""Normalized weather-domain values used by Solara."""

from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from numbers import Real


@dataclass(frozen=True, slots=True)
class WeatherObservation:
    """An immutable normalized daily weather observation."""

    observed_on: date
    temperature_celsius: float
    relative_humidity_percent: float
    precipitation_mm: float

    def __post_init__(self) -> None:
        """Validate normalized weather evidence."""

        if (
            not isinstance(self.observed_on, date)
            or isinstance(self.observed_on, datetime)
        ):
            raise TypeError("observed_on must be a date")

        if (
            not isinstance(self.temperature_celsius, Real)
            or isinstance(self.temperature_celsius, bool)
        ):
            raise TypeError("temperature_celsius must be a real number")

        if not isfinite(self.temperature_celsius):
            raise ValueError("temperature_celsius must be a finite number")

        if not -100.0 <= self.temperature_celsius <= 60.0:
            raise ValueError(
                "temperature_celsius must be between -100 and 60"
            )

        if (
            not isinstance(self.relative_humidity_percent, Real)
            or isinstance(self.relative_humidity_percent, bool)
        ):
            raise TypeError(
                "relative_humidity_percent must be a real number"
            )

        if not isfinite(self.relative_humidity_percent):
            raise ValueError(
                "relative_humidity_percent must be a finite number"
            )

        if not 0.0 <= self.relative_humidity_percent <= 100.0:
            raise ValueError(
                "relative_humidity_percent must be between 0 and 100"
            )

        if (
            not isinstance(self.precipitation_mm, Real)
            or isinstance(self.precipitation_mm, bool)
        ):
            raise TypeError("precipitation_mm must be a real number")

        if not isfinite(self.precipitation_mm):
            raise ValueError("precipitation_mm must be a finite number")

        if self.precipitation_mm < 0.0:
            raise ValueError("precipitation_mm must not be negative")