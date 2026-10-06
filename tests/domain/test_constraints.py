"""Tests for explicit hard and soft planning constraints."""

import pytest

from solara_travel.domain import ClimateCondition, ClimateConstraint, ConstraintSeverity


def test_climate_constraint_accepts_typed_hard_and_soft_values() -> None:
    assert tuple(ClimateCondition) == (ClimateCondition.COLD,)
    assert ClimateCondition.COLD.value == "cold"
    assert (
        ClimateConstraint(ClimateCondition.COLD, ConstraintSeverity.HARD).severity
        is ConstraintSeverity.HARD
    )
    assert (
        ClimateConstraint(ClimateCondition.COLD, ConstraintSeverity.SOFT).severity
        is ConstraintSeverity.SOFT
    )


@pytest.mark.parametrize(
    ("condition", "severity", "message"),
    [
        ("cold", ConstraintSeverity.HARD, "condition must be ClimateCondition"),
        (ClimateCondition.COLD, "hard", "severity must be ConstraintSeverity"),
    ],
)
def test_climate_constraint_rejects_untyped_values(
    condition: object, severity: object, message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        ClimateConstraint(condition, severity)  # type: ignore[arg-type]


@pytest.mark.parametrize("unsupported", ["cold_or_snowy", "snow", "snowy"])
def test_temperature_only_contract_rejects_legacy_and_snow_conditions(unsupported):
    with pytest.raises(ValueError):
        ClimateCondition(unsupported)
