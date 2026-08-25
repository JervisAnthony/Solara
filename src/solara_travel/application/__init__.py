"""Application recommendation values and services exposed by Solara."""

from solara_travel.application.errors import (
    BroadScopeCombinationError,
    DestinationDiscoveryUnavailableError,
    DestinationNotFoundError,
)
from solara_travel.application.narration import (
    NarratedRecommendationResult,
    RecommendationNarration,
    RecommendationNarrationService,
)
from solara_travel.application.postcards import (
    DestinationPostcards,
    InvalidPhotoHandleError,
    PhotoDeliveryService,
    PostcardCollection,
    PostcardEnrichmentService,
    PostcardPhoto,
)
from solara_travel.application.recommendation_service import (
    RecommendationPlan,
    RecommendationService,
)
from solara_travel.application.results import (
    DestinationRecommendation,
    RecommendationEvidence,
    RecommendationResult,
)
from solara_travel.application.travel_scopes import TravelScopeSuggestionService
from solara_travel.application.wayfinder import (
    WayfinderDestinationNote,
    WayfinderNarrative,
    parse_wayfinder_narrative,
)

__all__ = [
    "DestinationRecommendation",
    "DestinationDiscoveryUnavailableError",
    "DestinationNotFoundError",
    "BroadScopeCombinationError",
    "NarratedRecommendationResult",
    "DestinationPostcards",
    "InvalidPhotoHandleError",
    "PhotoDeliveryService",
    "PostcardCollection",
    "PostcardEnrichmentService",
    "PostcardPhoto",
    "RecommendationEvidence",
    "RecommendationNarration",
    "RecommendationNarrationService",
    "RecommendationResult",
    "RecommendationPlan",
    "RecommendationService",
    "TravelScopeSuggestionService",
    "WayfinderDestinationNote",
    "WayfinderNarrative",
    "parse_wayfinder_narrative",
]
