"""Deterministic tests for process-local public-alpha safeguards."""

from dataclasses import FrozenInstanceError
from threading import Barrier, Thread

import pytest

from solara_travel.presentation.api import PublicAlphaSafeguardSettings, create_app
from solara_travel.presentation.api.safeguards import (
    ApiSafeguards,
    RecommendationLease,
    SafeguardRejection,
)


class FakeClock:
    """Controllable monotonic clock with no real sleeping."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _settings(**overrides: int) -> PublicAlphaSafeguardSettings:
    values = {
        "recommendation_rate_limit": 2,
        "recommendation_rate_window_seconds": 10,
        "recommendation_budget_limit": 4,
        "recommendation_budget_window_seconds": 100,
        "recommendation_concurrency_limit": 2,
        "feedback_rate_limit": 2,
        "feedback_rate_window_seconds": 10,
        "narration_budget_limit": 2,
        "narration_budget_window_seconds": 10,
    }
    values.update(overrides)
    return PublicAlphaSafeguardSettings(**values)


def _accept_and_release(safeguards: ApiSafeguards) -> None:
    admission = safeguards.admit_recommendation()
    assert isinstance(admission, RecommendationLease)
    with admission:
        pass


def test_default_settings_match_the_approved_public_alpha_guardrails() -> None:
    settings = PublicAlphaSafeguardSettings()

    assert settings.recommendation_rate_limit == 12
    assert settings.recommendation_rate_window_seconds == 60
    assert settings.recommendation_budget_limit == 60
    assert settings.recommendation_budget_window_seconds == 3600
    assert settings.recommendation_concurrency_limit == 2
    assert settings.feedback_rate_limit == 30
    assert settings.feedback_rate_window_seconds == 60
    assert settings.narration_budget_limit == 30
    assert settings.narration_budget_window_seconds == 3600


@pytest.mark.parametrize("field_name", PublicAlphaSafeguardSettings.__dataclass_fields__)
@pytest.mark.parametrize("invalid", [True, 0, -1])
def test_settings_reject_bool_and_non_positive_values(field_name: str, invalid: object) -> None:
    with pytest.raises((TypeError, ValueError), match=field_name):
        PublicAlphaSafeguardSettings(**{field_name: invalid})  # type: ignore[arg-type]


def test_settings_and_rejection_results_are_immutable() -> None:
    settings = PublicAlphaSafeguardSettings()
    rejection = SafeguardRejection("safe_code", 1)

    with pytest.raises(FrozenInstanceError):
        settings.feedback_rate_limit = 1  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        rejection.retry_after_seconds = 2  # type: ignore[misc]


def test_safeguards_reject_invalid_constructor_arguments() -> None:
    with pytest.raises(TypeError, match="settings"):
        ApiSafeguards(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="clock"):
        ApiSafeguards(_settings(), clock=None)  # type: ignore[arg-type]


def test_recommendation_rate_is_rolling_and_reports_ceil_retry_after() -> None:
    clock = FakeClock()
    safeguards = ApiSafeguards(_settings(), clock=clock)

    _accept_and_release(safeguards)
    clock.advance(0.25)
    _accept_and_release(safeguards)
    clock.advance(0.25)

    assert safeguards.admit_recommendation() == SafeguardRejection(
        "recommendation_rate_limited", 10
    )

    clock.advance(9.5)
    _accept_and_release(safeguards)


def test_short_window_rejection_does_not_consume_long_budget() -> None:
    clock = FakeClock()
    safeguards = ApiSafeguards(
        _settings(
            recommendation_rate_limit=1,
            recommendation_rate_window_seconds=1,
            recommendation_budget_limit=2,
            recommendation_budget_window_seconds=10,
        ),
        clock=clock,
    )

    _accept_and_release(safeguards)
    assert safeguards.admit_recommendation() == SafeguardRejection("recommendation_rate_limited", 1)
    clock.advance(1)
    _accept_and_release(safeguards)
    clock.advance(1)

    assert safeguards.admit_recommendation() == SafeguardRejection(
        "recommendation_budget_exhausted", 8
    )
    clock.advance(8)
    _accept_and_release(safeguards)


def test_concurrency_rejections_consume_no_quota_and_leases_release() -> None:
    clock = FakeClock()
    safeguards = ApiSafeguards(
        _settings(recommendation_rate_limit=1, recommendation_concurrency_limit=1),
        clock=clock,
    )
    first = safeguards.admit_recommendation()
    assert isinstance(first, RecommendationLease)

    assert safeguards.admit_recommendation() == SafeguardRejection(
        "recommendation_capacity_reached", 1
    )
    with first:
        pass
    assert safeguards.admit_recommendation() == SafeguardRejection(
        "recommendation_rate_limited", 10
    )


def test_concurrency_lease_releases_after_an_exception() -> None:
    safeguards = ApiSafeguards(_settings(recommendation_concurrency_limit=1))
    first = safeguards.admit_recommendation()
    assert isinstance(first, RecommendationLease)

    with pytest.raises(RuntimeError, match="defect"):
        with first:
            raise RuntimeError("defect")

    second = safeguards.admit_recommendation()
    assert isinstance(second, RecommendationLease)
    with second:
        pass


def test_feedback_rate_is_independent_rolling_and_bounded() -> None:
    clock = FakeClock()
    safeguards = ApiSafeguards(_settings(), clock=clock)

    assert safeguards.admit_feedback() is None
    clock.advance(0.1)
    assert safeguards.admit_feedback() is None
    clock.advance(0.1)
    assert safeguards.admit_feedback() == SafeguardRejection("feedback_rate_limited", 10)
    assert safeguards.admit_narration() is True
    clock.advance(9.8)
    assert safeguards.admit_feedback() is None


def test_narration_budget_expires_without_affecting_recommendations() -> None:
    clock = FakeClock()
    safeguards = ApiSafeguards(_settings(), clock=clock)

    assert safeguards.admit_narration() is True
    assert safeguards.admit_narration() is True
    assert safeguards.admit_narration() is False
    _accept_and_release(safeguards)
    clock.advance(10)
    assert safeguards.admit_narration() is True


def test_each_application_owns_fresh_safeguard_state() -> None:
    first = create_app()
    second = create_app()

    assert first.state.api_safeguards is not second.state.api_safeguards
    assert isinstance(first.state.api_safeguards.admit_recommendation(), RecommendationLease)
    assert isinstance(second.state.api_safeguards.admit_recommendation(), RecommendationLease)


def test_concurrent_admission_is_atomic() -> None:
    safeguards = ApiSafeguards(_settings(recommendation_concurrency_limit=1))
    start = Barrier(3)
    decisions_ready = Barrier(3)
    results: list[RecommendationLease | SafeguardRejection] = []

    def attempt() -> None:
        start.wait()
        decision = safeguards.admit_recommendation()
        results.append(decision)
        decisions_ready.wait()
        if isinstance(decision, RecommendationLease):
            with decision:
                pass

    threads = [Thread(target=attempt), Thread(target=attempt)]
    for thread in threads:
        thread.start()
    start.wait()
    decisions_ready.wait()
    for thread in threads:
        thread.join()

    assert sum(isinstance(result, RecommendationLease) for result in results) == 1
    assert results.count(SafeguardRejection("recommendation_capacity_reached", 1)) == 1
