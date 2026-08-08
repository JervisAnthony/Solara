"""Deterministic and explainable suitability-scoring primitives."""

from dataclasses import dataclass
from math import isfinite
from numbers import Real


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    """An immutable named contribution to a suitability score.

    Both the component score and its weight use the inclusive normalized range
    from 0 to 1. The original component name is preserved so scoring evidence
    remains faithful to the value supplied by the caller.
    """

    name: str
    score: float
    weight: float

    def __post_init__(self) -> None:
        """Validate the component name, score, and weight."""

        if not isinstance(self.name, str):
            raise TypeError("score component name must be a string")

        if not self.name.strip():
            raise ValueError("score component name must not be blank")

        if not isinstance(self.score, Real) or isinstance(self.score, bool):
            raise TypeError("score must be a real number")

        if not isfinite(self.score):
            raise ValueError("score must be a finite number")

        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")

        if not isinstance(self.weight, Real) or isinstance(self.weight, bool):
            raise TypeError("weight must be a real number")

        if not isfinite(self.weight):
            raise ValueError("weight must be a finite number")

        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("weight must be between 0 and 1")

    @property
    def weighted_contribution(self) -> float:
        """Return this component's contribution to a weighted score."""

        return float(self.score * self.weight)


@dataclass(frozen=True, slots=True)
class SuitabilityScore:
    """An immutable explainable aggregate of weighted score components.

    The final score is calculated as a normalized weighted average so component
    weights represent relative importance and do not need to sum to exactly one.

    Components remain available in their original order for explanation and
    auditing.
    """

    components: tuple[ScoreComponent, ...]

    def __post_init__(self) -> None:
        """Validate the component collection and aggregate constraints."""

        if not isinstance(self.components, tuple):
            raise TypeError("components must be a tuple")

        if not self.components:
            raise ValueError("at least one score component must be provided")

        if not all(
            isinstance(component, ScoreComponent)
            for component in self.components
        ):
            raise TypeError("every component must be a ScoreComponent")

        comparable_names = [
            component.name.strip().casefold()
            for component in self.components
        ]
        if len(comparable_names) != len(set(comparable_names)):
            raise ValueError("score component names must be unique")

        if self.total_weight <= 0.0:
            raise ValueError("total component weight must be greater than zero")

    @property
    def total_weight(self) -> float:
        """Return the combined weight represented by all components."""

        return float(sum(component.weight for component in self.components))

    @property
    def weighted_total(self) -> float:
        """Return the raw total of all weighted component contributions."""

        return float(
            sum(
                component.weighted_contribution
                for component in self.components
            )
        )

    @property
    def score(self) -> float:
        """Return the normalized weighted suitability score."""

        return self.weighted_total / self.total_weight