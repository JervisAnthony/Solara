"""Immutable configuration for Solara's HTTP presentation layer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Minimal settings for creating the FastAPI application."""

    docs_enabled: bool = True

    def __post_init__(self) -> None:
        """Require an explicit boolean documentation policy."""

        if not isinstance(self.docs_enabled, bool):
            raise TypeError("docs_enabled must be a bool")
