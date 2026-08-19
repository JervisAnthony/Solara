"""External capability contracts exposed by Solara."""

from solara_travel.ports.errors import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.ports.narration import NarrationPrompt, NarrationProvider
from solara_travel.ports.places import (
    AttractionDiscoveryPort,
    DestinationDiscoveryPort,
    PlacesProvider,
)
from solara_travel.ports.weather import HistoricalWeatherProvider

__all__ = [
    "AttractionDiscoveryPort",
    "DestinationDiscoveryPort",
    "HistoricalWeatherProvider",
    "NarrationPrompt",
    "NarrationProvider",
    "PlacesProvider",
    "ProviderAuthenticationError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "ProviderUnavailableError",
]
