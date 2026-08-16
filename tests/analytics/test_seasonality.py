"""Tests for deterministic historical seasonality intelligence."""

from dataclasses import FrozenInstanceError
from datetime import date
from math import inf, nan

import pytest

from solara_travel.analytics.climate import assess_temperature_comfort
from solara_travel.analytics.scoring import ScoreComponent, SuitabilityScore
from solara_travel.analytics.seasonality import (
    SeasonalTemperatureComfortAssessment,
    SeasonalWeatherProfile,
    assess_seasonal_temperature_comfort,
    build_seasonal_weather_profile,
    seasonal_temperature_comfort_score_component,
)
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation


def _observation(
    observed_on: date,
    temperature: float = 22.0,
    humidity: float = 60.0,
    precipitation: float = 0.0,
) -> WeatherObservation:
    return WeatherObservation(
        observed_on=observed_on,
        temperature_celsius=temperature,
        relative_humidity_percent=humidity,
        precipitation_mm=precipitation,
    )


def _period(
    start: date = date(2027, 4, 10),
    end: date = date(2027, 4, 12),
) -> TravelPeriod:
    return TravelPeriod(start_date=start, end_date=end)


def _comfort_range() -> TemperatureComfortRange:
    return TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=10.0,
    )


def _profile(
    temperatures: tuple[float, ...] = (20.0, 22.0, 24.0),
) -> SeasonalWeatherProfile:
    observations = tuple(
        _observation(
            date(year, 4, 10),
            temperature=temperature,
        )
        for year, temperature in zip(
            range(2020, 2020 + len(temperatures)),
            temperatures,
            strict=True,
        )
    )
    return SeasonalWeatherProfile(
        target_period=_period(date(2027, 4, 10), date(2027, 4, 10)),
        observations=observations,
    )


def test_profile_builder_matches_single_calendar_day_across_years() -> None:
    """Historical year should not affect month/day seasonal matching."""

    matching_first = _observation(date(2020, 4, 10), 18.0)
    unrelated = _observation(date(2021, 4, 11), 19.0)
    matching_second = _observation(date(2022, 4, 10), 20.0)

    profile = build_seasonal_weather_profile(
        (matching_first, unrelated, matching_second),
        _period(date(2027, 4, 10), date(2027, 4, 10)),
    )

    assert profile.observations == (matching_first, matching_second)


def test_profile_builder_matches_multiple_target_days_and_preserves_order() -> None:
    """Matched evidence should retain its original chronological order."""

    first = _observation(date(2020, 4, 11), 18.0)
    excluded = _observation(date(2021, 5, 1), 19.0)
    second = _observation(date(2022, 4, 10), 20.0)
    third = _observation(date(2022, 4, 12), 21.0)

    profile = build_seasonal_weather_profile(
        (first, excluded, second, third),
        _period(),
    )

    assert profile.observations == (first, second, third)


def test_profile_builder_supports_cross_year_target_period() -> None:
    """December-to-January windows should match both sides of New Year."""

    december = _observation(date(2020, 12, 30), 4.0)
    excluded = _observation(date(2021, 2, 1), 5.0)
    january = _observation(date(2022, 1, 2), 6.0)

    profile = build_seasonal_weather_profile(
        (december, excluded, january),
        _period(date(2027, 12, 29), date(2028, 1, 3)),
    )

    assert profile.observations == (december, january)


def test_profile_builder_matches_leap_day_without_fabrication() -> None:
    """A target leap window should select genuine February 29 evidence."""

    february_28 = _observation(date(2019, 2, 28), 8.0)
    leap_day = _observation(date(2020, 2, 29), 9.0)
    march_1 = _observation(date(2021, 3, 1), 10.0)

    profile = build_seasonal_weather_profile(
        (february_28, leap_day, march_1),
        _period(date(2028, 2, 28), date(2028, 3, 1)),
    )

    assert profile.observations == (february_28, leap_day, march_1)


def test_profile_builder_rejects_missing_exact_leap_day_evidence() -> None:
    """An exact February 29 target requires a genuine historical leap-day record."""

    observations = (
        _observation(date(2019, 2, 28)),
        _observation(date(2021, 3, 1)),
    )

    with pytest.raises(ValueError, match="no historical observations match"):
        build_seasonal_weather_profile(
            observations,
            _period(date(2028, 2, 29), date(2028, 2, 29)),
        )


@pytest.mark.parametrize("observations", [[], None, {"weather": "sunny"}])
def test_profile_builder_rejects_non_tuple_observations(observations: object) -> None:
    """Seasonality evidence must use the immutable tuple contract."""

    with pytest.raises(TypeError, match="observations must be a tuple"):
        build_seasonal_weather_profile(
            observations,  # type: ignore[arg-type]
            _period(),
        )


def test_profile_builder_rejects_empty_observations() -> None:
    """A seasonal profile cannot be constructed without real evidence."""

    with pytest.raises(ValueError, match="observations must not be empty"):
        build_seasonal_weather_profile((), _period())


def test_profile_builder_rejects_invalid_observation_item() -> None:
    """Raw provider values and unrelated objects must not enter analytics."""

    with pytest.raises(TypeError, match="every observation"):
        build_seasonal_weather_profile(
            (_observation(date(2020, 4, 10)), {"temperature": 20.0}),  # type: ignore[arg-type]
            _period(),
        )


def test_profile_builder_rejects_invalid_target_period() -> None:
    """Calendar matching requires a Solara TravelPeriod."""

    with pytest.raises(TypeError, match="target_period must be a TravelPeriod"):
        build_seasonal_weather_profile(
            (_observation(date(2020, 4, 10)),),
            (date(2027, 4, 10), date(2027, 4, 12)),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "observations",
    [
        (
            _observation(date(2020, 4, 10)),
            _observation(date(2020, 4, 10)),
        ),
        (
            _observation(date(2021, 4, 10)),
            _observation(date(2020, 4, 10)),
        ),
        (
            _observation(date(2020, 4, 10)),
            _observation(date(2022, 4, 10)),
            _observation(date(2021, 4, 10)),
        ),
    ],
)
def test_profile_builder_rejects_non_increasing_evidence(
    observations: tuple[WeatherObservation, ...],
) -> None:
    """Duplicate, descending, or later out-of-order evidence must be rejected."""

    with pytest.raises(ValueError, match="strictly increasing by date"):
        build_seasonal_weather_profile(observations, _period())


def test_profile_builder_rejects_valid_evidence_without_match() -> None:
    """A profile must contain evidence matching the target calendar window."""

    with pytest.raises(ValueError, match="no historical observations match"):
        build_seasonal_weather_profile(
            (_observation(date(2020, 8, 1)),),
            _period(),
        )


def test_profile_exposes_evidence_depth_and_auditable_metrics() -> None:
    """Profile properties should be simple arithmetic over retained evidence."""

    observations = (
        _observation(date(2020, 4, 10), -5.0, 50.0, 0.0),
        _observation(date(2021, 4, 10), 15.0, 70.0, 3.0),
        _observation(date(2021, 4, 11), 25.0, 100.0, 6.0),
    )
    profile = build_seasonal_weather_profile(observations, _period())

    assert profile.observation_count == 3
    assert profile.historical_years == (2020, 2021)
    assert profile.historical_year_count == 2
    assert profile.mean_temperature_celsius == pytest.approx(35.0 / 3.0)
    assert profile.minimum_temperature_celsius == -5.0
    assert profile.maximum_temperature_celsius == 25.0
    assert profile.mean_relative_humidity_percent == pytest.approx(220.0 / 3.0)
    assert profile.mean_daily_precipitation_mm == 3.0


def test_single_observation_profile_exposes_exact_metrics() -> None:
    """A single historical year is sufficient and should retain exact values."""

    observation = _observation(date(2020, 4, 10), -2.0, 95.0, 0.0)
    profile = build_seasonal_weather_profile((observation,), _period())

    assert profile.observation_count == 1
    assert profile.historical_years == (2020,)
    assert profile.historical_year_count == 1
    assert profile.mean_temperature_celsius == -2.0
    assert profile.minimum_temperature_celsius == -2.0
    assert profile.maximum_temperature_celsius == -2.0
    assert profile.mean_relative_humidity_percent == 95.0
    assert profile.mean_daily_precipitation_mm == 0.0


def test_profile_direct_construction_preserves_tuple_and_value_behavior() -> None:
    """Equivalent direct profiles should be immutable, equal, and hashable."""

    observations = (_observation(date(2020, 4, 10)),)
    first = SeasonalWeatherProfile(_period(), observations)
    second = SeasonalWeatherProfile(_period(), observations)

    assert first.observations is observations
    assert first == second
    assert {first, second} == {first}

    with pytest.raises(FrozenInstanceError):
        first.observations = ()


def test_profile_direct_construction_rejects_invalid_target() -> None:
    """Direct profile construction should protect the target period type."""

    with pytest.raises(TypeError, match="target_period must be a TravelPeriod"):
        SeasonalWeatherProfile(
            target_period="April",  # type: ignore[arg-type]
            observations=(_observation(date(2020, 4, 10)),),
        )


@pytest.mark.parametrize(
    "observations",
    [
        [_observation(date(2020, 4, 10))],
        None,
    ],
)
def test_profile_direct_construction_rejects_non_tuple(
    observations: object,
) -> None:
    """Direct profiles require immutable observation tuples."""

    with pytest.raises(TypeError, match="observations must be a tuple"):
        SeasonalWeatherProfile(
            target_period=_period(),
            observations=observations,  # type: ignore[arg-type]
        )


def test_profile_direct_construction_rejects_empty_tuple() -> None:
    """Direct profiles require at least one observation."""

    with pytest.raises(ValueError, match="observations must not be empty"):
        SeasonalWeatherProfile(_period(), ())


def test_profile_direct_construction_rejects_invalid_item() -> None:
    """Direct profiles reject non-domain evidence."""

    with pytest.raises(TypeError, match="every observation"):
        SeasonalWeatherProfile(_period(), ("sunny",))  # type: ignore[arg-type]


def test_profile_direct_construction_rejects_duplicate_dates() -> None:
    """Direct profiles retain the same strict evidence-ordering invariant."""

    observation = _observation(date(2020, 4, 10))

    with pytest.raises(ValueError, match="strictly increasing by date"):
        SeasonalWeatherProfile(_period(), (observation, observation))


def test_profile_direct_construction_rejects_nonmatching_calendar_day() -> None:
    """Retained profile evidence must belong to the target calendar window."""

    with pytest.raises(ValueError, match="must match target period"):
        SeasonalWeatherProfile(
            _period(),
            (_observation(date(2020, 8, 1)),),
        )


def test_seasonal_comfort_all_comfortable() -> None:
    """All in-range temperatures should produce full seasonal comfort."""

    assessment = assess_seasonal_temperature_comfort(
        _profile((18.0, 23.0, 28.0)),
        _comfort_range(),
    )

    assert assessment.score == 1.0
    assert assessment.within_preferred_fraction == 1.0
    assert assessment.mean_deviation_celsius == 0.0


def test_seasonal_comfort_none_comfortable() -> None:
    """Temperatures at tolerance limits should produce zero comfort."""

    assessment = assess_seasonal_temperature_comfort(
        _profile((8.0, 38.0)),
        _comfort_range(),
    )

    assert assessment.score == 0.0
    assert assessment.within_preferred_fraction == 0.0
    assert assessment.mean_deviation_celsius == 10.0


def test_seasonal_comfort_mixed_evidence_uses_equal_weight() -> None:
    """Mixed daily comfort should use transparent arithmetic means."""

    assessment = assess_seasonal_temperature_comfort(
        _profile((20.0, 15.0, 38.0)),
        _comfort_range(),
    )

    assert assessment.score == pytest.approx((1.0 + 0.7 + 0.0) / 3.0)
    assert assessment.within_preferred_fraction == pytest.approx(1.0 / 3.0)
    assert assessment.mean_deviation_celsius == pytest.approx(13.0 / 3.0)


def test_seasonal_comfort_preserves_daily_assessment_order_and_boundaries() -> None:
    """Daily results should align with profile evidence at comfort boundaries."""

    profile = _profile((18.0, 28.0, 8.0, 38.0, 50.0))
    assessment = assess_seasonal_temperature_comfort(profile, _comfort_range())

    assert tuple(
        daily.observation for daily in assessment.daily_assessments
    ) == profile.observations
    assert tuple(daily.score for daily in assessment.daily_assessments) == (
        1.0,
        1.0,
        0.0,
        0.0,
        0.0,
    )


def test_assess_seasonal_comfort_rejects_invalid_profile() -> None:
    """Seasonal comfort requires an explicit seasonal profile."""

    with pytest.raises(TypeError, match="profile must be a SeasonalWeatherProfile"):
        assess_seasonal_temperature_comfort(
            profile=(_observation(date(2020, 4, 10)),),  # type: ignore[arg-type]
            comfort_range=_comfort_range(),
        )


def test_assess_seasonal_comfort_rejects_invalid_range() -> None:
    """Seasonal comfort requires an explicit temperature-comfort policy."""

    with pytest.raises(TypeError, match="comfort_range must be"):
        assess_seasonal_temperature_comfort(
            profile=_profile(),
            comfort_range=(18.0, 28.0),  # type: ignore[arg-type]
        )


def test_seasonal_assessment_direct_construction_is_value_object() -> None:
    """Valid direct assessments should match function-created immutable values."""

    profile = _profile()
    comfort_range = _comfort_range()
    daily = tuple(
        assess_temperature_comfort(observation, comfort_range)
        for observation in profile.observations
    )
    direct = SeasonalTemperatureComfortAssessment(profile, comfort_range, daily)
    derived = assess_seasonal_temperature_comfort(profile, comfort_range)

    assert direct == derived
    assert {direct, derived} == {direct}

    with pytest.raises(FrozenInstanceError):
        direct.daily_assessments = ()


def test_seasonal_assessment_rejects_invalid_direct_profile() -> None:
    """Direct assessment construction validates its profile."""

    with pytest.raises(TypeError, match="profile must be"):
        SeasonalTemperatureComfortAssessment(
            profile="seasonal",  # type: ignore[arg-type]
            comfort_range=_comfort_range(),
            daily_assessments=(),
        )


def test_seasonal_assessment_rejects_invalid_direct_range() -> None:
    """Direct assessment construction validates its comfort range."""

    with pytest.raises(TypeError, match="comfort_range must be"):
        SeasonalTemperatureComfortAssessment(
            profile=_profile(),
            comfort_range="mild",  # type: ignore[arg-type]
            daily_assessments=(),
        )


def test_seasonal_assessment_rejects_non_tuple_daily_assessments() -> None:
    """Direct assessment evidence must be immutable."""

    with pytest.raises(TypeError, match="daily_assessments must be a tuple"):
        SeasonalTemperatureComfortAssessment(
            profile=_profile(),
            comfort_range=_comfort_range(),
            daily_assessments=[],  # type: ignore[arg-type]
        )


def test_seasonal_assessment_rejects_empty_daily_assessments() -> None:
    """A seasonal assessment cannot exist without daily comfort evidence."""

    with pytest.raises(ValueError, match="must not be empty"):
        SeasonalTemperatureComfortAssessment(_profile(), _comfort_range(), ())


def test_seasonal_assessment_rejects_invalid_daily_item() -> None:
    """Every direct daily item must be a TemperatureComfortAssessment."""

    with pytest.raises(TypeError, match="every daily assessment"):
        SeasonalTemperatureComfortAssessment(
            _profile((20.0,)),
            _comfort_range(),
            ("comfortable",),  # type: ignore[arg-type]
        )


def test_seasonal_assessment_rejects_wrong_daily_count() -> None:
    """Daily assessments must correspond one-for-one with profile observations."""

    profile = _profile((20.0, 22.0))
    comfort_range = _comfort_range()
    one_daily = (
        assess_temperature_comfort(profile.observations[0], comfort_range),
    )

    with pytest.raises(ValueError, match="correspond to profile"):
        SeasonalTemperatureComfortAssessment(profile, comfort_range, one_daily)


def test_seasonal_assessment_rejects_mismatched_daily_observation() -> None:
    """Positional daily evidence must reference the matching profile observation."""

    profile = _profile((20.0,))
    comfort_range = _comfort_range()
    wrong_daily = (
        assess_temperature_comfort(
            _observation(date(2020, 4, 10), 21.0),
            comfort_range,
        ),
    )

    with pytest.raises(ValueError, match="observation must match"):
        SeasonalTemperatureComfortAssessment(profile, comfort_range, wrong_daily)


def test_seasonal_assessment_rejects_mismatched_daily_range() -> None:
    """Every daily assessment must use the parent comfort policy."""

    profile = _profile((20.0,))
    comfort_range = _comfort_range()
    other_range = TemperatureComfortRange(15.0, 25.0, 5.0)
    wrong_daily = (
        assess_temperature_comfort(profile.observations[0], other_range),
    )

    with pytest.raises(ValueError, match="comfort range must match"):
        SeasonalTemperatureComfortAssessment(profile, comfort_range, wrong_daily)


def test_seasonal_score_component_integrates_with_generic_scoring() -> None:
    """Seasonal comfort should become a stable generic scoring contribution."""

    assessment = assess_seasonal_temperature_comfort(
        _profile((20.0, 15.0)),
        _comfort_range(),
    )
    component = seasonal_temperature_comfort_score_component(assessment, 0.4)

    assert isinstance(component, ScoreComponent)
    assert component.name == "seasonal_temperature_comfort"
    assert component.score == assessment.score
    assert component.weight == 0.4

    suitability = SuitabilityScore((component,))
    assert suitability.score == assessment.score


def test_seasonal_score_component_supports_zero_weight() -> None:
    """Seasonal evidence may remain visible without affecting aggregation."""

    assessment = assess_seasonal_temperature_comfort(_profile(), _comfort_range())
    component = seasonal_temperature_comfort_score_component(assessment, 0.0)

    assert component.weight == 0.0
    assert component.weighted_contribution == 0.0


def test_seasonal_score_component_rejects_invalid_assessment() -> None:
    """Score conversion requires an explicit seasonal assessment."""

    with pytest.raises(TypeError, match="assessment must be a Seasonal"):
        seasonal_temperature_comfort_score_component(
            assessment="comfortable",  # type: ignore[arg-type]
            weight=0.5,
        )


@pytest.mark.parametrize(
    ("weight", "error_type", "message"),
    [
        (-0.1, ValueError, "between 0 and 1"),
        (1.1, ValueError, "between 0 and 1"),
        (nan, ValueError, "finite number"),
        (inf, ValueError, "finite number"),
        (True, TypeError, "real number"),
    ],
)
def test_seasonal_score_component_delegates_weight_validation(
    weight: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """Generic ScoreComponent validation should remain authoritative."""

    assessment = assess_seasonal_temperature_comfort(_profile(), _comfort_range())

    with pytest.raises(error_type, match=message):
        seasonal_temperature_comfort_score_component(
            assessment,
            weight,  # type: ignore[arg-type]
        )


def test_public_analytics_exports_remain_available() -> None:
    """New and existing analytics APIs should remain intentionally importable."""

    import solara_travel.analytics as analytics

    assert analytics.SeasonalWeatherProfile is SeasonalWeatherProfile
    assert (
        analytics.SeasonalTemperatureComfortAssessment
        is SeasonalTemperatureComfortAssessment
    )
    assert analytics.build_seasonal_weather_profile is build_seasonal_weather_profile
    assert (
        analytics.assess_seasonal_temperature_comfort
        is assess_seasonal_temperature_comfort
    )
    assert (
        analytics.seasonal_temperature_comfort_score_component
        is seasonal_temperature_comfort_score_component
    )
    assert analytics.ScoreComponent is ScoreComponent
    assert analytics.SuitabilityScore is SuitabilityScore
    assert analytics.TemperatureComfortAssessment.__name__ == (
        "TemperatureComfortAssessment"
    )
    assert analytics.assess_temperature_comfort is assess_temperature_comfort
    assert analytics.temperature_comfort_score_component.__name__ == (
        "temperature_comfort_score_component"
    )
