"""Recommendation-request value objects used by the Solara domain."""

from dataclasses import dataclass, field

from solara_travel.domain.destination import Destination
from solara_travel.domain.preferences import TravellerPreferences
from solara_travel.domain.travel import TravelPeriod


@dataclass(frozen=True, slots=True)
class RecommendationRequest:
    """An immutable request for travel recommendations.

    A request always contains a travel period and may optionally include
    traveller preferences or a destination that has already been selected.

    When no destination is supplied, the request represents destination
    discovery rather than recommendations for a known destination.
    """

    travel_period: TravelPeriod
    preferences: TravellerPreferences = field(default_factory=TravellerPreferences)
    destination: Destination | None = None

    def __post_init__(self) -> None:
        """Validate recommendation-request domain values."""

        if not isinstance(self.travel_period, TravelPeriod):
            raise TypeError("travel period must be TravelPeriod")

        if not isinstance(self.preferences, TravellerPreferences):
            raise TypeError("preferences must be TravellerPreferences")

        if self.destination is not None and not isinstance(
            self.destination,
            Destination,
        ):
            raise TypeError("destination must be Destination or None")