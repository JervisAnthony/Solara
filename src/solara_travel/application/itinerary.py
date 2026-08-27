"""Deterministic application services for the active-session Itinerary Studio."""

from dataclasses import dataclass, replace
from datetime import date
from hashlib import sha256
from typing import ClassVar

from solara_travel.domain import (
    AccessibilityStatus,
    ActivityOption,
    DayPeriod,
    Destination,
    DestinationStay,
    DurationEstimate,
    DurationProvenance,
    EstimateConfidence,
    FeasibilityAssessment,
    FeasibilityLevel,
    Itinerary,
    ItineraryActivity,
    ItineraryDay,
    Pace,
    TravelLeg,
    TravellerProfile,
    TravelRequirement,
)
from solara_travel.ports.places import AttractionDiscoveryPort

MAX_ACTIVITY_OPTIONS = 12

_CATEGORY_DURATIONS: tuple[tuple[tuple[str, ...], tuple[int, int]], ...] = (
    (("museum", "gallery", "temple", "church", "cultural"), (60, 120)),
    (("beach", "park", "nature", "garden", "hiking"), (120, 180)),
    (("market", "food", "restaurant"), (90, 120)),
    (("night", "entertainment"), (90, 150)),
    (("landmark", "attraction", "viewpoint"), (60, 90)),
)


@dataclass(frozen=True, slots=True)
class ActivityDiscoveryService:
    """Map bounded normalized Places results into provider-independent options."""

    provider: AttractionDiscoveryPort
    maximum_options: int = MAX_ACTIVITY_OPTIONS

    def __post_init__(self) -> None:
        if not isinstance(self.provider, AttractionDiscoveryPort):
            raise TypeError("provider must satisfy AttractionDiscoveryPort")
        if type(self.maximum_options) is not int:
            raise TypeError("maximum_options must be an integer")
        if not 1 <= self.maximum_options <= MAX_ACTIVITY_OPTIONS:
            raise ValueError(f"maximum_options must be between 1 and {MAX_ACTIVITY_OPTIONS}")

    def discover(self, destination: Destination) -> tuple[ActivityOption, ...]:
        """Return a stable, deduplicated palette with documented estimate provenance."""

        if not isinstance(destination, Destination):
            raise TypeError("destination must be Destination")
        attractions = self.provider.discover_attractions(destination)
        if not isinstance(attractions, tuple):
            raise TypeError("activity provider must return a tuple")
        options: list[ActivityOption] = []
        seen: set[str] = set()
        for attraction in attractions:
            identity_source = (
                f"{attraction.name.strip().casefold()}|"
                f"{attraction.coordinates.latitude:.6f}|{attraction.coordinates.longitude:.6f}"
            )
            identity = sha256(identity_source.encode("utf-8")).hexdigest()[:20]
            if identity in seen:
                continue
            options.append(
                ActivityOption(
                    identity=identity,
                    name=attraction.name,
                    destination=destination,
                    category=attraction.category,
                    coordinates=attraction.coordinates,
                    duration=_duration_for_category(attraction.category),
                    accessibility=AccessibilityStatus.UNKNOWN,
                )
            )
            seen.add(identity)
            if len(options) == self.maximum_options:
                break
        return tuple(options)


def _duration_for_category(category: str) -> DurationEstimate | None:
    normalized = category.casefold()
    for keywords, duration in _CATEGORY_DURATIONS:
        if any(keyword in normalized for keyword in keywords):
            return DurationEstimate(
                *duration,
                provenance=DurationProvenance.CATEGORY_HEURISTIC,
                confidence=EstimateConfidence.MEDIUM,
            )
    return None


@dataclass(frozen=True, slots=True)
class ItineraryPlanningService:
    """Build and safely update itinerary structure from validated destinations."""

    def initialize(
        self,
        start_date: date,
        end_date: date,
        profile: TravellerProfile,
        stays: tuple[DestinationStay, ...],
        travel_legs: tuple[TravelLeg, ...] = (),
    ) -> Itinerary:
        """Create sequential days and attach route legs to arrival days."""

        if not isinstance(stays, tuple) or not stays:
            raise ValueError("stays must be a non-empty tuple")
        if not all(isinstance(stay, DestinationStay) for stay in stays):
            raise TypeError("stays must contain DestinationStay values")
        if not isinstance(travel_legs, tuple):
            raise TypeError("travel_legs must be a tuple")
        expected_leg_count = max(0, len(stays) - 1)
        if travel_legs and len(travel_legs) != expected_leg_count:
            raise ValueError("travel legs must align with destination transitions")
        for index, leg in enumerate(travel_legs):
            if (
                leg.origin != stays[index].destination
                or leg.destination != stays[index + 1].destination
            ):
                raise ValueError("travel legs must follow the destination route")

        days: list[ItineraryDay] = []
        number = 1
        for stay_index, stay in enumerate(stays):
            for local_day in range(stay.days):
                inbound = (
                    travel_legs[stay_index - 1]
                    if stay_index > 0 and local_day == 0 and travel_legs
                    else None
                )
                days.append(ItineraryDay(number, stay.destination, inbound_travel_leg=inbound))
                number += 1
        return Itinerary(start_date, end_date, profile, stays, tuple(days))

    def update_route(
        self,
        itinerary: Itinerary,
        stays: tuple[DestinationStay, ...],
        travel_legs: tuple[TravelLeg, ...] = (),
    ) -> Itinerary:
        """Rebuild allocation and retain activities where a compatible day remains."""

        rebuilt = self.initialize(
            itinerary.start_date,
            itinerary.end_date,
            itinerary.traveller_profile,
            stays,
            travel_legs,
        )
        editor = ItineraryEditor()
        for old_day in itinerary.days:
            candidates = [day for day in rebuilt.days if day.destination == old_day.destination]
            for activity in old_day.activities:
                target = next(
                    (day for day in candidates if day.number == old_day.number),
                    candidates[0] if candidates else None,
                )
                if target is not None:
                    rebuilt = editor.add_activity(
                        rebuilt,
                        ActivityOption(
                            activity.identity,
                            activity.name,
                            activity.destination,
                            activity.category,
                            activity.coordinates,
                            activity.duration,
                            activity.accessibility,
                        ),
                        target.number,
                        activity.period,
                    )
        return rebuilt


@dataclass(frozen=True, slots=True)
class ItineraryEditor:
    """Immutable, deterministic activity operations used by API and browser flows."""

    def add_activity(
        self,
        itinerary: Itinerary,
        option: ActivityOption,
        day_number: int,
        period: DayPeriod,
    ) -> Itinerary:
        day = _find_day(itinerary, day_number)
        if day.destination != option.destination:
            raise ValueError("activity destination must match the selected day")
        if any(
            activity.identity == option.identity
            for candidate_day in itinerary.days
            for activity in candidate_day.activities
        ):
            raise ValueError("activity is already selected")
        order = sum(activity.period is period for activity in day.activities)
        activity = ItineraryActivity(
            option.identity,
            option.name,
            option.destination,
            option.category,
            option.coordinates,
            option.duration,
            day.number,
            period,
            order,
            option.accessibility,
        )
        return _replace_day(itinerary, replace(day, activities=day.activities + (activity,)))

    def remove_activity(self, itinerary: Itinerary, identity: str) -> Itinerary:
        day, activity = _find_activity(itinerary, identity)
        remaining = tuple(item for item in day.activities if item.identity != activity.identity)
        return _replace_day(itinerary, replace(day, activities=_normalize_orders(remaining)))

    def replace_activity(
        self,
        itinerary: Itinerary,
        identity: str,
        replacement: ActivityOption,
    ) -> Itinerary:
        day, activity = _find_activity(itinerary, identity)
        without = self.remove_activity(itinerary, identity)
        return self.add_activity(without, replacement, day.number, activity.period)

    def move_activity(
        self,
        itinerary: Itinerary,
        identity: str,
        day_number: int,
        period: DayPeriod,
    ) -> Itinerary:
        _day, activity = _find_activity(itinerary, identity)
        option = ActivityOption(
            activity.identity,
            activity.name,
            activity.destination,
            activity.category,
            activity.coordinates,
            activity.duration,
            activity.accessibility,
        )
        return self.add_activity(
            self.remove_activity(itinerary, identity), option, day_number, period
        )

    def reorder_activities(
        self,
        itinerary: Itinerary,
        day_number: int,
        period: DayPeriod,
        identities: tuple[str, ...],
    ) -> Itinerary:
        day = _find_day(itinerary, day_number)
        in_period = tuple(item for item in day.activities if item.period is period)
        if set(identities) != {item.identity for item in in_period} or len(identities) != len(
            in_period
        ):
            raise ValueError("reorder identities must exactly match the selected period")
        by_identity = {item.identity: item for item in in_period}
        reordered = tuple(
            replace(by_identity[identity], order=index) for index, identity in enumerate(identities)
        )
        others = tuple(item for item in day.activities if item.period is not period)
        return _replace_day(itinerary, replace(day, activities=others + reordered))


@dataclass(frozen=True, slots=True)
class FeasibilityService:
    """Calculate transparent day budgets without AI or invented travel time."""

    _PACE_CAPACITY: ClassVar[dict[Pace, int]] = {
        Pace.RELAXED: 480,
        Pace.BALANCED: 600,
        Pace.ACTIVE: 720,
    }

    def assess(self, day: ItineraryDay, profile: TravellerProfile) -> FeasibilityAssessment:
        if not isinstance(day, ItineraryDay):
            raise TypeError("day must be ItineraryDay")
        if not isinstance(profile, TravellerProfile):
            raise TypeError("profile must be TravellerProfile")

        available = self._PACE_CAPACITY[profile.pace]
        buffer = 90  # one meal and a meaningful rest block
        transition_count = max(0, len(day.activities) - 1)
        buffer += transition_count * 30
        if profile.party.children or profile.party.infants:
            buffer += 30
        if profile.party.seniors:
            buffer += 30
        adjustments = {
            TravelRequirement.FREQUENT_BREAKS: 45,
            TravelRequirement.REDUCED_WALKING: 30,
            TravelRequirement.WHEELCHAIR_ACCESS: 30,
            TravelRequirement.MOBILITY_ASSISTANCE: 30,
            TravelRequirement.STROLLER: 20,
            TravelRequirement.SLOWER_TRANSITIONS: 30,
        }
        buffer += sum(adjustments[requirement] for requirement in profile.requirements)

        warnings: list[str] = []
        activity_minutes = 0
        for activity in day.activities:
            if activity.duration is None:
                warnings.append(f"Duration is unknown for {activity.name}.")
            else:
                activity_minutes += activity.duration.typical_minutes
        travel_minutes = 0
        unresolved_travel = False
        if day.inbound_travel_leg is not None:
            if day.inbound_travel_leg.duration is None:
                unresolved_travel = True
                warnings.append(
                    "Travel time is needed before this arrival day's load can be assessed."
                )
            else:
                # Arrival-day planning deliberately uses the conservative upper bound.
                travel_minutes += day.inbound_travel_leg.duration.maximum_minutes
                travel_minutes += day.inbound_travel_leg.planning_buffer_minutes
        occupied = activity_minutes + travel_minutes + buffer
        ratio = occupied / available
        if unresolved_travel:
            level = FeasibilityLevel.UNRESOLVED
        elif ratio <= 0.45:
            level = FeasibilityLevel.RELAXED
        elif ratio <= 0.70:
            level = FeasibilityLevel.COMFORTABLE
        elif ratio <= 0.90:
            level = FeasibilityLevel.FULL
        else:
            level = FeasibilityLevel.VERY_FULL
            warnings.append(
                "This day is becoming quite full for the selected pace and travel needs."
            )
        violations: tuple[str, ...] = ()
        if not unresolved_travel and travel_minutes >= available:
            violations = (
                "Known travel consumes the usable planning window for this arrival day.",
            )
        elif not unresolved_travel and day.inbound_travel_leg is not None and occupied > available:
            violations = (
                "Known travel, activities, and required buffers exceed this day's planning window.",
            )
        return FeasibilityAssessment(
            day.number,
            level,
            occupied,
            available,
            available - occupied,
            buffer,
            tuple(warnings),
            violations,
        )


@dataclass(frozen=True, slots=True)
class ItinerarySummaryService:
    """Produce non-authoritative structured Wayfinder fallback copy."""

    def summarize(self, itinerary: Itinerary) -> str:
        destinations = ", ".join(stay.destination.name for stay in itinerary.stays)
        activity_count = sum(len(day.activities) for day in itinerary.days)
        return (
            f"A {len(itinerary.days)}-day route through {destinations}, with "
            f"{activity_count} selected experiences. Review travel estimates and day-load "
            "guidance before making live transport or booking decisions."
        )


def _find_day(itinerary: Itinerary, number: int) -> ItineraryDay:
    if not isinstance(itinerary, Itinerary):
        raise TypeError("itinerary must be Itinerary")
    day = next((candidate for candidate in itinerary.days if candidate.number == number), None)
    if day is None:
        raise ValueError("itinerary day was not found")
    return day


def _find_activity(itinerary: Itinerary, identity: str) -> tuple[ItineraryDay, ItineraryActivity]:
    for day in itinerary.days:
        for activity in day.activities:
            if activity.identity == identity:
                return day, activity
    raise ValueError("itinerary activity was not found")


def _normalize_orders(activities: tuple[ItineraryActivity, ...]) -> tuple[ItineraryActivity, ...]:
    counters = {period: 0 for period in DayPeriod}
    normalized: list[ItineraryActivity] = []
    for activity in activities:
        normalized.append(replace(activity, order=counters[activity.period]))
        counters[activity.period] += 1
    return tuple(normalized)


def _replace_day(itinerary: Itinerary, replacement: ItineraryDay) -> Itinerary:
    return replace(
        itinerary,
        days=tuple(
            replacement if day.number == replacement.number else day for day in itinerary.days
        ),
    )
