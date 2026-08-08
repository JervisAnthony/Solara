"""Traveller-preference value objects used by the Solara domain."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TravellerInterests:
    """An immutable collection of a traveller's stated interests."""

    interests: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate the interest collection and its values."""

        if not isinstance(self.interests, tuple):
            raise TypeError("interests must be a tuple")

        if not self.interests:
            raise ValueError("at least one interest must be provided")

        if not all(isinstance(interest, str) for interest in self.interests):
            raise TypeError("every interest must be a string")

        if any(not interest.strip() for interest in self.interests):
            raise ValueError("interests must not be blank")

        comparable_interests = [
            interest.strip().casefold() for interest in self.interests
        ]
        if len(comparable_interests) != len(set(comparable_interests)):
            raise ValueError("interests must not contain duplicates")


@dataclass(frozen=True, slots=True)
class TravellerPreferences:
    """Immutable preferences supplied by a traveller.

    Interests are optional at this level so that Solara can represent a
    traveller who has not stated any explicit interests.

    Pace and climate preferences remain free-form domain values for now rather
    than being constrained by premature enums. Their allowed vocabularies can
    evolve when recommendation behaviour establishes concrete requirements.
    """

    interests: TravellerInterests | None = None
    preferred_pace: str | None = None
    preferred_climate: str | None = None

    def __post_init__(self) -> None:
        """Validate optional traveller preference values."""

        if self.interests is not None and not isinstance(
            self.interests,
            TravellerInterests,
        ):
            raise TypeError("interests must be TravellerInterests or None")

        if self.preferred_pace is not None:
            if not isinstance(self.preferred_pace, str):
                raise TypeError("preferred pace must be a string or None")

            if not self.preferred_pace.strip():
                raise ValueError("preferred pace must not be blank")

        if self.preferred_climate is not None:
            if not isinstance(self.preferred_climate, str):
                raise TypeError("preferred climate must be a string or None")

            if not self.preferred_climate.strip():
                raise ValueError("preferred climate must not be blank")