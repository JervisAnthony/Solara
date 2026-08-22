"""Immutable configuration for Solara's HTTP presentation layer."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PublicAlphaSafeguardSettings:
    """Conservative process-local limits for the hosted public alpha."""

    recommendation_rate_limit: int = 12
    recommendation_rate_window_seconds: int = 60
    recommendation_budget_limit: int = 60
    recommendation_budget_window_seconds: int = 3600
    recommendation_concurrency_limit: int = 2
    feedback_rate_limit: int = 30
    feedback_rate_window_seconds: int = 60
    narration_budget_limit: int = 30
    narration_budget_window_seconds: int = 3600

    def __post_init__(self) -> None:
        """Reject malformed or non-positive guardrail configuration."""

        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if type(value) is not int:
                raise TypeError(f"{field_name} must be an int")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")


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
