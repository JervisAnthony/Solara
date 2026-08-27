"""Tests for explicit hard and soft planning constraints."""

import pytest

from solara_travel.domain import ClimateCondition, ClimateConstraint, ConstraintSeverity


def test_climate_constraint_accepts_typed_hard_and_soft_values() -> None:
    assert (
        ClimateConstraint(ClimateCondition.COLD_OR_SNOWY, ConstraintSeverity.HARD).severity
        is ConstraintSeverity.HARD
    )
    assert (
        ClimateConstraint(ClimateCondition.COLD_OR_SNOWY, ConstraintSeverity.SOFT).severity
        is ConstraintSeverity.SOFT
    )


@pytest.mark.parametrize(
    ("condition", "severity", "message"),
    [
        ("cold_or_snowy", ConstraintSeverity.HARD, "condition must be ClimateCondition"),
        (ClimateCondition.COLD_OR_SNOWY, "hard", "severity must be ConstraintSeverity"),
    ],
)
def test_climate_constraint_rejects_untyped_values(
    condition: object, severity: object, message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        ClimateConstraint(condition, severity)  # type: ignore[arg-type]
