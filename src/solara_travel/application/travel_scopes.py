"""Application services for safe geographic typeahead suggestions."""

from dataclasses import dataclass

from solara_travel.domain.destination import DestinationQuery
from solara_travel.domain.travel_scope import TravelScopeSuggestion
from solara_travel.ports.places import TravelScopeSuggestionPort


@dataclass(frozen=True, slots=True)
class TravelScopeSuggestionService:
    """Validate typeahead text and return bounded provider-independent suggestions."""

    provider: TravelScopeSuggestionPort

    def __post_init__(self) -> None:
        if not isinstance(self.provider, TravelScopeSuggestionPort):
            raise TypeError("provider must satisfy TravelScopeSuggestionPort")

    def suggest(self, query: DestinationQuery) -> tuple[TravelScopeSuggestion, ...]:
        """Return at most five unique suggestions for one validated query."""

        if not isinstance(query, DestinationQuery):
            raise TypeError("query must be DestinationQuery")
        suggestions = self.provider.suggest_travel_scopes(query)
        if not isinstance(suggestions, tuple):
            raise TypeError("suggestion provider must return a tuple")
        if not all(isinstance(item, TravelScopeSuggestion) for item in suggestions):
            raise TypeError("suggestion provider must return TravelScopeSuggestion values")
        unique: list[TravelScopeSuggestion] = []
        seen: set[str] = set()
        for suggestion in suggestions:
            identity = suggestion.display_name.casefold()
            if identity not in seen:
                unique.append(suggestion)
                seen.add(identity)
            if len(unique) == 5:
                break
        return tuple(unique)
