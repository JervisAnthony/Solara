"""Destination entities used by the Solara travel domain."""

from dataclasses import dataclass

from solara_travel.domain.geography import GeoCoordinates


@dataclass(frozen=True, slots=True)
class Destination:
    """An immutable travel destination.

    A destination is identified here by a human-readable name, country, and
    geographic coordinates. Provider-specific identifiers are intentionally
    excluded from the core domain model.
    """

    name: str
    country: str
    coordinates: GeoCoordinates

    def __post_init__(self) -> None:
        """Validate destination identity values."""

        if not isinstance(self.name, str) or not isinstance(self.country, str):
            raise TypeError("destination name and country must be strings")

        if not self.name.strip():
            raise ValueError("destination name must not be blank")

        if not self.country.strip():
            raise ValueError("destination country must not be blank")

        if not isinstance(self.coordinates, GeoCoordinates):
            raise TypeError("destination coordinates must be GeoCoordinates")