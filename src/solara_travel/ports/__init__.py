"""External capability contracts exposed by Solara."""

from solara_travel.ports.discovery import DestinationCandidateProposalPort
from solara_travel.ports.errors import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.ports.narration import NarrationPrompt, NarrationProvider
from solara_travel.ports.photos import (
    PhotoAuthorAttribution,
    PhotoHandleCodec,
    PhotoMedia,
    PhotoMediaProvider,
    PostcardMetadataProvider,
    PostcardPhotoCandidate,
)
from solara_travel.ports.places import (
    AttractionDiscoveryPort,
    DestinationDiscoveryPort,
    DestinationResolutionPort,
    PlacesProvider,
    TravelScopeResolutionPort,
    TravelScopeSuggestionPort,
)
from solara_travel.ports.weather import HistoricalWeatherProvider

__all__ = [
    "AttractionDiscoveryPort",
    "DestinationDiscoveryPort",
    "DestinationResolutionPort",
    "DestinationCandidateProposalPort",
    "HistoricalWeatherProvider",
    "NarrationPrompt",
    "NarrationProvider",
    "PhotoAuthorAttribution",
    "PhotoHandleCodec",
    "PhotoMedia",
    "PhotoMediaProvider",
    "PlacesProvider",
    "TravelScopeResolutionPort",
    "TravelScopeSuggestionPort",
    "ProviderAuthenticationError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "ProviderUnavailableError",
    "PostcardMetadataProvider",
    "PostcardPhotoCandidate",
]
