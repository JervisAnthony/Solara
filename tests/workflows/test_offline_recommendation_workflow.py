"""End-to-end tests for explicit offline recommendation composition."""

from datetime import date

import pytest

from solara_travel.application import RecommendationService
from solara_travel.domain import (
    Attraction,
    Destination,
    GeoCoordinates,
    RecommendationRequest,
    TemperatureComfortRange,
    TravelPeriod,
    WeatherObservation,
)
from solara_travel.infrastructure.offline import (
    DEFAULT_OFFLINE_DATASET,
    DEFAULT_OFFLINE_HISTORICAL_PERIOD,
    OfflineDestinationFixture,
    OfflineHistoricalWeatherProvider,
    OfflinePlacesProvider,
    OfflineTravelDataset,
)
from solara_travel.workflows import build_offline_recommendation_service


def _target_period() -> TravelPeriod:
    return TravelPeriod(date(2026, 4, 10), date(2026, 4, 12))


def _comfort_range() -> TemperatureComfortRange:
    return TemperatureComfortRange(18.0, 28.0, 10.0)


def _request(destination: Destination | None = None) -> RecommendationRequest:
    return RecommendationRequest(_target_period(), destination=destination)


def _custom_dataset() -> OfflineTravelDataset:
    destination = Destination(
        "Custom Fixture Port",
        "Fixtureland",
        GeoCoordinates(5.0, 6.0),
    )
    attraction = Attraction(
        "Custom Clock",
        "synthetic landmark",
        GeoCoordinates(5.1, 6.1),
    )
    weather = (
        WeatherObservation(date(2020, 4, 10), 24.0, 50.0, 0.0),
        WeatherObservation(date(2020, 4, 11), 24.0, 51.0, 0.1),
        WeatherObservation(date(2020, 4, 12), 24.0, 52.0, 0.2),
    )
    return OfflineTravelDataset((OfflineDestinationFixture(destination, (attraction,), weather),))


def test_factory_returns_existing_recommendation_service_with_explicit_policy() -> None:
    comfort_range = _comfort_range()

    service = build_offline_recommendation_service(comfort_range=comfort_range)

    assert isinstance(service, RecommendationService)
    assert isinstance(service.places_provider, OfflinePlacesProvider)
    assert isinstance(service.weather_provider, OfflineHistoricalWeatherProvider)
    assert service.places_provider.dataset is DEFAULT_OFFLINE_DATASET
    assert service.weather_provider.dataset is DEFAULT_OFFLINE_DATASET
    assert service.historical_period is DEFAULT_OFFLINE_HISTORICAL_PERIOD
    assert service.comfort_range is comfort_range


def test_default_offline_workflow_runs_real_pipeline_end_to_end() -> None:
    service = build_offline_recommendation_service(comfort_range=_comfort_range())

    result = service.recommend(_request())

    assert result.recommendation_count == 3
    assert result.has_recommendations
    assert tuple(recommendation.destination.name for recommendation in result.recommendations) == (
        "Sunspire Bay",
        "Mistral Hollow",
        "Frostglass Vale",
    )
    assert tuple(
        recommendation.score for recommendation in result.recommendations
    ) == pytest.approx((1.0, 0.68, 0.0))
    for recommendation in result.recommendations:
        assert len(recommendation.evidence.attractions) == 2
        assert recommendation.evidence.seasonal_weather.target_period == _target_period()
        assert recommendation.evidence.seasonal_weather.observation_count == 15
        assert recommendation.evidence.seasonal_weather.historical_years == (
            2020,
            2021,
            2022,
            2023,
            2024,
        )
        assert recommendation.components[0].name == "seasonal_temperature_comfort"
        assert (
            recommendation.components[0].score
            == recommendation.evidence.seasonal_temperature_comfort.score
        )


def test_default_offline_workflow_is_repeatable() -> None:
    first_service = build_offline_recommendation_service(comfort_range=_comfort_range())
    second_service = build_offline_recommendation_service(comfort_range=_comfort_range())

    assert first_service.recommend(_request()) == second_service.recommend(_request())


def test_preselected_destination_uses_fixture_evidence() -> None:
    destination = DEFAULT_OFFLINE_DATASET.fixtures[1].destination
    service = build_offline_recommendation_service(comfort_range=_comfort_range())

    result = service.recommend(_request(destination))

    assert result.recommendation_count == 1
    assert result.recommendations[0].destination is destination
    assert (
        result.recommendations[0].evidence.attractions
        is DEFAULT_OFFLINE_DATASET.fixtures[1].attractions
    )
    assert result.recommendations[0].evidence.seasonal_weather.observation_count == 15


def test_empty_dataset_produces_empty_result_without_fallback() -> None:
    service = build_offline_recommendation_service(
        comfort_range=_comfort_range(), dataset=OfflineTravelDataset(())
    )

    result = service.recommend(_request())

    assert result.recommendations == ()
    assert result.recommendation_count == 0
    assert not result.has_recommendations


def test_unsupported_calendar_window_does_not_fabricate_evidence() -> None:
    service = build_offline_recommendation_service(comfort_range=_comfort_range())
    request = RecommendationRequest(TravelPeriod(date(2026, 5, 1), date(2026, 5, 2)))

    with pytest.raises(ValueError, match="no historical observations match target period"):
        service.recommend(request)


def test_caller_supplied_comfort_policy_changes_ranking() -> None:
    cold_comfort = TemperatureComfortRange(0.0, 10.0, 10.0)
    service = build_offline_recommendation_service(comfort_range=cold_comfort)

    result = service.recommend(_request())

    assert service.comfort_range is cold_comfort
    assert result.recommendations[0].destination.name == "Frostglass Vale"


def test_seasonal_weight_passes_through_to_existing_scoring() -> None:
    service = build_offline_recommendation_service(
        comfort_range=_comfort_range(), seasonal_weight=0.4
    )

    result = service.recommend(_request())

    assert service.seasonal_weight == 0.4
    assert all(
        recommendation.components[0].weight == 0.4 for recommendation in result.recommendations
    )


@pytest.mark.parametrize("weight", [-0.1, 1.1, "heavy"])
def test_invalid_seasonal_weight_uses_existing_validation(weight: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        build_offline_recommendation_service(
            comfort_range=_comfort_range(),
            seasonal_weight=weight,  # type: ignore[arg-type]
        )


def test_custom_dataset_is_used_instead_of_default_dataset() -> None:
    dataset = _custom_dataset()
    service = build_offline_recommendation_service(
        comfort_range=_comfort_range(),
        dataset=dataset,
        historical_period=TravelPeriod(date(2020, 4, 10), date(2020, 4, 12)),
    )

    result = service.recommend(_request())

    assert result.recommendation_count == 1
    assert result.recommendations[0].destination is dataset.fixtures[0].destination
    assert result.recommendations[0].evidence.attractions is dataset.fixtures[0].attractions


def test_public_offline_imports_are_available() -> None:
    assert DEFAULT_OFFLINE_DATASET.fixtures
    assert isinstance(DEFAULT_OFFLINE_HISTORICAL_PERIOD, TravelPeriod)
    assert OfflineDestinationFixture.__name__ == "OfflineDestinationFixture"
    assert OfflineHistoricalWeatherProvider.__name__ == "OfflineHistoricalWeatherProvider"
    assert OfflinePlacesProvider.__name__ == "OfflinePlacesProvider"
    assert OfflineTravelDataset.__name__ == "OfflineTravelDataset"
    assert callable(build_offline_recommendation_service)
