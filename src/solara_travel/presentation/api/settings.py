"""Immutable configuration for Solara's HTTP presentation layer."""

from dataclasses import dataclass, field

from solara_travel.config.settings import PublicAlphaSafeguardSettings


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Minimal settings for creating the FastAPI application."""

    docs_enabled: bool = True
    public_alpha_safeguards: PublicAlphaSafeguardSettings = field(
        default_factory=PublicAlphaSafeguardSettings
    )

    def __post_init__(self) -> None:
        """Require an explicit boolean documentation policy."""

        if not isinstance(self.docs_enabled, bool):
            raise TypeError("docs_enabled must be a bool")
        if not isinstance(self.public_alpha_safeguards, PublicAlphaSafeguardSettings):
            raise TypeError("public_alpha_safeguards must be PublicAlphaSafeguardSettings")
