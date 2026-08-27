"""Typed planning constraints that distinguish eligibility from preference."""

from dataclasses import dataclass
from enum import StrEnum


class ConstraintSeverity(StrEnum):
    """How a planning constraint affects candidate selection."""

    HARD = "hard"
    SOFT = "soft"


class ClimateCondition(StrEnum):
    """Climate conditions Solara can evaluate from seasonal temperature evidence."""

    COLD_OR_SNOWY = "cold_or_snowy"


@dataclass(frozen=True, slots=True)
class ClimateConstraint:
    """An explicit climate condition and whether it is mandatory."""

    condition: ClimateCondition
    severity: ConstraintSeverity

    def __post_init__(self) -> None:
        if not isinstance(self.condition, ClimateCondition):
            raise TypeError("condition must be ClimateCondition")
        if not isinstance(self.severity, ConstraintSeverity):
            raise TypeError("severity must be ConstraintSeverity")
