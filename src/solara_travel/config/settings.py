"""Immutable settings values used by hosted application composition."""

from dataclasses import dataclass, field
from datetime import date, datetime
from math import isfinite
from numbers import Real

from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.travel import TravelPeriod


def _require_positive_finite(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise TypeError(f"{name} must be a real number")
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")


def _require_positive_int(value: int, name: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be an int")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _normalize_required_text(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank")
    return normalized


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
            _require_positive_int(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class GooglePlacesSettings:
    """Google Places credentials and bounded request policy."""

    api_key: str = field(repr=False)
    timeout_seconds: float = 10.0
    destination_page_size: int = 10
    attraction_max_results: int = 20
    attraction_radius_meters: float = 30_000.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "api_key",
            _normalize_required_text(self.api_key, "api_key"),
        )
        _require_positive_finite(self.timeout_seconds, "timeout_seconds")
        if type(self.destination_page_size) is not int:
            raise TypeError("destination_page_size must be an int")
        if not 1 <= self.destination_page_size <= 20:
            raise ValueError("destination_page_size must be between 1 and 20")
        if type(self.attraction_max_results) is not int:
            raise TypeError("attraction_max_results must be an int")
        if not 1 <= self.attraction_max_results <= 20:
            raise ValueError("attraction_max_results must be between 1 and 20")
        _require_positive_finite(
            self.attraction_radius_meters,
            "attraction_radius_meters",
        )
        if self.attraction_radius_meters > 50_000:
            raise ValueError("attraction_radius_meters must not exceed 50000")


@dataclass(frozen=True, slots=True)
class OpenMeteoSettings:
    """Open-Meteo request policy."""

    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        _require_positive_finite(self.timeout_seconds, "timeout_seconds")


@dataclass(frozen=True, slots=True)
class OpenAINarrationSettings:
    """Required OpenAI narration credentials and request policy."""

    api_key: str = field(repr=False)
    model: str
    timeout_seconds: float = 30.0
    max_output_tokens: int = 1200

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "api_key",
            _normalize_required_text(self.api_key, "api_key"),
        )
        object.__setattr__(
            self,
            "model",
            _normalize_required_text(self.model, "model"),
        )
        _require_positive_finite(self.timeout_seconds, "timeout_seconds")
        _require_positive_int(self.max_output_tokens, "max_output_tokens")


@dataclass(frozen=True, slots=True)
class RecommendationPolicySettings:
    """Historical-evidence and comfort-scoring policy for hosted MVP1."""

    historical_start_date: date = date(2020, 1, 1)
    historical_end_date: date = date(2024, 12, 31)
    comfort_min_celsius: float = 18.0
    comfort_max_celsius: float = 28.0
    comfort_tolerance_celsius: float = 10.0
    seasonal_weight: float = 1.0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.historical_start_date, date)
            or isinstance(self.historical_start_date, datetime)
            or not isinstance(self.historical_end_date, date)
            or isinstance(self.historical_end_date, datetime)
        ):
            raise TypeError("historical dates must be date values")
        TravelPeriod(self.historical_start_date, self.historical_end_date)
        TemperatureComfortRange(
            self.comfort_min_celsius,
            self.comfort_max_celsius,
            self.comfort_tolerance_celsius,
        )
        if not isinstance(self.seasonal_weight, Real) or isinstance(self.seasonal_weight, bool):
            raise TypeError("seasonal_weight must be a real number")
        if not isfinite(self.seasonal_weight):
            raise ValueError("seasonal_weight must be finite")
        if not 0 < self.seasonal_weight <= 1:
            raise ValueError("seasonal_weight must be greater than 0 and at most 1")


@dataclass(frozen=True, slots=True)
class DeploymentSettings:
    """Complete explicit configuration for one hosted application instance."""

    google_places: GooglePlacesSettings
    openai_narration: OpenAINarrationSettings
    open_meteo: OpenMeteoSettings = field(default_factory=OpenMeteoSettings)
    recommendation_policy: RecommendationPolicySettings = field(
        default_factory=RecommendationPolicySettings
    )
    public_alpha_safeguards: PublicAlphaSafeguardSettings = field(
        default_factory=PublicAlphaSafeguardSettings
    )
    docs_enabled: bool = False

    def __post_init__(self) -> None:
        expected = (
            ("google_places", GooglePlacesSettings),
            ("openai_narration", OpenAINarrationSettings),
            ("open_meteo", OpenMeteoSettings),
            ("recommendation_policy", RecommendationPolicySettings),
            ("public_alpha_safeguards", PublicAlphaSafeguardSettings),
        )
        for name, expected_type in expected:
            if not isinstance(getattr(self, name), expected_type):
                raise TypeError(f"{name} must be {expected_type.__name__}")
        if not isinstance(self.docs_enabled, bool):
            raise TypeError("docs_enabled must be a bool")
