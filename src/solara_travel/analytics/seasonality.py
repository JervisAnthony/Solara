"""Deterministic seasonal intelligence derived from historical weather evidence."""

from dataclasses import dataclass
from datetime import timedelta
from statistics import fmean

from solara_travel.analytics.climate import (
    TemperatureComfortAssessment,
    assess_temperature_comfort,
)
from solara_travel.analytics.scoring import ScoreComponent
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation


@dataclass(frozen=True, slots=True)
class SeasonalWeatherProfile:
    """Immutable historical weather evidence for a target calendar window."""

    target_period: TravelPeriod
    observations: tuple[WeatherObservation, ...]

    def __post_init__(self) -> None:
        """Validate the target period and retained seasonal evidence."""

        _validate_target_period(self.target_period)
        _validate_observations(self.observations)
        target_keys = _target_calendar_day_keys(self.target_period)

        if any(
            _calendar_day_key(observation) not in target_keys
            for observation in self.observations
        ):
            raise ValueError(
                "profile observations must match target period calendar days"
            )

    @property
    def observation_count(self) -> int:
        """Return the number of historical observations in the profile."""

        return len(self.observations)

    @property
    def historical_years(self) -> tuple[int, ...]:
        """Return the distinct represented historical years in ascending order."""

        return tuple(sorted({observation.observed_on.year for observation in self.observations}))

    @property
    def historical_year_count(self) -> int:
        """Return the number of distinct represented historical years."""

        return len(self.historical_years)

    @property
    def mean_temperature_celsius(self) -> float:
        """Return the arithmetic mean historical temperature."""

        return fmean(
            observation.temperature_celsius
            for observation in self.observations
        )

    @property
    def minimum_temperature_celsius(self) -> float:
        """Return the minimum observed historical temperature."""

        return min(
            observation.temperature_celsius
            for observation in self.observations
        )

    @property
    def maximum_temperature_celsius(self) -> float:
        """Return the maximum observed historical temperature."""

        return max(
            observation.temperature_celsius
            for observation in self.observations
        )

    @property
    def mean_relative_humidity_percent(self) -> float:
        """Return the arithmetic mean historical relative humidity."""

        return fmean(
            observation.relative_humidity_percent
            for observation in self.observations
        )

    @property
    def mean_daily_precipitation_mm(self) -> float:
        """Return the arithmetic mean historical daily precipitation."""

        return fmean(
            observation.precipitation_mm
            for observation in self.observations
        )


@dataclass(frozen=True, slots=True)
class SeasonalTemperatureComfortAssessment:
    """Explainable comfort assessment across historical seasonal evidence."""

    profile: SeasonalWeatherProfile
    comfort_range: TemperatureComfortRange
    daily_assessments: tuple[TemperatureComfortAssessment, ...]

    def __post_init__(self) -> None:
        """Reject inconsistent manually constructed seasonal assessments."""

        if not isinstance(self.profile, SeasonalWeatherProfile):
            raise TypeError("profile must be a SeasonalWeatherProfile")

        if not isinstance(self.comfort_range, TemperatureComfortRange):
            raise TypeError(
                "comfort_range must be a TemperatureComfortRange"
            )

        if not isinstance(self.daily_assessments, tuple):
            raise TypeError("daily_assessments must be a tuple")

        if not self.daily_assessments:
            raise ValueError("daily_assessments must not be empty")

        if not all(
            isinstance(assessment, TemperatureComfortAssessment)
            for assessment in self.daily_assessments
        ):
            raise TypeError(
                "every daily assessment must be a TemperatureComfortAssessment"
            )

        if len(self.daily_assessments) != self.profile.observation_count:
            raise ValueError(
                "daily assessments must correspond to profile observations"
            )

        for observation, assessment in zip(
            self.profile.observations,
            self.daily_assessments,
            strict=True,
        ):
            if assessment.observation != observation:
                raise ValueError(
                    "daily assessment observation must match profile observation"
                )

            if assessment.comfort_range != self.comfort_range:
                raise ValueError(
                    "daily assessment comfort range must match parent comfort range"
                )

    @property
    def score(self) -> float:
        """Return the equally weighted mean daily comfort score."""

        return fmean(
            assessment.score
            for assessment in self.daily_assessments
        )

    @property
    def within_preferred_fraction(self) -> float:
        """Return the fraction of observations inside the preferred range."""

        within_count = sum(
            assessment.within_preferred_range
            for assessment in self.daily_assessments
        )
        return within_count / len(self.daily_assessments)

    @property
    def mean_deviation_celsius(self) -> float:
        """Return the arithmetic mean deviation from the preferred range."""

        return fmean(
            assessment.deviation_celsius
            for assessment in self.daily_assessments
        )


def build_seasonal_weather_profile(
    observations: tuple[WeatherObservation, ...],
    target_period: TravelPeriod,
) -> SeasonalWeatherProfile:
    """Select historical evidence matching the target period's calendar days."""

    _validate_target_period(target_period)
    _validate_observations(observations)
    target_keys = _target_calendar_day_keys(target_period)
    matched_observations = tuple(
        observation
        for observation in observations
        if _calendar_day_key(observation) in target_keys
    )

    if not matched_observations:
        raise ValueError("no historical observations match target period")

    return SeasonalWeatherProfile(
        target_period=target_period,
        observations=matched_observations,
    )


def assess_seasonal_temperature_comfort(
    profile: SeasonalWeatherProfile,
    comfort_range: TemperatureComfortRange,
) -> SeasonalTemperatureComfortAssessment:
    """Assess historical seasonal temperatures using explicit comfort policy."""

    if not isinstance(profile, SeasonalWeatherProfile):
        raise TypeError("profile must be a SeasonalWeatherProfile")

    if not isinstance(comfort_range, TemperatureComfortRange):
        raise TypeError(
            "comfort_range must be a TemperatureComfortRange"
        )

    daily_assessments = tuple(
        assess_temperature_comfort(observation, comfort_range)
        for observation in profile.observations
    )

    return SeasonalTemperatureComfortAssessment(
        profile=profile,
        comfort_range=comfort_range,
        daily_assessments=daily_assessments,
    )


def seasonal_temperature_comfort_score_component(
    assessment: SeasonalTemperatureComfortAssessment,
    weight: float,
) -> ScoreComponent:
    """Convert seasonal comfort evidence into a generic score component."""

    if not isinstance(assessment, SeasonalTemperatureComfortAssessment):
        raise TypeError(
            "assessment must be a SeasonalTemperatureComfortAssessment"
        )

    return ScoreComponent(
        name="seasonal_temperature_comfort",
        score=assessment.score,
        weight=weight,
    )


def _validate_target_period(target_period: object) -> None:
    """Require a Solara-owned inclusive travel period."""

    if not isinstance(target_period, TravelPeriod):
        raise TypeError("target_period must be a TravelPeriod")


def _validate_observations(observations: object) -> None:
    """Validate immutable, non-empty, chronologically unique evidence."""

    if not isinstance(observations, tuple):
        raise TypeError("observations must be a tuple")

    if not observations:
        raise ValueError("observations must not be empty")

    if not all(
        isinstance(observation, WeatherObservation)
        for observation in observations
    ):
        raise TypeError("every observation must be a WeatherObservation")

    if any(
        current.observed_on <= previous.observed_on
        for previous, current in zip(
            observations,
            observations[1:],
            strict=False,
        )
    ):
        raise ValueError("observations must be strictly increasing by date")


def _target_calendar_day_keys(
    target_period: TravelPeriod,
) -> frozenset[tuple[int, int]]:
    """Return inclusive month/day keys represented by a target period."""

    keys: set[tuple[int, int]] = set()
    current_date = target_period.start_date

    while current_date <= target_period.end_date:
        keys.add((current_date.month, current_date.day))
        current_date += timedelta(days=1)

    return frozenset(keys)


def _calendar_day_key(observation: WeatherObservation) -> tuple[int, int]:
    """Return the seasonal month/day key for one observation."""

    return observation.observed_on.month, observation.observed_on.day
