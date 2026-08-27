"""Tests for provider-independent Itinerary Studio domain values."""

from datetime import date

import pytest

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
    GeoCoordinates,
    Itinerary,
    ItineraryActivity,
    ItineraryDay,
    Pace,
    TravelLeg,
    TravellerParty,
    TravellerProfile,
    TravelMode,
    TravelRequirement,
)


def destination(name: str = "Bangkok") -> Destination:
    return Destination(name, "Thailand", GeoCoordinates(13.75, 100.5))


def duration() -> DurationEstimate:
    return DurationEstimate(
        60,
        120,
        DurationProvenance.CATEGORY_HEURISTIC,
        EstimateConfidence.MEDIUM,
    )


def option(place: Destination | None = None) -> ActivityOption:
    selected_destination = place or destination()
    return ActivityOption(
        "trusted-1",
        "Grand Palace",
        selected_destination,
        "cultural landmark",
        selected_destination.coordinates,
        duration(),
    )


def activity(place: Destination | None = None, **changes: object) -> ItineraryActivity:
    selected_destination = place or destination()
    values: dict[str, object] = {
        "identity": "trusted-1",
        "name": "Grand Palace",
        "destination": selected_destination,
        "category": "cultural landmark",
        "coordinates": selected_destination.coordinates,
        "duration": duration(),
        "day_number": 1,
        "period": DayPeriod.MORNING,
        "order": 0,
        "accessibility": AccessibilityStatus.UNKNOWN,
    }
    values.update(changes)
    return ItineraryActivity(**values)  # type: ignore[arg-type]


def profile() -> TravellerProfile:
    return TravellerProfile(TravellerParty())


def test_traveller_party_supports_all_compositions_and_coherent_total() -> None:
    party = TravellerParty(2, 1, 2, 1, 2)
    assert party.total == 8


@pytest.mark.parametrize(
    ("values", "error", "message"),
    [
        ({"adults": 1.0}, TypeError, "counts must be integers"),
        ({"adults": -1, "children": 2}, ValueError, "must not be negative"),
        ({"adults": 0}, ValueError, "at least one"),
        ({"adults": 21}, ValueError, "at most 20"),
    ],
)
def test_traveller_party_rejects_invalid_counts(
    values: dict[str, object], error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        TravellerParty(**values)  # type: ignore[arg-type]


def test_traveller_profile_supports_pace_and_unique_requirements() -> None:
    selected = TravellerProfile(
        TravellerParty(2, children=1, seniors=1),
        Pace.RELAXED,
        (TravelRequirement.REDUCED_WALKING, TravelRequirement.FREQUENT_BREAKS),
    )
    assert selected.pace is Pace.RELAXED


@pytest.mark.parametrize(
    ("values", "error", "message"),
    [
        ({"party": object()}, TypeError, "party must"),
        ({"party": TravellerParty(), "pace": "fast"}, TypeError, "pace must"),
        ({"party": TravellerParty(), "requirements": []}, TypeError, "must be a tuple"),
        ({"party": TravellerParty(), "requirements": ("rest",)}, TypeError, "must contain"),
        (
            {
                "party": TravellerParty(),
                "requirements": (
                    TravelRequirement.STROLLER,
                    TravelRequirement.STROLLER,
                ),
            },
            ValueError,
            "must not contain duplicates",
        ),
    ],
)
def test_traveller_profile_rejects_invalid_structure(
    values: dict[str, object], error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        TravellerProfile(**values)  # type: ignore[arg-type]


def test_duration_estimate_exposes_rounded_midpoint_and_trust() -> None:
    estimate = DurationEstimate(60, 91, DurationProvenance.PROVIDER, EstimateConfidence.HIGH)
    assert estimate.typical_minutes == 76


@pytest.mark.parametrize(
    ("values", "error", "message"),
    [
        ((1.0, 2), TypeError, "must be integers"),
        ((0, 2), ValueError, "must be positive"),
        ((3, 2), ValueError, "must not exceed"),
        ((1, 2, "provider", EstimateConfidence.HIGH), TypeError, "provenance must"),
        ((1, 2, DurationProvenance.PROVIDER, "high"), TypeError, "confidence must"),
    ],
)
def test_duration_estimate_rejects_invalid_values(
    values: tuple[object, ...], error: type[Exception], message: str
) -> None:
    args = (*values, DurationProvenance.PROVIDER, EstimateConfidence.LOW)[:4]
    with pytest.raises(error, match=message):
        DurationEstimate(*args)  # type: ignore[arg-type]


def test_destination_stay_requires_typed_destination_and_positive_days() -> None:
    assert DestinationStay(destination(), 2).days == 2
    with pytest.raises(TypeError, match="destination must"):
        DestinationStay(object(), 2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="days must"):
        DestinationStay(destination(), 1.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be positive"):
        DestinationStay(destination(), 0)


def test_activity_option_preserves_location_duration_and_unknown_accessibility() -> None:
    selected = option()
    assert selected.coordinates == destination().coordinates
    assert selected.accessibility is AccessibilityStatus.UNKNOWN


@pytest.mark.parametrize(
    ("changes", "error", "message"),
    [
        ({"identity": 1}, TypeError, "identity must be a string"),
        ({"name": " "}, ValueError, "name must not be blank"),
        ({"destination": object()}, TypeError, "destination must"),
        ({"coordinates": object()}, TypeError, "coordinates must"),
        ({"duration": object()}, TypeError, "duration must"),
        ({"accessibility": "unknown"}, TypeError, "accessibility must"),
    ],
)
def test_activity_option_rejects_invalid_values(
    changes: dict[str, object], error: type[Exception], message: str
) -> None:
    values = {
        "identity": "id",
        "name": "Place",
        "destination": destination(),
        "category": "museum",
        "coordinates": None,
        "duration": None,
        "accessibility": AccessibilityStatus.UNKNOWN,
    }
    values.update(changes)
    with pytest.raises(error, match=message):
        ActivityOption(**values)  # type: ignore[arg-type]


def test_itinerary_activity_supports_unknown_duration_and_accessibility_truth() -> None:
    selected = activity(duration=None, coordinates=None)
    assert selected.duration is None
    assert selected.accessibility is AccessibilityStatus.UNKNOWN


@pytest.mark.parametrize(
    ("changes", "error", "message"),
    [
        ({"category": 1}, TypeError, "category must be a string"),
        ({"identity": ""}, ValueError, "identity must not be blank"),
        ({"destination": object()}, TypeError, "destination must"),
        ({"coordinates": object()}, TypeError, "coordinates must"),
        ({"duration": object()}, TypeError, "duration must"),
        ({"day_number": 0}, ValueError, "day_number must"),
        ({"period": "morning"}, TypeError, "period must"),
        ({"order": -1}, ValueError, "order must"),
        ({"accessibility": "unknown"}, TypeError, "accessibility must"),
    ],
)
def test_itinerary_activity_rejects_invalid_values(
    changes: dict[str, object], error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        activity(**changes)


def test_travel_leg_represents_estimated_and_unknown_transitions() -> None:
    origin = destination()
    target = destination("Chiang Mai")
    estimated = TravelLeg(
        origin,
        target,
        TravelMode.FLIGHT,
        duration(),
        90,
        "trusted routing provider",
        580.5,
        True,
    )
    unknown = TravelLeg(origin, target)
    assert estimated.planning_buffer_minutes == 90
    assert estimated.evidence_provenance == "trusted routing provider"
    assert estimated.distance_kilometers == 580.5
    assert estimated.verified is True
    assert unknown.mode is None
    assert unknown.duration is None
    assert unknown.verified is False


@pytest.mark.parametrize(
    ("args", "error", "message"),
    [
        ((object(), destination("Other")), TypeError, "endpoints"),
        ((destination(), destination()), ValueError, "different"),
        ((destination(), destination("Other"), "road"), TypeError, "mode must"),
        (
            (destination(), destination("Other"), TravelMode.ROAD, object()),
            TypeError,
            "duration must",
        ),
        ((destination(), destination("Other"), TravelMode.ROAD, None, 1.0), TypeError, "buffer"),
        ((destination(), destination("Other"), TravelMode.ROAD, None, -1), ValueError, "negative"),
        (
            (destination(), destination("Other"), None, None, 0, " "),
            ValueError,
            "non-blank",
        ),
        (
            (destination(), destination("Other"), None, None, 0, None, "far"),
            TypeError,
            "must be a number",
        ),
        (
            (destination(), destination("Other"), None, None, 0, None, 0),
            ValueError,
            "must be positive",
        ),
        (
            (destination(), destination("Other"), None, None, 0, None, None, 1),
            TypeError,
            "must be a boolean",
        ),
        (
            (destination(), destination("Other"), None, None, 0, None, None, True),
            ValueError,
            "require a mode",
        ),
        (
            (destination(), destination("Other"), TravelMode.ROAD),
            ValueError,
            "require verified evidence",
        ),
    ],
)
def test_travel_leg_rejects_invalid_values(
    args: tuple[object, ...], error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        TravelLeg(*args)  # type: ignore[arg-type]


def test_itinerary_day_accepts_ordered_activities_and_matching_leg() -> None:
    origin = destination("Phuket")
    target = destination()
    leg = TravelLeg(origin, target)
    day = ItineraryDay(1, target, (activity(),), leg)
    assert day.inbound_travel_leg == leg


@pytest.mark.parametrize(
    ("values", "error", "message"),
    [
        ({"number": 0}, ValueError, "positive"),
        ({"destination": object()}, TypeError, "destination must"),
        ({"activities": []}, TypeError, "must be a tuple"),
        ({"activities": (object(),)}, TypeError, "must contain"),
        ({"activities": (activity(day_number=2),)}, ValueError, "belong"),
        ({"activities": (activity(), activity())}, ValueError, "duplicate"),
        (
            {
                "activities": (
                    activity(),
                    activity(identity="other", name="Other"),
                )
            },
            ValueError,
            "order must be unique",
        ),
        ({"inbound_travel_leg": object()}, TypeError, "must be TravelLeg"),
        (
            {
                "inbound_travel_leg": TravelLeg(
                    destination(), destination("Chiang Mai")
                )
            },
            ValueError,
            "must arrive",
        ),
    ],
)
def test_itinerary_day_rejects_incoherent_values(
    values: dict[str, object], error: type[Exception], message: str
) -> None:
    defaults: dict[str, object] = {"number": 1, "destination": destination()}
    defaults.update(values)
    with pytest.raises(error, match=message):
        ItineraryDay(**defaults)  # type: ignore[arg-type]


def test_itinerary_requires_allocations_dates_and_days_to_align() -> None:
    trip = Itinerary(
        date(2026, 12, 1),
        date(2026, 12, 2),
        profile(),
        (DestinationStay(destination(), 2),),
        (ItineraryDay(1, destination()), ItineraryDay(2, destination())),
    )
    assert len(trip.days) == 2


@pytest.mark.parametrize(
    ("changes", "error", "message"),
    [
        ({"start_date": "2026-01-01"}, TypeError, "dates must"),
        (
            {"start_date": date(2026, 1, 2), "end_date": date(2026, 1, 1)},
            ValueError,
            "must not be after",
        ),
        ({"traveller_profile": object()}, TypeError, "traveller_profile"),
        ({"stays": []}, ValueError, "non-empty tuple"),
        ({"stays": (object(),)}, TypeError, "must contain"),
        ({"days": []}, TypeError, "days must be a tuple"),
        ({"stays": (DestinationStay(destination(), 2),)}, ValueError, "allocations must equal"),
        ({"days": ()}, ValueError, "one day"),
        ({"days": (ItineraryDay(2, destination()),)}, ValueError, "sequential"),
        ({"days": (ItineraryDay(1, destination("Other")),)}, ValueError, "follow destination"),
    ],
)
def test_itinerary_rejects_incoherent_values(
    changes: dict[str, object], error: type[Exception], message: str
) -> None:
    defaults: dict[str, object] = {
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 1),
        "traveller_profile": profile(),
        "stays": (DestinationStay(destination(), 1),),
        "days": (ItineraryDay(1, destination()),),
    }
    defaults.update(changes)
    with pytest.raises(error, match=message):
        Itinerary(**defaults)  # type: ignore[arg-type]


def test_feasibility_assessment_preserves_transparent_calculation() -> None:
    result = FeasibilityAssessment(
        1, FeasibilityLevel.COMFORTABLE, 400, 600, 200, 120, ("Watch pacing",), ()
    )
    assert result.remaining_minutes == 200


@pytest.mark.parametrize(
    ("changes", "error", "message"),
    [
        ({"day_number": 0}, ValueError, "positive"),
        ({"level": "full"}, TypeError, "level must"),
        ({"occupied_minutes": 1.0}, TypeError, "must be an integer"),
        ({"occupied_minutes": -1, "remaining_minutes": 601}, ValueError, "inconsistent"),
        ({"remaining_minutes": 100}, ValueError, "must equal"),
        ({"warnings": ["warning"]}, TypeError, "warnings must"),
        ({"hard_violations": ("",)}, TypeError, "hard_violations must"),
    ],
)
def test_feasibility_assessment_rejects_incoherent_values(
    changes: dict[str, object], error: type[Exception], message: str
) -> None:
    defaults: dict[str, object] = {
        "day_number": 1,
        "level": FeasibilityLevel.RELAXED,
        "occupied_minutes": 100,
        "available_minutes": 600,
        "remaining_minutes": 500,
        "buffer_minutes": 90,
    }
    defaults.update(changes)
    with pytest.raises(error, match=message):
        FeasibilityAssessment(**defaults)  # type: ignore[arg-type]
