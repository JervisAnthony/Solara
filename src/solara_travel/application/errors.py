"""Application-owned errors for recommendation workflows."""

from solara_travel.domain import DestinationQuery


class DestinationNotFoundError(Exception):
    """Raised when an explicit traveller destination cannot be resolved."""

    def __init__(self, query: DestinationQuery, suggestions: tuple[str, ...] = ()) -> None:
        if not isinstance(query, DestinationQuery):
            raise TypeError("query must be a DestinationQuery")
        if not isinstance(suggestions, tuple) or not all(
            isinstance(suggestion, str) and suggestion.strip() for suggestion in suggestions
        ):
            raise TypeError("suggestions must be a tuple of non-blank strings")
        self.query = query
        self.suggestions = suggestions
        super().__init__("requested destination could not be resolved")


class BroadScopeCombinationError(ValueError):
    """Raised when a request mixes a broad scope with another destination."""


class DestinationDiscoveryUnavailableError(RuntimeError):
    """Raised when broad/open candidate discovery is not configured or fails safely."""
