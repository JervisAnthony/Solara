"""Geographic value objects used by the Solara travel domain."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class GeoCoordinates:
    """Immutable geographic coordinates expressed in decimal degrees.

    Latitude is constrained to the inclusive range -90 to 90 degrees.
    Longitude is constrained to the inclusive range -180 to 180 degrees.
    """

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        """Validate that the coordinate represents a finite geographic point."""

        if not isfinite(self.latitude) or not isfinite(self.longitude):
            raise ValueError("coordinates must be finite numbers")

        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90 degrees")

        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180 degrees")