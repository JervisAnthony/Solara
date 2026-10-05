"""Versioned, local handoff preparation. Nothing is stored or submitted."""

import json
from dataclasses import dataclass, replace
from datetime import date, timedelta

from solara_travel.application.itinerary import FeasibilityService
from solara_travel.domain import (
    AccessibilityStatus,
    DayPeriod,
    Destination,
    DestinationStay,
    DurationEstimate,
    DurationProvenance,
    EstimateConfidence,
    GeoCoordinates,
    Itinerary,
    ItineraryActivity,
    ItineraryDay,
    Pace,
    TravelLeg,
    TravellerParty,
    TravellerProfile,
    TravelRequirement,
)
from solara_travel.domain.itinerary import TravelMode

MAX_SNAPSHOT_BYTES = 1_000_000

# Freeze the v1 wire contract independently of future domain fields.
_V1_FIELDS = {
    Itinerary: ("start_date", "end_date", "traveller_profile", "stays", "days"),
    TravellerProfile: ("party", "pace", "requirements"),
    TravellerParty: ("adults", "young_adults", "children", "infants", "seniors"),
    DestinationStay: ("destination", "days"),
    Destination: ("name", "country", "coordinates"),
    GeoCoordinates: ("latitude", "longitude"),
    ItineraryDay: ("number", "destination", "activities", "inbound_travel_leg"),
    ItineraryActivity: (
        "identity",
        "name",
        "destination",
        "category",
        "coordinates",
        "duration",
        "day_number",
        "period",
        "order",
        "accessibility",
    ),
    DurationEstimate: ("minimum_minutes", "maximum_minutes", "provenance", "confidence"),
    TravelLeg: (
        "origin",
        "destination",
        "mode",
        "duration",
        "planning_buffer_minutes",
        "evidence_provenance",
        "distance_kilometers",
        "verified",
    ),
}


def _safe_data(value: object) -> object:
    if type(value) in _V1_FIELDS:
        return {key: _safe_data(getattr(value, key)) for key in _V1_FIELDS[type(value)]}
    if isinstance(value, tuple):
        return [_safe_data(item) for item in value]
    return value


def _object(value: object, expected: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("snapshot object has missing or unsupported fields")
    return value


def _record(value: object, cls: type) -> dict:
    return _object(value, set(_V1_FIELDS[cls]))


def _coordinates(value: object) -> GeoCoordinates | None:
    return None if value is None else GeoCoordinates(**_record(value, GeoCoordinates))


def _destination(value: object) -> Destination:
    data = _record(value, Destination)
    return Destination(data["name"], data["country"], _coordinates(data["coordinates"]))


def _duration(value: object) -> DurationEstimate | None:
    if value is None:
        return None
    data = _record(value, DurationEstimate)
    return DurationEstimate(
        data["minimum_minutes"],
        data["maximum_minutes"],
        DurationProvenance(data["provenance"]),
        EstimateConfidence(data["confidence"]),
    )


def _leg(value: object) -> TravelLeg | None:
    if value is None:
        return None
    data = _record(value, TravelLeg)
    return TravelLeg(
        _destination(data["origin"]),
        _destination(data["destination"]),
        None if data["mode"] is None else TravelMode(data["mode"]),
        _duration(data["duration"]),
        data["planning_buffer_minutes"],
        data["evidence_provenance"],
        data["distance_kilometers"],
        data["verified"],
    )


def _activity(value: object) -> ItineraryActivity:
    data = _record(value, ItineraryActivity)
    return ItineraryActivity(
        data["identity"],
        data["name"],
        _destination(data["destination"]),
        data["category"],
        _coordinates(data["coordinates"]),
        _duration(data["duration"]),
        data["day_number"],
        DayPeriod(data["period"]),
        data["order"],
        AccessibilityStatus(data["accessibility"]),
    )


def _date_json(value: object) -> str:
    if type(value) is not date:
        raise TypeError("unsupported snapshot value")
    return value.isoformat()


@dataclass(frozen=True, slots=True)
class TripSnapshot:
    """Portable itinerary truth, version 1. Commerce and narration are excluded."""

    itinerary: Itinerary
    requirements_included: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.itinerary, Itinerary):
            raise TypeError("snapshot requires Itinerary")
        if type(self.requirements_included) is not bool:
            raise TypeError("requirements_included must be boolean")
        if not self.requirements_included:
            profile = replace(self.itinerary.traveller_profile, requirements=())
            object.__setattr__(
                self, "itinerary", replace(self.itinerary, traveller_profile=profile)
            )

    def to_json(self) -> str:
        """Deterministic allowlisted data; no raw providers, prompts or credentials."""
        data = {
            "schema_version": 1,
            "requirements_included": self.requirements_included,
            "itinerary": _safe_data(self.itinerary),
        }
        result = json.dumps(
            data,
            default=_date_json,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(result.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise ValueError("snapshot exceeds size limit")
        return result

    @classmethod
    def from_json(cls, content: str) -> "TripSnapshot":
        """Strict round trip for future repositories; not a public import endpoint."""
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise ValueError("invalid snapshot size or type")
        root = _object(
            json.loads(content), {"schema_version", "requirements_included", "itinerary"}
        )
        if type(root["schema_version"]) is not int or root["schema_version"] != 1:
            raise ValueError("unsupported schema version")
        data = _record(root["itinerary"], Itinerary)
        profile = _record(data["traveller_profile"], TravellerProfile)
        parsed_profile = TravellerProfile(
            TravellerParty(**_record(profile["party"], TravellerParty)),
            Pace(profile["pace"]),
            tuple(TravelRequirement(item) for item in profile["requirements"]),
        )
        stays = tuple(
            DestinationStay(_destination(item["destination"]), item["days"])
            for item in (_record(value, DestinationStay) for value in data["stays"])
        )
        days = tuple(
            ItineraryDay(
                item["number"],
                _destination(item["destination"]),
                tuple(_activity(value) for value in item["activities"]),
                _leg(item["inbound_travel_leg"]),
            )
            for item in (_record(value, ItineraryDay) for value in data["days"])
        )
        itinerary = Itinerary(
            date.fromisoformat(data["start_date"]),
            date.fromisoformat(data["end_date"]),
            parsed_profile,
            stays,
            days,
        )
        if root["requirements_included"] is False and parsed_profile.requirements:
            raise ValueError("undisclosed requirements must be absent")
        return cls(itinerary, root["requirements_included"])


@dataclass(frozen=True, slots=True)
class TripHandoff:
    """Traveller-approved local artifact, never an agency submission or reservation."""

    snapshot: TripSnapshot

    def to_text(self) -> str:
        trip = self.snapshot.itinerary
        lines = [
            "SOLARA · TRIP HANDOFF",
            "Planning summary · not booked or submitted",
            f"{trip.start_date} to {trip.end_date} · {trip.traveller_profile.pace.value} pace",
            f"Travellers: {trip.traveller_profile.party.total}",
            "Stay departure dates below are exclusive allocation boundaries, not reservations.",
        ]
        for stay in trip.dated_stays:
            lines.append(
                f"{stay.stay.destination.name}, {stay.stay.destination.country}: "
                f"{stay.arrival_date} to {stay.departure_date} · {stay.allocated_days} days"
            )
        if self.snapshot.requirements_included:
            lines.append(
                "Travel requirements: "
                + ", ".join(
                    item.value.replace("_", " ") for item in trip.traveller_profile.requirements
                )
            )
        else:
            lines.append("Travel requirements: excluded by traveller")
        feasibility = FeasibilityService()
        for day in trip.days:
            day_date = trip.start_date + timedelta(days=day.number - 1)
            lines.append(f"Day {day.number} · {day_date} · {day.destination.name}")
            leg = day.inbound_travel_leg
            if leg is not None:
                lines.append(
                    f"Journey: {leg.origin.name} → {leg.destination.name} · {leg.resolution}"
                )
                if leg.duration is not None:
                    lines.append(
                        f"Verified planning estimate: {leg.duration.minimum_minutes}–"
                        f"{leg.duration.maximum_minutes} minutes · {leg.evidence_provenance}"
                    )
                else:
                    lines.append("Travel time needed; arrival-day feasibility unresolved")
            if self.snapshot.requirements_included:
                assessment = feasibility.assess(day, trip.traveller_profile)
                lines.append(f"Feasibility: {assessment.level}")
            else:
                lines.append("Day load: review in Solara with your full travel requirements.")
            for activity in sorted(
                day.activities, key=lambda item: (list(DayPeriod).index(item.period), item.order)
            ):
                duration = activity.duration
                timing = (
                    "duration unknown"
                    if duration is None
                    else (
                        f"{duration.minimum_minutes}–{duration.maximum_minutes} minutes "
                        f"({duration.provenance})"
                    )
                )
                lines.append(f"  {activity.period}: {activity.name} · {timing}")
        return "\n".join(lines) + "\n"
