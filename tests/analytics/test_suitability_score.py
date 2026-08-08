"""Tests for deterministic weighted suitability scores."""

from dataclasses import FrozenInstanceError
from math import isclose

import pytest

from solara_travel.analytics.scoring import ScoreComponent, SuitabilityScore


def test_suitability_score_accepts_single_component() -> None:
    """A single weighted component should produce its own normalized score."""

    component = ScoreComponent(
        name="interest_match",
        score=0.85,
        weight=0.40,
    )

    suitability = SuitabilityScore(
        components=(component,),
    )

    assert suitability.components == (component,)
    assert suitability.score == pytest.approx(0.85)


def test_suitability_score_calculates_normalized_weighted_average() -> None:
    """Overall suitability should be the normalized weighted component total."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.90,
                weight=0.50,
            ),
            ScoreComponent(
                name="popularity",
                score=0.70,
                weight=0.30,
            ),
            ScoreComponent(
                name="seasonal_suitability",
                score=0.80,
                weight=0.20,
            ),
        ),
    )

    assert suitability.score == pytest.approx(0.82)


def test_suitability_score_normalizes_weights_that_do_not_sum_to_one() -> None:
    """Weights may express relative importance without summing to exactly one."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=1.0,
                weight=0.60,
            ),
            ScoreComponent(
                name="popularity",
                score=0.50,
                weight=0.20,
            ),
        ),
    )

    expected = ((1.0 * 0.60) + (0.50 * 0.20)) / 0.80

    assert suitability.score == pytest.approx(expected)


def test_suitability_score_reports_total_weight() -> None:
    """The aggregate should expose the weight represented by its components."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.90,
                weight=0.50,
            ),
            ScoreComponent(
                name="popularity",
                score=0.70,
                weight=0.30,
            ),
        ),
    )

    assert suitability.total_weight == pytest.approx(0.80)


def test_suitability_score_reports_weighted_total() -> None:
    """The raw weighted contribution should remain available for explanation."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.90,
                weight=0.50,
            ),
            ScoreComponent(
                name="popularity",
                score=0.70,
                weight=0.30,
            ),
        ),
    )

    assert suitability.weighted_total == pytest.approx(0.66)


def test_zero_weight_component_does_not_affect_score() -> None:
    """Disabled components should remain visible without changing suitability."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.80,
                weight=1.0,
            ),
            ScoreComponent(
                name="popularity",
                score=0.0,
                weight=0.0,
            ),
        ),
    )

    assert suitability.score == pytest.approx(0.80)


def test_zero_weight_component_remains_in_explanation_components() -> None:
    """Zero-weight components should not silently disappear from evidence."""

    disabled = ScoreComponent(
        name="popularity",
        score=0.40,
        weight=0.0,
    )
    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.80,
                weight=1.0,
            ),
            disabled,
        ),
    )

    assert disabled in suitability.components


def test_suitability_score_can_reach_zero() -> None:
    """Completely unsuitable weighted evidence may produce zero."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.0,
                weight=1.0,
            ),
        ),
    )

    assert suitability.score == 0.0


def test_suitability_score_can_reach_one() -> None:
    """Completely suitable weighted evidence may produce one."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=1.0,
                weight=1.0,
            ),
        ),
    )

    assert suitability.score == 1.0


def test_suitability_score_remains_within_normalized_range() -> None:
    """Normalized composition must remain bounded between zero and one."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="first",
                score=0.123456,
                weight=0.73,
            ),
            ScoreComponent(
                name="second",
                score=0.987654,
                weight=0.19,
            ),
            ScoreComponent(
                name="third",
                score=0.50,
                weight=0.08,
            ),
        ),
    )

    assert 0.0 <= suitability.score <= 1.0


def test_suitability_score_rejects_empty_components() -> None:
    """A suitability score requires at least one explanatory component."""

    with pytest.raises(
        ValueError,
        match="at least one score component must be provided",
    ):
        SuitabilityScore(components=())


@pytest.mark.parametrize(
    "components",
    [
        [],
        {"interest_match"},
        "interest_match",
        None,
    ],
)
def test_suitability_score_rejects_non_tuple_components(
    components: object,
) -> None:
    """Score components must be supplied using an immutable tuple."""

    with pytest.raises(
        TypeError,
        match="components must be a tuple",
    ):
        SuitabilityScore(
            components=components,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "component",
    [
        None,
        "interest_match",
        0.85,
        {"name": "interest_match", "score": 0.85},
    ],
)
def test_suitability_score_rejects_non_score_components(
    component: object,
) -> None:
    """Every aggregate component must use the ScoreComponent value object."""

    with pytest.raises(
        TypeError,
        match="every component must be a ScoreComponent",
    ):
        SuitabilityScore(
            components=(component,),  # type: ignore[arg-type]
        )


def test_suitability_score_rejects_all_zero_weights() -> None:
    """At least one component must participate in the weighted calculation."""

    with pytest.raises(
        ValueError,
        match="total component weight must be greater than zero",
    ):
        SuitabilityScore(
            components=(
                ScoreComponent(
                    name="interest_match",
                    score=0.80,
                    weight=0.0,
                ),
                ScoreComponent(
                    name="popularity",
                    score=0.60,
                    weight=0.0,
                ),
            ),
        )


def test_suitability_score_rejects_exact_duplicate_component_names() -> None:
    """Two components must not claim the same explanatory responsibility."""

    with pytest.raises(
        ValueError,
        match="score component names must be unique",
    ):
        SuitabilityScore(
            components=(
                ScoreComponent(
                    name="interest_match",
                    score=0.80,
                    weight=0.50,
                ),
                ScoreComponent(
                    name="interest_match",
                    score=0.90,
                    weight=0.50,
                ),
            ),
        )


def test_suitability_score_rejects_case_insensitive_duplicate_names() -> None:
    """Component names should be unique regardless of letter casing."""

    with pytest.raises(
        ValueError,
        match="score component names must be unique",
    ):
        SuitabilityScore(
            components=(
                ScoreComponent(
                    name="interest_match",
                    score=0.80,
                    weight=0.50,
                ),
                ScoreComponent(
                    name="Interest_Match",
                    score=0.90,
                    weight=0.50,
                ),
            ),
        )


def test_suitability_score_rejects_whitespace_equivalent_duplicate_names() -> None:
    """Surrounding whitespace must not allow duplicate component names."""

    with pytest.raises(
        ValueError,
        match="score component names must be unique",
    ):
        SuitabilityScore(
            components=(
                ScoreComponent(
                    name="interest_match",
                    score=0.80,
                    weight=0.50,
                ),
                ScoreComponent(
                    name=" interest_match ",
                    score=0.90,
                    weight=0.50,
                ),
            ),
        )


def test_suitability_score_preserves_component_order() -> None:
    """Explanation components should retain their caller-defined order."""

    first = ScoreComponent(
        name="interest_match",
        score=0.90,
        weight=0.50,
    )
    second = ScoreComponent(
        name="popularity",
        score=0.70,
        weight=0.30,
    )
    third = ScoreComponent(
        name="seasonal_suitability",
        score=0.80,
        weight=0.20,
    )

    suitability = SuitabilityScore(
        components=(first, second, third),
    )

    assert suitability.components == (first, second, third)


def test_suitability_score_uses_value_equality() -> None:
    """Equivalent component collections should produce equal score values."""

    first = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.90,
                weight=0.60,
            ),
            ScoreComponent(
                name="popularity",
                score=0.70,
                weight=0.40,
            ),
        ),
    )
    second = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.90,
                weight=0.60,
            ),
            ScoreComponent(
                name="popularity",
                score=0.70,
                weight=0.40,
            ),
        ),
    )

    assert first == second
    assert isclose(first.score, second.score)


def test_suitability_score_is_hashable() -> None:
    """Suitability scores should be usable in immutable collections."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.90,
                weight=1.0,
            ),
        ),
    )

    assert {suitability, suitability} == {suitability}


def test_suitability_score_is_immutable() -> None:
    """Suitability evidence must not change after construction."""

    suitability = SuitabilityScore(
        components=(
            ScoreComponent(
                name="interest_match",
                score=0.90,
                weight=1.0,
            ),
        ),
    )

    with pytest.raises(FrozenInstanceError):
        suitability.components = ()