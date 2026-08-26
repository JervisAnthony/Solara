"""Provider-independent geographic scope values for travel discovery."""

from dataclasses import dataclass
from enum import StrEnum

from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates


class TravelScopeKind(StrEnum):
    """Supported geographic meanings for traveller-entered place text."""

    LOCALITY = "locality"
    REGION = "region"
    COUNTRY = "country"


@dataclass(frozen=True, slots=True)
class GeoViewport:
    """Provider-independent rectangular bounds used as defensive metadata."""

    southwest: GeoCoordinates
    northeast: GeoCoordinates

    def __post_init__(self) -> None:
        if not isinstance(self.southwest, GeoCoordinates):
            raise TypeError("southwest must be GeoCoordinates")
        if not isinstance(self.northeast, GeoCoordinates):
            raise TypeError("northeast must be GeoCoordinates")
        if self.southwest.latitude > self.northeast.latitude:
            raise ValueError("viewport latitude bounds are inverted")

    def contains(self, coordinates: GeoCoordinates) -> bool:
        """Return whether coordinates fall within these bounds, including dateline spans."""

        if not isinstance(coordinates, GeoCoordinates):
            raise TypeError("coordinates must be GeoCoordinates")
        latitude_matches = (
            self.southwest.latitude <= coordinates.latitude <= self.northeast.latitude
        )
        if self.southwest.longitude <= self.northeast.longitude:
            longitude_matches = (
                self.southwest.longitude <= coordinates.longitude <= self.northeast.longitude
            )
        else:
            longitude_matches = (
                coordinates.longitude >= self.southwest.longitude
                or coordinates.longitude <= self.northeast.longitude
            )
        return latitude_matches and longitude_matches


@dataclass(frozen=True, slots=True)
class TravelScope:
    """Normalized geographic meaning without provider identifiers or fields."""

    display_name: str
    kind: TravelScopeKind
    country_name: str | None
    country_code: str | None
    canonical_name: str | None = None
    center: GeoCoordinates | None = None
    viewport: GeoViewport | None = None
    containing_regions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("display_name",):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")
            normalized = value.strip()
            if not normalized:
                raise ValueError(f"{field_name} must not be blank")
            object.__setattr__(self, field_name, normalized)
        if not isinstance(self.kind, TravelScopeKind):
            raise TypeError("kind must be TravelScopeKind")
        for field_name in ("country_name", "country_code"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string or None")
            if isinstance(value, str) and not value.strip():
                raise ValueError(f"{field_name} must not be blank")
            if isinstance(value, str):
                object.__setattr__(self, field_name, value.strip())
        if (self.country_name is None) != (self.country_code is None):
            raise ValueError("country_name and country_code must both be set or both be None")
        if self.kind is not TravelScopeKind.REGION and self.country_name is None:
            raise ValueError("country and locality scopes must include country identity")
        if self.country_code is not None:
            object.__setattr__(self, "country_code", self.country_code.upper())
        if self.canonical_name is None:
            object.__setattr__(self, "canonical_name", self.display_name)
        elif not isinstance(self.canonical_name, str):
            raise TypeError("canonical_name must be a string or None")
        elif not self.canonical_name.strip():
            raise ValueError("canonical_name must not be blank")
        else:
            object.__setattr__(self, "canonical_name", self.canonical_name.strip())
        if self.center is not None and not isinstance(self.center, GeoCoordinates):
            raise TypeError("center must be GeoCoordinates or None")
        if self.viewport is not None and not isinstance(self.viewport, GeoViewport):
            raise TypeError("viewport must be GeoViewport or None")
        if not isinstance(self.containing_regions, tuple):
            raise TypeError("containing_regions must be a tuple")
        if not all(
            isinstance(region, str) and region.strip() for region in self.containing_regions
        ):
            raise ValueError("containing_regions must contain non-blank strings")
        normalized_regions = tuple(region.strip() for region in self.containing_regions)
        if len({region.casefold() for region in normalized_regions}) != len(normalized_regions):
            raise ValueError("containing_regions must not contain duplicates")
        object.__setattr__(self, "containing_regions", normalized_regions)

    def to_destination(self) -> Destination:
        """Convert a validated locality scope into a scoreable destination."""

        if self.kind is not TravelScopeKind.LOCALITY:
            raise ValueError("only locality scopes can become destinations")
        if self.center is None:
            raise ValueError("locality scope must include center coordinates")
        assert self.country_name is not None
        return Destination(self.canonical_name or self.display_name, self.country_name, self.center)

    def contains(self, candidate: "TravelScope") -> bool:
        """Return whether one validated locality belongs to this broad scope."""

        if not isinstance(candidate, TravelScope):
            raise TypeError("candidate must be TravelScope")
        if candidate.kind is not TravelScopeKind.LOCALITY:
            return False
        if self.kind is TravelScopeKind.COUNTRY:
            assert self.country_code is not None
            return candidate.country_code == self.country_code
        if self.kind is not TravelScopeKind.REGION:
            return False
        if self.country_code is not None and candidate.country_code != self.country_code:
            return False
        expected = {
            self.display_name.casefold(),
            (self.canonical_name or self.display_name).casefold(),
        }
        if any(region.casefold() in expected for region in candidate.containing_regions):
            return True
        return (
            self.viewport is not None
            and candidate.center is not None
            and self.viewport.contains(candidate.center)
        )


@dataclass(frozen=True, slots=True)
class TravelScopeSuggestion:
    """Small provider-independent prediction shown in the planner."""

    display_name: str
    kind: TravelScopeKind

    def __post_init__(self) -> None:
        if not isinstance(self.display_name, str):
            raise TypeError("display_name must be a string")
        normalized = self.display_name.strip()
        if not normalized:
            raise ValueError("display_name must not be blank")
        if not isinstance(self.kind, TravelScopeKind):
            raise TypeError("kind must be TravelScopeKind")
        object.__setattr__(self, "display_name", normalized)
