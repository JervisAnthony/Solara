"""Application recommendation values and services exposed by Solara."""

from solara_travel.application.narration import (
    NarratedRecommendationResult,
    RecommendationNarration,
    RecommendationNarrationService,
)
from solara_travel.application.recommendation_service import RecommendationService
from solara_travel.application.results import (
    DestinationRecommendation,
    RecommendationEvidence,
    RecommendationResult,
)

__all__ = [
    "DestinationRecommendation",
    "NarratedRecommendationResult",
    "RecommendationEvidence",
    "RecommendationNarration",
    "RecommendationNarrationService",
    "RecommendationResult",
    "RecommendationService",
]
