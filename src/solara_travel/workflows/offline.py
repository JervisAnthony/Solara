"""Composition for the explicit credential-free recommendation workflow."""

from solara_travel.application.recommendation_service import RecommendationService
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.travel import TravelPeriod
from solara_travel.infrastructure.offline.dataset import OfflineTravelDataset
from solara_travel.infrastructure.offline.fixtures import (
    DEFAULT_OFFLINE_DATASET,
    DEFAULT_OFFLINE_HISTORICAL_PERIOD,
)
from solara_travel.infrastructure.offline.providers import (
    OfflineHistoricalWeatherProvider,
    OfflinePlacesProvider,
)


def build_offline_recommendation_service(
    *,
    comfort_range: TemperatureComfortRange,
    dataset: OfflineTravelDataset = DEFAULT_OFFLINE_DATASET,
    historical_period: TravelPeriod = DEFAULT_OFFLINE_HISTORICAL_PERIOD,
    seasonal_weight: float = 1.0,
) -> RecommendationService:
    """Compose the existing application service with explicit offline providers."""

    return RecommendationService(
        places_provider=OfflinePlacesProvider(dataset),
        weather_provider=OfflineHistoricalWeatherProvider(dataset),
        historical_period=historical_period,
        comfort_range=comfort_range,
        seasonal_weight=seasonal_weight,
    )
