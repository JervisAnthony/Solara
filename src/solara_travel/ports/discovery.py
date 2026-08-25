"""Provider-independent contracts for AI-assisted locality proposal."""

from typing import Protocol, runtime_checkable

from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel_intent import DestinationCandidateProposal
from solara_travel.domain.travel_scope import TravelScope


@runtime_checkable
class DestinationCandidateProposalPort(Protocol):
    """Propose bounded locality names without deciding evidence or rank."""

    def propose_candidates(
        self,
        request: RecommendationRequest,
        scope: TravelScope | None,
    ) -> DestinationCandidateProposal:
        """Return structured locality names for mandatory geographic validation."""
        ...
