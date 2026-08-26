"""Tests for recommendation-request domain values."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from solara_travel.domain.destination import Destination, DestinationQuery
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.preferences import (
    TravellerInterests,
    TravellerPreferences,
)
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod


def test_recommendation_request_accepts_travel_period() -> None:
    """A recommendation request requires a valid travel period."""

    travel_period = TravelPeriod(
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 16),
    )

    request = RecommendationRequest(
        travel_period=travel_period,
    )

    assert request.travel_period == travel_period


def test_recommendation_request_uses_empty_preferences_by_default() -> None:
    """A traveller may request recommendations without stated preferences."""

    request = RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
        ),
    )

    assert request.preferences == TravellerPreferences()


def test_recommendation_request_accepts_traveller_preferences() -> None:
    """A request may include structured traveller preferences."""

    preferences = TravellerPreferences(
        interests=TravellerInterests(
            interests=("history", "food"),
        ),
        preferred_pace="moderate",
        preferred_climate="mild",
    )

    request = RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
        ),
        preferences=preferences,
    )

    assert request.preferences == preferences


def test_recommendation_request_allows_optional_target_destination() -> None:
    """A request may target a known destination when one is already selected."""

    destination = Destination(
        name="Kyoto",
        country="Japan",
        coordinates=GeoCoordinates(
            latitude=35.0116,
            longitude=135.7681,
        ),
    )

    request = RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
        ),
        destination=destination,
    )

    assert request.destination == destination


def test_recommendation_request_allows_destination_discovery() -> None:
    """A destination may be omitted when Solara is expected to discover one."""

    request = RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
        ),
    )

    assert request.destination is None


@pytest.mark.parametrize(
    "travel_period",
    [
        None,
        "2026-11-10 to 2026-11-16",
        (date(2026, 11, 10), date(2026, 11, 16)),
    ],
)
def test_recommendation_request_rejects_invalid_travel_period_type(
    travel_period: object,
) -> None:
    """Travel periods must use Solara's TravelPeriod value object."""

    with pytest.raises(
        TypeError,
        match="travel period must be TravelPeriod",
    ):
        RecommendationRequest(
            travel_period=travel_period,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "preferences",
    [
        None,
        {"preferred_pace": "moderate"},
        ("history", "food"),
    ],
)
def test_recommendation_request_rejects_invalid_preferences_type(
    preferences: object,
) -> None:
    """Preferences must use Solara's TravellerPreferences value object."""

    with pytest.raises(
        TypeError,
        match="preferences must be TravellerPreferences",
    ):
        RecommendationRequest(
            travel_period=TravelPeriod(
                start_date=date(2026, 11, 10),
                end_date=date(2026, 11, 16),
            ),
            preferences=preferences,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "destination",
    [
        "Kyoto",
        {"name": "Kyoto", "country": "Japan"},
        GeoCoordinates(latitude=35.0116, longitude=135.7681),
    ],
)
def test_recommendation_request_rejects_invalid_destination_type(
    destination: object,
) -> None:
    """A supplied destination must use Solara's Destination domain model."""

    with pytest.raises(
        TypeError,
        match="destination must be Destination or None",
    ):
        RecommendationRequest(
            travel_period=TravelPeriod(
                start_date=date(2026, 11, 10),
                end_date=date(2026, 11, 16),
            ),
            destination=destination,  # type: ignore[arg-type]
        )


def test_recommendation_request_uses_value_equality() -> None:
    """Equivalent recommendation requests should compare equally."""

    first = RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
        ),
        preferences=TravellerPreferences(
            interests=TravellerInterests(
                interests=("history",),
            ),
        ),
    )
    second = RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
        ),
        preferences=TravellerPreferences(
            interests=TravellerInterests(
                interests=("history",),
            ),
        ),
    )

    assert first == second


def test_recommendation_request_is_hashable() -> None:
    """Recommendation requests should remain usable as immutable values."""

    request = RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
        ),
        preferences=TravellerPreferences(
            preferred_pace="moderate",
        ),
    )

    assert {request, request} == {request}


def test_recommendation_request_is_immutable() -> None:
    """Recommendation request values must not change after construction."""

    request = RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 16),
        ),
    )

    with pytest.raises(FrozenInstanceError):
        request.destination = Destination(
            name="Kyoto",
            country="Japan",
            coordinates=GeoCoordinates(
                latitude=35.0116,
                longitude=135.7681,
            ),
        )


def test_recommendation_request_supports_ordered_destination_queries() -> None:
    queries = (DestinationQuery("Budapest"), DestinationQuery("Vienna"))

    request = RecommendationRequest(
        TravelPeriod(date(2026, 11, 10), date(2026, 11, 16)),
        destination_queries=queries,
    )

    assert request.destination_queries == queries


@pytest.mark.parametrize("queries", [[], "Budapest", None])
def test_recommendation_request_requires_query_tuple(queries: object) -> None:
    with pytest.raises(TypeError, match="destination_queries must be a tuple"):
        RecommendationRequest(
            TravelPeriod(date(2026, 11, 10), date(2026, 11, 16)),
            destination_queries=queries,  # type: ignore[arg-type]
        )


def test_recommendation_request_requires_destination_query_values() -> None:
    with pytest.raises(TypeError, match="every destination query"):
        RecommendationRequest(
            TravelPeriod(date(2026, 11, 10), date(2026, 11, 16)),
            destination_queries=("Budapest",),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("count", [0, 1, 5, 6, 12, 15])
def test_recommendation_request_accepts_up_to_fifteen_queries(count: int) -> None:
    request = RecommendationRequest(
        TravelPeriod(date(2026, 11, 10), date(2026, 11, 16)),
        destination_queries=tuple(DestinationQuery(str(index)) for index in range(count)),
    )

    assert len(request.destination_queries) == count


def test_recommendation_request_rejects_sixteen_queries() -> None:
    with pytest.raises(ValueError, match="at most 15"):
        RecommendationRequest(
            TravelPeriod(date(2026, 11, 10), date(2026, 11, 16)),
            destination_queries=tuple(DestinationQuery(str(index)) for index in range(16)),
        )


def test_recommendation_request_rejects_case_insensitive_duplicate_queries() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        RecommendationRequest(
            TravelPeriod(date(2026, 11, 10), date(2026, 11, 16)),
            destination_queries=(DestinationQuery("Budapest"), DestinationQuery("BUDAPEST")),
        )


def test_recommendation_request_rejects_both_destination_input_forms() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        RecommendationRequest(
            TravelPeriod(date(2026, 11, 10), date(2026, 11, 16)),
            destination=Destination("Kyoto", "Japan", GeoCoordinates(35.0, 135.0)),
            destination_queries=(DestinationQuery("Budapest"),),
        )
