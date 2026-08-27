"""Provider-independent values for configuring a realistic itinerary."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates


class Pace(StrEnum):
    """Traveller-selected scheduling rhythm."""

    RELAXED = "relaxed"
    BALANCED = "balanced"
    ACTIVE = "active"


class TravelRequirement(StrEnum):
    """Practical, traveller-declared planning considerations."""

    WHEELCHAIR_ACCESS = "wheelchair_access"
    REDUCED_WALKING = "reduced_walking"
    MOBILITY_ASSISTANCE = "mobility_assistance"
    FREQUENT_BREAKS = "frequent_breaks"
    STROLLER = "stroller"
    SLOWER_TRANSITIONS = "slower_transitions"


class DayPeriod(StrEnum):
    """Simple traveller-facing parts of a day."""

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class DurationProvenance(StrEnum):
    """Trust source attached to a planning duration."""

    PROVIDER = "provider"
    CATEGORY_HEURISTIC = "category_heuristic"
    TRAVELLER_SELECTED = "traveller_selected"


class EstimateConfidence(StrEnum):
    """Coarse confidence for an explicitly approximate duration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AccessibilityStatus(StrEnum):
    """Truthful accessibility knowledge state."""

    CONFIRMED = "confirmed"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class TravelMode(StrEnum):
    """Provider-neutral modes usable for route planning."""

    FLIGHT = "flight"
    RAIL = "rail"
    ROAD = "road"
    FERRY = "ferry"
    OTHER = "other"


class FeasibilityLevel(StrEnum):
    """Calm traveller-facing day-load states."""

    RELAXED = "relaxed"
    COMFORTABLE = "comfortable"
    FULL = "full"
    VERY_FULL = "very_full"


@dataclass(frozen=True, slots=True)
class TravellerParty:
    """Composition of a travelling group without sensitive medical data."""

    adults: int = 1
    young_adults: int = 0
    children: int = 0
    infants: int = 0
    seniors: int = 0

    def __post_init__(self) -> None:
        values = (self.adults, self.young_adults, self.children, self.infants, self.seniors)
        if any(type(value) is not int for value in values):
            raise TypeError("traveller counts must be integers")
        if any(value < 0 for value in values):
            raise ValueError("traveller counts must not be negative")
        if self.total == 0:
            raise ValueError("at least one traveller is required")
        if self.total > 20:
            raise ValueError("traveller party must contain at most 20 people")

    @property
    def total(self) -> int:
        """Return the coherent total across party categories."""

        return self.adults + self.young_adults + self.children + self.infants + self.seniors


@dataclass(frozen=True, slots=True)
class TravellerProfile:
    """Structured inputs that affect itinerary feasibility."""

    party: TravellerParty
    pace: Pace = Pace.BALANCED
    requirements: tuple[TravelRequirement, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.party, TravellerParty):
            raise TypeError("party must be TravellerParty")
        if not isinstance(self.pace, Pace):
            raise TypeError("pace must be Pace")
        if not isinstance(self.requirements, tuple):
            raise TypeError("requirements must be a tuple")
        if not all(isinstance(item, TravelRequirement) for item in self.requirements):
            raise TypeError("requirements must contain TravelRequirement values")
        if len(set(self.requirements)) != len(self.requirements):
            raise ValueError("requirements must not contain duplicates")


@dataclass(frozen=True, slots=True)
class DurationEstimate:
    """An honest duration range with provenance instead of fake precision."""

    minimum_minutes: int
    maximum_minutes: int
    provenance: DurationProvenance
    confidence: EstimateConfidence

    def __post_init__(self) -> None:
        if type(self.minimum_minutes) is not int or type(self.maximum_minutes) is not int:
            raise TypeError("duration minutes must be integers")
        if self.minimum_minutes <= 0 or self.maximum_minutes <= 0:
            raise ValueError("duration minutes must be positive")
        if self.minimum_minutes > self.maximum_minutes:
            raise ValueError("minimum duration must not exceed maximum duration")
        if not isinstance(self.provenance, DurationProvenance):
            raise TypeError("provenance must be DurationProvenance")
        if not isinstance(self.confidence, EstimateConfidence):
            raise TypeError("confidence must be EstimateConfidence")

    @property
    def typical_minutes(self) -> int:
        """Return the deterministic midpoint used only for planning calculations."""

        return (self.minimum_minutes + self.maximum_minutes + 1) // 2


@dataclass(frozen=True, slots=True)
class DestinationStay:
    """A validated destination and its positive trip-day allocation."""

    destination: Destination
    days: int

    def __post_init__(self) -> None:
        if not isinstance(self.destination, Destination):
            raise TypeError("destination must be Destination")
        if type(self.days) is not int:
            raise TypeError("days must be an integer")
        if self.days <= 0:
            raise ValueError("destination allocation must be positive")


@dataclass(frozen=True, slots=True)
class ActivityOption:
    """A provider-backed activity option before it is placed into a day."""

    identity: str
    name: str
    destination: Destination
    category: str
    coordinates: GeoCoordinates | None
    duration: DurationEstimate | None
    accessibility: AccessibilityStatus = AccessibilityStatus.UNKNOWN

    def __post_init__(self) -> None:
        for field_name in ("identity", "name", "category"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank")
        if not isinstance(self.destination, Destination):
            raise TypeError("destination must be Destination")
        if self.coordinates is not None and not isinstance(self.coordinates, GeoCoordinates):
            raise TypeError("coordinates must be GeoCoordinates or None")
        if self.duration is not None and not isinstance(self.duration, DurationEstimate):
            raise TypeError("duration must be DurationEstimate or None")
        if not isinstance(self.accessibility, AccessibilityStatus):
            raise TypeError("accessibility must be AccessibilityStatus")


@dataclass(frozen=True, slots=True)
class ItineraryActivity:
    """One trusted selectable place arranged into a day and period."""

    identity: str
    name: str
    destination: Destination
    category: str
    coordinates: GeoCoordinates | None
    duration: DurationEstimate | None
    day_number: int
    period: DayPeriod
    order: int
    accessibility: AccessibilityStatus = AccessibilityStatus.UNKNOWN

    def __post_init__(self) -> None:
        for field_name in ("identity", "name", "category"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank")
        if not isinstance(self.destination, Destination):
            raise TypeError("destination must be Destination")
        if self.coordinates is not None and not isinstance(self.coordinates, GeoCoordinates):
            raise TypeError("coordinates must be GeoCoordinates or None")
        if self.duration is not None and not isinstance(self.duration, DurationEstimate):
            raise TypeError("duration must be DurationEstimate or None")
        if type(self.day_number) is not int or self.day_number <= 0:
            raise ValueError("day_number must be a positive integer")
        if not isinstance(self.period, DayPeriod):
            raise TypeError("period must be DayPeriod")
        if type(self.order) is not int or self.order < 0:
            raise ValueError("order must be a non-negative integer")
        if not isinstance(self.accessibility, AccessibilityStatus):
            raise TypeError("accessibility must be AccessibilityStatus")


@dataclass(frozen=True, slots=True)
class TravelLeg:
    """A first-class transition that consumes itinerary time."""

    origin: Destination
    destination: Destination
    mode: TravelMode
    duration: DurationEstimate | None = None
    planning_buffer_minutes: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.origin, Destination) or not isinstance(
            self.destination, Destination
        ):
            raise TypeError("travel-leg endpoints must be Destination values")
        if self.origin == self.destination:
            raise ValueError("travel-leg endpoints must be different")
        if not isinstance(self.mode, TravelMode):
            raise TypeError("mode must be TravelMode")
        if self.duration is not None and not isinstance(self.duration, DurationEstimate):
            raise TypeError("duration must be DurationEstimate or None")
        if type(self.planning_buffer_minutes) is not int:
            raise TypeError("planning_buffer_minutes must be an integer")
        if self.planning_buffer_minutes < 0:
            raise ValueError("planning_buffer_minutes must not be negative")


@dataclass(frozen=True, slots=True)
class ItineraryDay:
    """One destination day with ordered activities and an optional inbound leg."""

    number: int
    destination: Destination
    activities: tuple[ItineraryActivity, ...] = ()
    inbound_travel_leg: TravelLeg | None = None

    def __post_init__(self) -> None:
        if type(self.number) is not int or self.number <= 0:
            raise ValueError("day number must be a positive integer")
        if not isinstance(self.destination, Destination):
            raise TypeError("destination must be Destination")
        if not isinstance(self.activities, tuple):
            raise TypeError("activities must be a tuple")
        if not all(isinstance(item, ItineraryActivity) for item in self.activities):
            raise TypeError("activities must contain ItineraryActivity values")
        if any(
            item.day_number != self.number or item.destination != self.destination
            for item in self.activities
        ):
            raise ValueError("activities must belong to this day and destination")
        identities = [item.identity for item in self.activities]
        if len(set(identities)) != len(identities):
            raise ValueError("a day must not contain duplicate activities")
        ordering = [(item.period, item.order) for item in self.activities]
        if len(set(ordering)) != len(ordering):
            raise ValueError("activity order must be unique within each period")
        if self.inbound_travel_leg is not None:
            if not isinstance(self.inbound_travel_leg, TravelLeg):
                raise TypeError("inbound_travel_leg must be TravelLeg or None")
            if self.inbound_travel_leg.destination != self.destination:
                raise ValueError("inbound travel leg must arrive at the day's destination")


@dataclass(frozen=True, slots=True)
class Itinerary:
    """An active-session itinerary whose allocation matches its date range."""

    start_date: date
    end_date: date
    traveller_profile: TravellerProfile
    stays: tuple[DestinationStay, ...]
    days: tuple[ItineraryDay, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.start_date, date) or not isinstance(self.end_date, date):
            raise TypeError("itinerary dates must be date values")
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        if not isinstance(self.traveller_profile, TravellerProfile):
            raise TypeError("traveller_profile must be TravellerProfile")
        if not isinstance(self.stays, tuple) or not self.stays:
            raise ValueError("stays must be a non-empty tuple")
        if not all(isinstance(stay, DestinationStay) for stay in self.stays):
            raise TypeError("stays must contain DestinationStay values")
        if not isinstance(self.days, tuple):
            raise TypeError("days must be a tuple")
        duration = (self.end_date - self.start_date).days + 1
        if sum(stay.days for stay in self.stays) != duration:
            raise ValueError("destination allocations must equal trip duration")
        if len(self.days) != duration:
            raise ValueError("itinerary must contain one day per trip date")
        if tuple(day.number for day in self.days) != tuple(range(1, duration + 1)):
            raise ValueError("itinerary days must be sequential")
        expected_destinations = tuple(
            stay.destination for stay in self.stays for _ in range(stay.days)
        )
        if tuple(day.destination for day in self.days) != expected_destinations:
            raise ValueError("itinerary days must follow destination allocations")


@dataclass(frozen=True, slots=True)
class FeasibilityAssessment:
    """Transparent deterministic result for one itinerary day."""

    day_number: int
    level: FeasibilityLevel
    occupied_minutes: int
    available_minutes: int
    remaining_minutes: int
    buffer_minutes: int
    warnings: tuple[str, ...] = ()
    hard_violations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.day_number) is not int or self.day_number <= 0:
            raise ValueError("day_number must be a positive integer")
        if not isinstance(self.level, FeasibilityLevel):
            raise TypeError("level must be FeasibilityLevel")
        for field_name in (
            "occupied_minutes",
            "available_minutes",
            "remaining_minutes",
            "buffer_minutes",
        ):
            if type(getattr(self, field_name)) is not int:
                raise TypeError(f"{field_name} must be an integer")
        if self.occupied_minutes < 0 or self.available_minutes <= 0 or self.buffer_minutes < 0:
            raise ValueError("feasibility minute values are inconsistent")
        if self.remaining_minutes != self.available_minutes - self.occupied_minutes:
            raise ValueError("remaining_minutes must equal available minus occupied")
        if not isinstance(self.warnings, tuple) or not all(
            isinstance(item, str) and item for item in self.warnings
        ):
            raise TypeError("warnings must be a tuple of non-blank strings")
        if not isinstance(self.hard_violations, tuple) or not all(
            isinstance(item, str) and item for item in self.hard_violations
        ):
            raise TypeError("hard_violations must be a tuple of non-blank strings")
