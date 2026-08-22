"""Destination entities and queries used by the Solara travel domain."""

from dataclasses import dataclass

from solara_travel.domain.geography import GeoCoordinates

DESTINATION_QUERY_MAX_LENGTH = 120


@dataclass(frozen=True, slots=True)
class DestinationQuery:
    """A normalized, provider-independent destination entered by a traveller."""

    value: str

    def __post_init__(self) -> None:
        """Normalize surrounding whitespace and reject unsafe query values."""

        if not isinstance(self.value, str):
            raise TypeError("destination query must be a string")

        normalized = self.value.strip()
        if not normalized:
            raise ValueError("destination query must not be blank")
        if len(normalized) > DESTINATION_QUERY_MAX_LENGTH:
            raise ValueError(
                f"destination query must not exceed {DESTINATION_QUERY_MAX_LENGTH} characters"
            )
        if any(not character.isprintable() for character in normalized):
            raise ValueError("destination query must not contain control characters")

        object.__setattr__(self, "value", normalized)


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
