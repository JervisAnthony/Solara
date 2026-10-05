"""Portable journey truth, commercial separation and explicit local disclosure."""

import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from solara_travel.application import FeasibilityService, ItineraryPlanningService
from solara_travel.application.journeys import JourneyPlanningService
from solara_travel.application.trip_export import TripHandoff, TripSnapshot, _date_json
from solara_travel.domain import (
    AccessibilityStatus,
    DayPeriod,
    Destination,
    DestinationStay,
    DurationEstimate,
    DurationProvenance,
    EstimateConfidence,
    GeoCoordinates,
    ItineraryActivity,
    TravelLeg,
    TravellerParty,
    TravellerProfile,
    TravelMode,
    TravelRequirement,
)
from solara_travel.domain.journey import JourneyOption
from solara_travel.domain.partners import (
    OfferAvailability,
    OfferTargetKind,
    Partner,
    PartnerCapability,
    PartnerKind,
    PartnerOffer,
)
from solara_travel.ports.errors import ProviderUnavailableError
from solara_travel.presentation.web.branding import BrandPresentation


def destination(name="Singapore", country="Singapore"):
    return Destination(name, country, GeoCoordinates(1.3, 103.8))


def duration():
    return DurationEstimate(60, 120, DurationProvenance.PROVIDER, EstimateConfidence.HIGH)


def leg():
    return TravelLeg(
        destination(),
        destination("Bangkok", "Thailand"),
        TravelMode.FLIGHT,
        duration(),
        30,
        "Test routing fixture",
        verified=True,
    )


def trip(verified=False):
    stays = (
        DestinationStay(destination(), 1),
        DestinationStay(destination("Bangkok", "Thailand"), 2),
    )
    return ItineraryPlanningService().initialize(
        date(2026, 11, 1),
        date(2026, 11, 3),
        TravellerProfile(TravellerParty(), requirements=(TravelRequirement.FREQUENT_BREAKS,)),
        stays,
        (leg(),) if verified else (),
    )


def test_dated_journey_recalculates_disjoint_windows_and_unresolved_arrivals():
    planner = ItineraryPlanningService()
    original = trip()
    assert [stay.arrival_date for stay in original.dated_stays] == [
        date(2026, 11, 1),
        date(2026, 11, 2),
    ]
    assert original.dated_stays[0].departure_date == original.dated_stays[1].arrival_date
    assert original.dated_stays[-1].departure_date == original.end_date + timedelta(days=1)
    assert original.dated_stays[1].allocated_days == 2
    assert original.days[1].inbound_travel_leg.resolution == "unresolved"
    assert (
        FeasibilityService().assess(original.days[1], original.traveller_profile).level
        == "unresolved"
    )
    reordered = planner.update_route(original, tuple(reversed(original.stays)))
    assert reordered.dated_stays[1].arrival_date == date(2026, 11, 3)
    assert reordered.days[-1].destination.country == "Singapore"
    reallocated = planner.update_route(
        original, (replace(original.stays[0], days=2), replace(original.stays[1], days=1))
    )
    assert reallocated.dated_stays[1].arrival_date == date(2026, 11, 3)
    with pytest.raises(ValueError):
        planner.update_route(original, (original.stays[0], original.stays[0], original.stays[0]))
    single = planner.initialize(
        date(2026, 11, 1),
        date(2026, 11, 3),
        TravellerProfile(TravellerParty()),
        (DestinationStay(destination(), 3),),
    )
    assert len(single.dated_stays) == 1


def test_journey_option_is_dated_planning_evidence_only():
    option = JourneyOption("test-route", date(2026, 11, 2), leg())
    assert option.planning_only
    assert option.leg.resolution == "verified_planning"
    assert replace(leg(), duration=None).resolution == "unresolved"


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"identity": ""}, ValueError),
        ({"identity": 1}, ValueError),
        ({"departure_date": "2026-11-02"}, TypeError),
        ({"leg": object()}, TypeError),
        ({"leg": TravelLeg(destination(), destination("Bangkok", "Thailand"))}, ValueError),
        ({"leg": replace(leg(), duration=None)}, ValueError),
        (
            {
                "leg": replace(
                    leg(),
                    duration=replace(duration(), provenance=DurationProvenance.CATEGORY_HEURISTIC),
                )
            },
            ValueError,
        ),
    ],
)
def test_journey_option_rejects_unsupported_evidence(changes, error):
    with pytest.raises(error):
        JourneyOption(
            **(
                {"identity": "test-route", "departure_date": date(2026, 11, 2), "leg": leg()}
                | changes
            )
        )


class RoutingFixture:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def options(self, origin, destination, departure_date, *, limit):
        self.calls.append((origin, destination, departure_date, limit))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.parametrize(
    "result",
    [
        (),
        [],
        (object(),),
        ProviderUnavailableError("sentinel-secret"),
        (JourneyOption("route", date(2026, 11, 2), leg()),) * 4,
        (JourneyOption("route", date(2026, 11, 2), leg()),) * 2,
        (JourneyOption("route", date(2026, 11, 3), leg()),),
        (
            JourneyOption(
                "route", date(2026, 11, 2), replace(leg(), origin=destination("Hanoi", "Vietnam"))
            ),
        ),
        (
            JourneyOption(
                "route",
                date(2026, 11, 2),
                replace(leg(), destination=destination("Hanoi", "Vietnam")),
            ),
        ),
    ],
)
def test_optional_routing_degrades_without_fanout(result):
    fixture = RoutingFixture(result)
    assert (
        JourneyPlanningService(fixture).options(leg().origin, leg().destination, date(2026, 11, 2))
        == ()
    )
    assert len(fixture.calls) == 1
    assert fixture.calls[0][-1] == 3


def test_optional_routing_returns_only_applicable_options():
    option = JourneyOption("route", date(2026, 11, 2), leg())
    assert (
        JourneyPlanningService().options(leg().origin, leg().destination, date(2026, 11, 2)) == ()
    )
    assert JourneyPlanningService(RoutingFixture((option,))).options(
        leg().origin, leg().destination, date(2026, 11, 2)
    ) == (option,)


def partner():
    return Partner(
        "test-agency", "Test agency fixture", PartnerKind.AGENCY, (PartnerCapability.HANDOFF,)
    )


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"identity": ""}, ValueError),
        ({"name": 3}, ValueError),
        ({"kind": "agency"}, TypeError),
        ({"capabilities": []}, TypeError),
        ({"capabilities": ("handoff",)}, TypeError),
        ({"capabilities": (PartnerCapability.HANDOFF,) * 2}, ValueError),
    ],
)
def test_partner_capabilities_are_explicit(changes, error):
    assert partner().supports(PartnerCapability.HANDOFF)
    assert not partner().supports(PartnerCapability.TRANSPORT)
    with pytest.raises(error):
        replace(partner(), **changes)


def offer():
    return PartnerOffer(
        "external-test-offer",
        partner(),
        PartnerCapability.HANDOFF,
        OfferTargetKind.STAY,
        "stay-1",
        datetime(2026, 11, 1, tzinfo=timezone.utc),
        OfferAvailability.UNKNOWN,
    )


def test_optional_commercial_envelope_never_changes_itinerary_truth():
    value = offer()
    assert value.amount is None and value.currency is None
    assert value.availability == "unknown"
    priced = replace(
        value,
        amount=Decimal("0"),
        currency="INR",
        valid_until=value.retrieved_at + timedelta(hours=1),
    )
    assert priced.currency == "INR"
    assert "offer" not in TripSnapshot(trip()).to_json()


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"identity": ""}, ValueError),
        ({"target_identity": 3}, ValueError),
        ({"partner": object()}, TypeError),
        ({"capability": "handoff"}, TypeError),
        ({"capability": PartnerCapability.TRANSPORT}, ValueError),
        ({"target_kind": "stay"}, TypeError),
        ({"availability": "available"}, TypeError),
        ({"retrieved_at": "now"}, ValueError),
        ({"retrieved_at": datetime(2026, 11, 1)}, ValueError),
        ({"valid_until": "tomorrow"}, ValueError),
        ({"valid_until": datetime(2026, 11, 1)}, ValueError),
        ({"valid_until": datetime(2026, 10, 1, tzinfo=timezone.utc)}, ValueError),
        ({"amount": Decimal("1")}, ValueError),
        ({"currency": "INR"}, ValueError),
        ({"amount": 1, "currency": "INR"}, ValueError),
        ({"amount": Decimal("NaN"), "currency": "INR"}, ValueError),
        ({"amount": Decimal("-1"), "currency": "INR"}, ValueError),
        *[
            ({"amount": Decimal("1"), "currency": value}, ValueError)
            for value in (1, "US", "\u00dcSD", "U1D", "usd")
        ],
    ],
)
def test_commercial_envelope_rejects_invalid_claims(changes, error):
    with pytest.raises(error):
        replace(offer(), **changes)


def test_snapshot_is_deterministic_versioned_and_private():
    original = trip()
    snapshot = TripSnapshot(original)
    assert snapshot.to_json() == TripSnapshot(original).to_json()
    assert TripSnapshot.from_json(snapshot.to_json()) == snapshot
    assert "frequent_breaks" not in snapshot.to_json()
    assert original.traveller_profile.requirements
    included = TripSnapshot(original, True)
    assert TripSnapshot.from_json(included.to_json()) == included
    assert "frequent_breaks" in included.to_json()
    assert '"schema_version":1' in included.to_json()
    handoff = TripHandoff(snapshot).to_text()
    assert "excluded by traveller" in handoff and "unresolved" in handoff
    assert "Feasibility: relaxed" not in handoff
    assert "full travel requirements" in handoff
    assert "2026-11-02 to 2026-11-04" in handoff
    assert "frequent breaks" in TripHandoff(included).to_text()


@pytest.mark.parametrize("known_duration", [False, True])
def test_snapshot_activity_and_verified_journey_round_trip(known_duration):
    original = trip(True)
    activity = ItineraryActivity(
        "test-place",
        "Test <place>",
        original.days[0].destination,
        "museum",
        None if not known_duration else destination().coordinates,
        duration() if known_duration else None,
        1,
        DayPeriod.MORNING,
        0,
        AccessibilityStatus.UNKNOWN,
    )
    original = replace(
        original, days=(replace(original.days[0], activities=(activity,)), *original.days[1:])
    )
    snapshot = TripSnapshot(original)
    assert TripSnapshot.from_json(snapshot.to_json()) == snapshot
    text = TripHandoff(snapshot).to_text()
    assert "verified_planning" in text and "Test <place>" in text
    assert ("duration unknown" if not known_duration else "60–120 minutes") in text


@pytest.mark.parametrize("version", [0, 2, True, "1", None])
def test_snapshot_rejects_unsupported_version(version):
    data = json.loads(TripSnapshot(trip()).to_json())
    data["schema_version"] = version
    with pytest.raises(ValueError):
        TripSnapshot.from_json(json.dumps(data))


def test_snapshot_rejects_hidden_fields_and_invalid_disclosure():
    data = json.loads(TripSnapshot(trip()).to_json())
    for path in (
        [],
        ["itinerary"],
        ["itinerary", "traveller_profile"],
        ["itinerary", "stays", 0],
        ["itinerary", "days", 0, "destination"],
    ):
        bad = json.loads(json.dumps(data))
        node = bad
        for key in path:
            node = node[key]
        node["api_key"] = "sentinel-secret"
        with pytest.raises(ValueError):
            TripSnapshot.from_json(json.dumps(bad))
    data["itinerary"]["traveller_profile"]["requirements"] = ["frequent_breaks"]
    with pytest.raises(ValueError, match="undisclosed"):
        TripSnapshot.from_json(json.dumps(data))
    with pytest.raises(ValueError):
        TripSnapshot.from_json("[]")
    with pytest.raises(ValueError):
        TripSnapshot.from_json("{")
    with pytest.raises(TypeError):
        TripSnapshot(object())
    with pytest.raises(TypeError):
        TripSnapshot(trip(), 1)


def test_snapshot_size_bounds_and_unsupported_serialization():
    for value in (None, " " * 1_000_001):
        with pytest.raises(ValueError):
            TripSnapshot.from_json(value)
    huge = destination("x" * 1_000_001)
    original = ItineraryPlanningService().initialize(
        date(2026, 11, 1),
        date(2026, 11, 1),
        TravellerProfile(TravellerParty()),
        (DestinationStay(huge, 1),),
    )
    with pytest.raises(ValueError, match="size limit"):
        TripSnapshot(original).to_json()
    with pytest.raises(TypeError):
        _date_json(object())


def test_future_repository_uses_snapshot_contract_only_in_test():
    class RepositoryFixture:
        def __init__(self):
            self.values = {}

        def save(self, identity, snapshot):
            self.values[identity] = snapshot.to_json()

        def load(self, identity):
            value = self.values.get(identity)
            return None if value is None else TripSnapshot.from_json(value)

    fixture = RepositoryFixture()
    assert fixture.load("missing") is None
    fixture.save("test-trip", TripSnapshot(trip()))
    assert fixture.load("test-trip") == TripSnapshot(trip())


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"display_name": ""}, ValueError),
        ({"display_name": 2}, ValueError),
        ({"display_name": "x" * 81}, ValueError),
        ({"display_name": "A\nB"}, ValueError),
        ({"embedded": "true"}, TypeError),
    ],
)
def test_brand_boundary_validates_text_without_domain_changes(changes, error):
    assert BrandPresentation().display_name == "Solara"
    assert BrandPresentation("Test agency fixture", True).embedded
    with pytest.raises(error):
        BrandPresentation(**changes)
