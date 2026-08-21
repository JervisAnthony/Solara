"""Tests for explicit HTTP/domain recommendation mappings."""

from datetime import date

import pytest

from solara_travel.application import RecommendationNarration
from solara_travel.domain import (
    Destination,
    GeoCoordinates,
    RecommendationRequest,
    TemperatureComfortRange,
    TravellerInterests,
    TravellerPreferences,
    TravelPeriod,
)
from solara_travel.presentation.api.recommendation_mapping import (
    recommendation_result_to_response,
    to_domain_recommendation_request,
)
from solara_travel.presentation.api.recommendation_schemas import RecommendationRequestBody
from solara_travel.workflows import build_offline_recommendation_service


def _request_body(**overrides: object) -> RecommendationRequestBody:
    values: dict[str, object] = {
        "travel_period": {"start_date": "2026-04-10", "end_date": "2026-04-12"},
        "preferences": {
            "interests": ["History", "Nature"],
            "preferred_pace": " Relaxed ",
            "preferred_climate": "Warm",
        },
        "destination": {
            "name": "Sunspire Bay",
            "country": "Fixtureland",
            "coordinates": {"latitude": 12, "longitude": 24.0},
        },
    }
    values.update(overrides)
    return RecommendationRequestBody.model_validate(values)


def test_request_mapping_builds_explicit_domain_values_without_normalization() -> None:
    mapped = to_domain_recommendation_request(_request_body())

    assert mapped == RecommendationRequest(
        travel_period=TravelPeriod(date(2026, 4, 10), date(2026, 4, 12)),
        preferences=TravellerPreferences(
            interests=TravellerInterests(("History", "Nature")),
            preferred_pace=" Relaxed ",
            preferred_climate="Warm",
        ),
        destination=Destination(
            "Sunspire Bay",
            "Fixtureland",
            GeoCoordinates(12.0, 24.0),
        ),
    )


def test_request_mapping_uses_default_preferences_and_discovery_mode() -> None:
    mapped = to_domain_recommendation_request(
        RecommendationRequestBody.model_validate(
            {"travel_period": {"start_date": "2026-04-10", "end_date": "2026-04-12"}}
        )
    )

    assert mapped.preferences == TravellerPreferences()
    assert mapped.destination is None


def test_response_mapping_preserves_authoritative_order_values_and_selected_evidence() -> None:
    request = RecommendationRequest(
        TravelPeriod(date(2026, 4, 10), date(2026, 4, 12)),
        TravellerPreferences(TravellerInterests(("nature",)), "relaxed", "warm"),
    )
    result = build_offline_recommendation_service(
        comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0)
    ).recommend(request)

    response = recommendation_result_to_response(
        result,
        RecommendationNarration("Grounded result explanation."),
    )

    assert response.request.travel_period.start_date == date(2026, 4, 10)
    assert response.request.preferences.interests == ["nature"]
    assert response.request.destination is None
    assert response.recommendation_count == 3
    assert response.has_recommendations
    assert response.has_narration
    assert response.narration == "Grounded result explanation."
    assert [item.rank for item in response.recommendations] == [1, 2, 3]
    assert [item.destination.name for item in response.recommendations] == [
        "Sunspire Bay",
        "Mistral Hollow",
        "Frostglass Vale",
    ]
    assert [item.score for item in response.recommendations] == pytest.approx([1.0, 0.68, 0.0])
    first = response.recommendations[0]
    component = result.recommendations[0].components[0]
    assert first.components[0].weighted_contribution == component.weighted_contribution
    assert [attraction.name for attraction in first.evidence.attractions] == [
        "Prism Tidewalk",
        "Lantern Cloud Garden",
    ]
    assert first.evidence.seasonal_weather.target_period == response.request.travel_period
    assert first.evidence.seasonal_weather.observation_count == 15
    assert first.evidence.seasonal_weather.historical_years == [2020, 2021, 2022, 2023, 2024]
    assert first.evidence.temperature_comfort.comfort_range.minimum_celsius == 18.0
    dumped = response.model_dump()
    assert "observations" not in repr(dumped)
    assert "provider" not in repr(dumped).casefold()


def test_response_mapping_represents_empty_result_without_narration() -> None:
    from solara_travel.infrastructure.offline import OfflineTravelDataset

    result = build_offline_recommendation_service(
        comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0),
        dataset=OfflineTravelDataset(()),
    ).recommend(RecommendationRequest(TravelPeriod(date(2026, 4, 10), date(2026, 4, 12))))

    response = recommendation_result_to_response(result, None)

    assert response.recommendation_count == 0
    assert not response.has_recommendations
    assert response.recommendations == []
    assert not response.has_narration
    assert response.narration is None
