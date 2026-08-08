"""Climate-comfort domain values used by Solara."""

from dataclasses import dataclass
from math import isfinite
from numbers import Real


@dataclass(frozen=True, slots=True)
class TemperatureComfortRange:
    """An immutable preferred temperature range and degradation tolerance."""

    minimum_celsius: float
    maximum_celsius: float
    tolerance_celsius: float

    def __post_init__(self) -> None:
        """Validate the configured comfort boundaries and tolerance."""

        if (
            not isinstance(self.minimum_celsius, Real)
            or isinstance(self.minimum_celsius, bool)
        ):
            raise TypeError("minimum_celsius must be a real number")

        if not isfinite(self.minimum_celsius):
            raise ValueError("minimum_celsius must be a finite number")

        if not -100.0 <= self.minimum_celsius <= 60.0:
            raise ValueError("minimum_celsius must be between -100 and 60")

        if (
            not isinstance(self.maximum_celsius, Real)
            or isinstance(self.maximum_celsius, bool)
        ):
            raise TypeError("maximum_celsius must be a real number")

        if not isfinite(self.maximum_celsius):
            raise ValueError("maximum_celsius must be a finite number")

        if not -100.0 <= self.maximum_celsius <= 60.0:
            raise ValueError("maximum_celsius must be between -100 and 60")

        if self.minimum_celsius > self.maximum_celsius:
            raise ValueError(
                "minimum_celsius must not exceed maximum_celsius"
            )

        if (
            not isinstance(self.tolerance_celsius, Real)
            or isinstance(self.tolerance_celsius, bool)
        ):
            raise TypeError("tolerance_celsius must be a real number")

        if not isfinite(self.tolerance_celsius):
            raise ValueError("tolerance_celsius must be a finite number")

        if self.tolerance_celsius <= 0.0:
            raise ValueError("tolerance_celsius must be greater than zero")