"""External capability contracts exposed by Solara."""

from solara_travel.ports.errors import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.ports.places import (
    AttractionDiscoveryPort,
    DestinationDiscoveryPort,
    PlacesProvider,
)

__all__ = [
    "AttractionDiscoveryPort",
    "DestinationDiscoveryPort",
    "PlacesProvider",
    "ProviderAuthenticationError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "ProviderUnavailableError",
]