"""Structured candidate proposals derived from untrusted traveller intent."""

from dataclasses import dataclass

MAX_PROPOSED_LOCALITIES = 8


@dataclass(frozen=True, slots=True)
class DestinationCandidateProposal:
    """Strict provider-independent output from candidate-proposal AI."""

    themes: tuple[str, ...]
    desired_experiences: tuple[str, ...]
    avoidances: tuple[str, ...]
    candidate_localities: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "themes",
            "desired_experiences",
            "avoidances",
            "candidate_localities",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            if not all(isinstance(value, str) and value.strip() for value in values):
                raise ValueError(f"{field_name} must contain non-blank strings")
            normalized = tuple(value.strip() for value in values)
            if len({value.casefold() for value in normalized}) != len(normalized):
                raise ValueError(f"{field_name} must not contain duplicates")
            object.__setattr__(self, field_name, normalized)
        if not self.candidate_localities:
            raise ValueError("candidate_localities must not be empty")
        if len(self.candidate_localities) > MAX_PROPOSED_LOCALITIES:
            raise ValueError(
                f"candidate_localities must contain at most {MAX_PROPOSED_LOCALITIES} values"
            )
