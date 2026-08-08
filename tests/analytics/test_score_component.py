"""Tests for explainable suitability-score components."""

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from solara_travel.analytics.scoring import ScoreComponent


def test_score_component_accepts_valid_values() -> None:
    """A score component should preserve its name, score, and weight."""

    component = ScoreComponent(
        name="interest_match",
        score=0.85,
        weight=0.40,
    )

    assert component.name == "interest_match"
    assert component.score == 0.85
    assert component.weight == 0.40


@pytest.mark.parametrize(
    "score",
    [
        0.0,
        0.25,
        0.5,
        0.75,
        1.0,
    ],
)
def test_score_component_accepts_score_boundaries(score: float) -> None:
    """Component scores may span the inclusive normalized range."""

    component = ScoreComponent(
        name="interest_match",
        score=score,
        weight=0.40,
    )

    assert component.score == score


@pytest.mark.parametrize(
    "weight",
    [
        0.0,
        0.25,
        0.5,
        0.75,
        1.0,
    ],
)
def test_score_component_accepts_weight_boundaries(weight: float) -> None:
    """Component weights may span the inclusive normalized range."""

    component = ScoreComponent(
        name="interest_match",
        score=0.85,
        weight=weight,
    )

    assert component.weight == weight


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_score_component_rejects_blank_name(name: str) -> None:
    """A component requires a meaningful explanatory name."""

    with pytest.raises(
        ValueError,
        match="score component name must not be blank",
    ):
        ScoreComponent(
            name=name,
            score=0.85,
            weight=0.40,
        )


@pytest.mark.parametrize(
    "name",
    [
        None,
        42,
        ["interest_match"],
        {"name": "interest_match"},
    ],
)
def test_score_component_rejects_non_string_name(name: object) -> None:
    """Component names must be represented as strings."""

    with pytest.raises(
        TypeError,
        match="score component name must be a string",
    ):
        ScoreComponent(
            name=name,  # type: ignore[arg-type]
            score=0.85,
            weight=0.40,
        )


@pytest.mark.parametrize(
    "score",
    [
        -0.0001,
        -1.0,
        1.0001,
        2.0,
    ],
)
def test_score_component_rejects_score_outside_normalized_range(
    score: float,
) -> None:
    """Component scores must remain between zero and one inclusive."""

    with pytest.raises(
        ValueError,
        match="score must be between 0 and 1",
    ):
        ScoreComponent(
            name="interest_match",
            score=score,
            weight=0.40,
        )


@pytest.mark.parametrize(
    "weight",
    [
        -0.0001,
        -1.0,
        1.0001,
        2.0,
    ],
)
def test_score_component_rejects_weight_outside_normalized_range(
    weight: float,
) -> None:
    """Component weights must remain between zero and one inclusive."""

    with pytest.raises(
        ValueError,
        match="weight must be between 0 and 1",
    ):
        ScoreComponent(
            name="interest_match",
            score=0.85,
            weight=weight,
        )


@pytest.mark.parametrize(
    "score",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_score_component_rejects_non_finite_score(score: float) -> None:
    """NaN and infinite values are not meaningful suitability scores."""

    with pytest.raises(
        ValueError,
        match="score must be a finite number",
    ):
        ScoreComponent(
            name="interest_match",
            score=score,
            weight=0.40,
        )


@pytest.mark.parametrize(
    "weight",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_score_component_rejects_non_finite_weight(weight: float) -> None:
    """NaN and infinite values are not meaningful component weights."""

    with pytest.raises(
        ValueError,
        match="weight must be a finite number",
    ):
        ScoreComponent(
            name="interest_match",
            score=0.85,
            weight=weight,
        )


@pytest.mark.parametrize(
    "score",
    [
        None,
        "0.85",
        [0.85],
        True,
    ],
)
def test_score_component_rejects_non_numeric_score(score: object) -> None:
    """A component score must be a real numeric value."""

    with pytest.raises(
        TypeError,
        match="score must be a real number",
    ):
        ScoreComponent(
            name="interest_match",
            score=score,  # type: ignore[arg-type]
            weight=0.40,
        )


@pytest.mark.parametrize(
    "weight",
    [
        None,
        "0.40",
        [0.40],
        True,
    ],
)
def test_score_component_rejects_non_numeric_weight(weight: object) -> None:
    """A component weight must be a real numeric value."""

    with pytest.raises(
        TypeError,
        match="weight must be a real number",
    ):
        ScoreComponent(
            name="interest_match",
            score=0.85,
            weight=weight,  # type: ignore[arg-type]
        )


def test_score_component_reports_weighted_contribution() -> None:
    """A component should expose its contribution to weighted scoring."""

    component = ScoreComponent(
        name="interest_match",
        score=0.80,
        weight=0.25,
    )

    assert component.weighted_contribution == pytest.approx(0.20)


def test_zero_weight_produces_zero_weighted_contribution() -> None:
    """A disabled component should contribute nothing to the total score."""

    component = ScoreComponent(
        name="interest_match",
        score=1.0,
        weight=0.0,
    )

    assert component.weighted_contribution == 0.0


def test_score_component_preserves_supplied_name() -> None:
    """Validation should not silently normalize explanatory component names."""

    component = ScoreComponent(
        name=" Interest Match ",
        score=0.85,
        weight=0.40,
    )

    assert component.name == " Interest Match "


def test_score_component_uses_value_equality() -> None:
    """Equivalent score components should compare equally."""

    first = ScoreComponent(
        name="interest_match",
        score=0.85,
        weight=0.40,
    )
    second = ScoreComponent(
        name="interest_match",
        score=0.85,
        weight=0.40,
    )

    assert first == second


def test_score_component_is_hashable() -> None:
    """Score components should be usable in immutable collections."""

    component = ScoreComponent(
        name="interest_match",
        score=0.85,
        weight=0.40,
    )

    assert {component, component} == {component}


def test_score_component_is_immutable() -> None:
    """Scoring evidence must not change after construction."""

    component = ScoreComponent(
        name="interest_match",
        score=0.85,
        weight=0.40,
    )

    with pytest.raises(FrozenInstanceError):
        component.score = 0.95