"""Attraction entities used by the Solara travel domain."""

from dataclasses import dataclass

from solara_travel.domain.geography import GeoCoordinates


@dataclass(frozen=True, slots=True)
class Attraction:
    """An immutable attraction within a travel destination.

    Attractions are represented using Solara-owned values rather than
    provider-specific place objects or identifiers.
    """

    name: str
    category: str
    coordinates: GeoCoordinates

    def __post_init__(self) -> None:
        """Validate attraction identity values."""

        if not isinstance(self.name, str) or not isinstance(self.category, str):
            raise TypeError("attraction name and category must be strings")

        if not self.name.strip():
            raise ValueError("attraction name must not be blank")

        if not self.category.strip():
            raise ValueError("attraction category must not be blank")

        if not isinstance(self.coordinates, GeoCoordinates):
            raise TypeError("attraction coordinates must be GeoCoordinates")