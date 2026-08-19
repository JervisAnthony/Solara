"""Explicit synthetic offline infrastructure exposed by Solara."""

from solara_travel.infrastructure.offline.dataset import (
    OfflineDestinationFixture,
    OfflineTravelDataset,
)
from solara_travel.infrastructure.offline.fixtures import (
    DEFAULT_OFFLINE_DATASET,
    DEFAULT_OFFLINE_HISTORICAL_PERIOD,
)
from solara_travel.infrastructure.offline.providers import (
    OfflineHistoricalWeatherProvider,
    OfflinePlacesProvider,
)

__all__ = [
    "DEFAULT_OFFLINE_DATASET",
    "DEFAULT_OFFLINE_HISTORICAL_PERIOD",
    "OfflineDestinationFixture",
    "OfflineHistoricalWeatherProvider",
    "OfflinePlacesProvider",
    "OfflineTravelDataset",
]
