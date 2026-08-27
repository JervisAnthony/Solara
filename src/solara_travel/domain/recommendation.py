"""Recommendation-request value objects used by the Solara domain."""

from dataclasses import dataclass, field

from solara_travel.domain.constraints import ClimateConstraint
from solara_travel.domain.destination import Destination, DestinationQuery
from solara_travel.domain.preferences import TravellerPreferences
from solara_travel.domain.travel import TravelPeriod

MAX_SELECTED_TRAVEL_SCOPES = 15


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
    destination_queries: tuple[DestinationQuery, ...] = ()
    climate_constraint: ClimateConstraint | None = None

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

        if not isinstance(self.destination_queries, tuple):
            raise TypeError("destination_queries must be a tuple")
        if not all(isinstance(query, DestinationQuery) for query in self.destination_queries):
            raise TypeError("every destination query must be a DestinationQuery")
        if len(self.destination_queries) > MAX_SELECTED_TRAVEL_SCOPES:
            raise ValueError(
                f"destination_queries must contain at most {MAX_SELECTED_TRAVEL_SCOPES} values"
            )
        if self.destination is not None and self.destination_queries:
            raise ValueError("destination and destination_queries are mutually exclusive")

        if self.climate_constraint is not None and not isinstance(
            self.climate_constraint, ClimateConstraint
        ):
            raise TypeError("climate_constraint must be ClimateConstraint or None")

        normalized_queries = tuple(query.value.casefold() for query in self.destination_queries)
        if len(normalized_queries) != len(set(normalized_queries)):
            raise ValueError("destination_queries must not contain duplicates")
