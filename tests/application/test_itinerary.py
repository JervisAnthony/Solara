"""Tests for deterministic Itinerary Studio application services."""

from dataclasses import replace
from datetime import date

import pytest

from solara_travel.application import (
    MAX_ACTIVITY_OPTIONS,
    ActivityDiscoveryService,
    FeasibilityService,
    ItineraryEditor,
    ItineraryPlanningService,
    ItinerarySummaryService,
)
from solara_travel.domain import (
    ActivityOption,
    Attraction,
    DayPeriod,
    Destination,
    DestinationStay,
    DurationEstimate,
    DurationProvenance,
    EstimateConfidence,
    FeasibilityLevel,
    GeoCoordinates,
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


def estimate(minutes: int = 120) -> DurationEstimate:
    return DurationEstimate(
        minutes,
        minutes,
        DurationProvenance.CATEGORY_HEURISTIC,
        EstimateConfidence.MEDIUM,
    )


def activity_option(identity: str = "id-1", place: Destination | None = None) -> ActivityOption:
    selected = place or destination()
    return ActivityOption(
        identity,
        f"Place {identity}",
        selected,
        "museum",
        selected.coordinates,
        estimate(),
    )


class AttractionProvider:
    def __init__(self, attractions: object) -> None:
        self.attractions = attractions

    def discover_attractions(self, destination: Destination) -> tuple[Attraction, ...]:
        del destination
        return self.attractions  # type: ignore[return-value]


def profile(
    pace: Pace = Pace.BALANCED,
    *,
    children: int = 0,
    infants: int = 0,
    seniors: int = 0,
    requirements: tuple[TravelRequirement, ...] = (),
) -> TravellerProfile:
    return TravellerProfile(
        TravellerParty(1, children=children, infants=infants, seniors=seniors),
        pace,
        requirements,
    )


def itinerary(days: int = 2):
    return ItineraryPlanningService().initialize(
        date(2026, 11, 1),
        date(2026, 11, days),
        profile(),
        (DestinationStay(destination(), days),),
    )


def test_activity_discovery_is_bounded_deduplicated_and_trust_aware() -> None:
    categories = [
        "museum",
        "beach",
        "market",
        "nightlife",
        "landmark",
        "unclassified",
    ]
    attractions = tuple(
        Attraction(f"Place {index}", category, GeoCoordinates(10 + index, 20 + index))
        for index, category in enumerate(categories)
    )
    duplicate = attractions[0]
    service = ActivityDiscoveryService(
        AttractionProvider((duplicate, duplicate) + attractions[1:]), 6
    )

    first = service.discover(destination())
    second = service.discover(destination())

    assert first == second
    assert len(first) == 6
    assert [option.duration is not None for option in first] == [True] * 5 + [False]
    assert len({option.identity for option in first}) == 6


def test_activity_discovery_accepts_empty_results_and_enforces_contract() -> None:
    assert ActivityDiscoveryService(AttractionProvider(())).discover(destination()) == ()
    with pytest.raises(TypeError, match="destination must"):
        ActivityDiscoveryService(AttractionProvider(())).discover(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must return a tuple"):
        ActivityDiscoveryService(AttractionProvider([])).discover(destination())


@pytest.mark.parametrize(
    ("provider", "maximum", "error", "message"),
    [
        (object(), 1, TypeError, "must satisfy"),
        (AttractionProvider(()), 1.0, TypeError, "must be an integer"),
        (AttractionProvider(()), 0, ValueError, "between 1"),
        (AttractionProvider(()), MAX_ACTIVITY_OPTIONS + 1, ValueError, "between 1"),
    ],
)
def test_activity_discovery_rejects_invalid_configuration(
    provider: object, maximum: object, error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        ActivityDiscoveryService(provider, maximum)  # type: ignore[arg-type]


def test_planning_service_initializes_route_and_travel_arrival_day() -> None:
    bangkok = destination()
    chiang_mai = destination("Chiang Mai")
    leg = TravelLeg(bangkok, chiang_mai, TravelMode.FLIGHT, estimate(180), 90)
    trip = ItineraryPlanningService().initialize(
        date(2026, 11, 1),
        date(2026, 11, 3),
        profile(),
        (DestinationStay(bangkok, 1), DestinationStay(chiang_mai, 2)),
        (leg,),
    )
    assert [day.destination.name for day in trip.days] == ["Bangkok", "Chiang Mai", "Chiang Mai"]
    assert trip.days[1].inbound_travel_leg == leg
    assert trip.days[2].inbound_travel_leg is None


@pytest.mark.parametrize(
    ("stays", "legs", "error", "message"),
    [
        ([], (), ValueError, "non-empty"),
        ((object(),), (), TypeError, "must contain"),
        ((DestinationStay(destination(), 1),), [], TypeError, "must be a tuple"),
        (
            (DestinationStay(destination(), 1), DestinationStay(destination("Other"), 1)),
            (),
            ValueError,
            "allocations must equal",
        ),
        (
            (DestinationStay(destination(), 1), DestinationStay(destination("Other"), 1)),
            (TravelLeg(destination(), destination("Other"), TravelMode.ROAD),) * 2,
            ValueError,
            "must align",
        ),
        (
            (DestinationStay(destination(), 1), DestinationStay(destination("Other"), 1)),
            (TravelLeg(destination("Wrong"), destination("Other"), TravelMode.ROAD),),
            ValueError,
            "must follow",
        ),
    ],
)
def test_planning_service_rejects_incoherent_route_input(
    stays: object, legs: object, error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        ItineraryPlanningService().initialize(
            date(2026, 11, 1),
            date(2026, 11, 1),
            profile(),
            stays,  # type: ignore[arg-type]
            legs,  # type: ignore[arg-type]
        )


def test_route_update_reorders_allocations_and_preserves_compatible_activities() -> None:
    editor = ItineraryEditor()
    original = editor.add_activity(itinerary(2), activity_option(), 1, DayPeriod.MORNING)
    updated = ItineraryPlanningService().update_route(
        original,
        (DestinationStay(destination(), 2),),
    )
    assert updated.days[0].activities[0].identity == "id-1"

    other = destination("Other")
    changed = ItineraryPlanningService().update_route(
        original,
        (DestinationStay(other, 2),),
    )
    assert all(not day.activities for day in changed.days)


def test_editor_add_remove_replace_move_and_reorder_are_immutable() -> None:
    editor = ItineraryEditor()
    original = itinerary(2)
    first = editor.add_activity(original, activity_option("one"), 1, DayPeriod.MORNING)
    second = editor.add_activity(first, activity_option("two"), 1, DayPeriod.MORNING)
    reordered = editor.reorder_activities(second, 1, DayPeriod.MORNING, ("two", "one"))
    moved = editor.move_activity(reordered, "one", 2, DayPeriod.AFTERNOON)
    replaced = editor.replace_activity(moved, "two", activity_option("three"))
    removed = editor.remove_activity(replaced, "one")

    assert not original.days[0].activities
    assert [item.identity for item in reordered.days[0].activities] == ["two", "one"]
    assert moved.days[1].activities[0].period is DayPeriod.AFTERNOON
    assert replaced.days[0].activities[0].identity == "three"
    assert not removed.days[1].activities


def test_editor_rejects_invalid_operations() -> None:
    editor = ItineraryEditor()
    trip = itinerary()
    other = destination("Other")
    with pytest.raises(TypeError, match="itinerary must"):
        editor.add_activity(object(), activity_option(), 1, DayPeriod.MORNING)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="day was not found"):
        editor.add_activity(trip, activity_option(), 99, DayPeriod.MORNING)
    with pytest.raises(ValueError, match="destination must match"):
        editor.add_activity(trip, activity_option(place=other), 1, DayPeriod.MORNING)
    selected = editor.add_activity(trip, activity_option(), 1, DayPeriod.MORNING)
    with pytest.raises(ValueError, match="already selected"):
        editor.add_activity(selected, activity_option(), 2, DayPeriod.MORNING)
    with pytest.raises(ValueError, match="activity was not found"):
        editor.remove_activity(selected, "missing")
    with pytest.raises(ValueError, match="exactly match"):
        editor.reorder_activities(selected, 1, DayPeriod.MORNING, ())


def populated_day(
    count: int,
    *,
    minutes: int = 120,
    travel_leg: TravelLeg | None = None,
    unknown: bool = False,
) -> ItineraryDay:
    place = destination()
    activities = tuple(
        replace(
            ItineraryEditor()
            .add_activity(itinerary(), activity_option(str(index)), 1, DayPeriod.MORNING)
            .days[0]
            .activities[0],
            duration=None if unknown else estimate(minutes),
            order=index,
        )
        for index in range(count)
    )
    return ItineraryDay(1, place, activities, travel_leg)


@pytest.mark.parametrize(
    ("day", "selected_profile", "level"),
    [
        (populated_day(0), profile(Pace.ACTIVE), FeasibilityLevel.RELAXED),
        (populated_day(2, minutes=120), profile(), FeasibilityLevel.COMFORTABLE),
        (populated_day(3, minutes=120), profile(), FeasibilityLevel.FULL),
        (populated_day(4, minutes=150), profile(Pace.RELAXED), FeasibilityLevel.VERY_FULL),
    ],
)
def test_feasibility_levels_are_deterministic(
    day: ItineraryDay, selected_profile: TravellerProfile, level: FeasibilityLevel
) -> None:
    first = FeasibilityService().assess(day, selected_profile)
    assert first == FeasibilityService().assess(day, selected_profile)
    assert first.level is level


def test_feasibility_accounts_for_party_needs_unknowns_travel_and_hard_impossibility() -> None:
    origin = destination("Origin")
    target = destination()
    unknown_leg = TravelLeg(origin, target, TravelMode.FERRY, None, 90)
    needs = tuple(TravelRequirement)
    selected_profile = profile(
        Pace.RELAXED,
        children=1,
        infants=1,
        seniors=1,
        requirements=needs,
    )
    unknown_result = FeasibilityService().assess(
        populated_day(1, travel_leg=unknown_leg, unknown=True), selected_profile
    )
    assert len(unknown_result.warnings) >= 2
    assert unknown_result.buffer_minutes > 200

    known_leg = replace(unknown_leg, duration=estimate(900))
    impossible = FeasibilityService().assess(
        populated_day(4, minutes=180, travel_leg=known_leg), selected_profile
    )
    assert impossible.hard_violations == ("The planned day exceeds a complete 24-hour window.",)


def test_feasibility_rejects_invalid_inputs_and_summary_is_non_authoritative() -> None:
    with pytest.raises(TypeError, match="day must"):
        FeasibilityService().assess(object(), profile())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="profile must"):
        FeasibilityService().assess(populated_day(0), object())  # type: ignore[arg-type]
    text = ItinerarySummaryService().summarize(itinerary())
    assert "2-day route" in text
    assert "booking decisions" in text
