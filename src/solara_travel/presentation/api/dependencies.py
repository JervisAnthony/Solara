"""Immutable application-service dependencies for FastAPI composition."""

from dataclasses import dataclass

from solara_travel.application import (
    RecommendationNarrationService,
    RecommendationService,
)


@dataclass(frozen=True, slots=True)
class ApiDependencies:
    """Optional services supplied explicitly to one FastAPI application."""

    recommendation_service: RecommendationService | None = None
    narration_service: RecommendationNarrationService | None = None

    def __post_init__(self) -> None:
        """Validate service types and the narration dependency invariant."""

        if self.recommendation_service is not None and not isinstance(
            self.recommendation_service, RecommendationService
        ):
            raise TypeError("recommendation_service must be RecommendationService or None")

        if self.narration_service is not None and not isinstance(
            self.narration_service, RecommendationNarrationService
        ):
            raise TypeError("narration_service must be RecommendationNarrationService or None")

        if self.narration_service is not None and self.recommendation_service is None:
            raise ValueError("narration_service requires recommendation_service")
