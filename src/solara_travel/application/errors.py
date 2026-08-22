"""Application-owned errors for recommendation workflows."""

from solara_travel.domain import DestinationQuery


class DestinationNotFoundError(Exception):
    """Raised when an explicit traveller destination cannot be resolved."""

    def __init__(self, query: DestinationQuery) -> None:
        if not isinstance(query, DestinationQuery):
            raise TypeError("query must be a DestinationQuery")
        self.query = query
        super().__init__("requested destination could not be resolved")
