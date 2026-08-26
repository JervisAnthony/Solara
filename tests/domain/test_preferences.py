"""Tests for traveller-preference domain value objects."""

from dataclasses import FrozenInstanceError

import pytest

from solara_travel.domain.preferences import (
    TravellerInterests,
    TravellerPreferences,
)


def test_traveller_interests_accepts_single_interest() -> None:
    """A traveller may state one interest."""

    traveller_interests = TravellerInterests(interests=("history",))

    assert traveller_interests.interests == ("history",)


def test_traveller_interests_accepts_multiple_interests() -> None:
    """A traveller may state several distinct interests."""

    interests = ("history", "food", "architecture")

    assert TravellerInterests(interests=interests).interests == interests


def test_traveller_interests_preserves_supplied_values() -> None:
    """Validation should not normalize the stored interest strings."""

    interests = (" History ", "local Food")

    assert TravellerInterests(interests=interests).interests == interests


def test_traveller_interests_rejects_empty_tuple() -> None:
    """At least one interest is required."""

    with pytest.raises(ValueError, match="at least one interest must be provided"):
        TravellerInterests(interests=())


@pytest.mark.parametrize("interests", [["history"], {"history"}, "history"])
def test_traveller_interests_rejects_non_tuple_collection(interests: object) -> None:
    """Interest collections must use the immutable tuple type."""

    with pytest.raises(TypeError, match="interests must be a tuple"):
        TravellerInterests(interests=interests)  # type: ignore[arg-type]


@pytest.mark.parametrize("interest", [None, 42, ["history"]])
def test_traveller_interests_rejects_non_string_values(interest: object) -> None:
    """Every individual interest must be a string."""

    with pytest.raises(TypeError, match="every interest must be a string"):
        TravellerInterests(interests=(interest,))  # type: ignore[arg-type]


@pytest.mark.parametrize("interest", ["", " ", "\t", "\n"])
def test_traveller_interests_rejects_blank_values(interest: str) -> None:
    """Empty and whitespace-only interests are invalid."""

    with pytest.raises(ValueError, match="interests must not be blank"):
        TravellerInterests(interests=(interest,))


@pytest.mark.parametrize(
    "interests",
    [
        ("history", "history"),
        ("history", "History"),
        (" food ", "FOOD"),
    ],
)
def test_traveller_interests_rejects_duplicates(interests: tuple[str, ...]) -> None:
    """Duplicates are compared case-insensitively after trimming whitespace."""

    with pytest.raises(ValueError, match="interests must not contain duplicates"):
        TravellerInterests(interests=interests)


def test_traveller_interests_uses_value_equality() -> None:
    """Instances with identical supplied values should compare equally."""

    first = TravellerInterests(interests=("history", "food"))
    second = TravellerInterests(interests=("history", "food"))

    assert first == second


def test_traveller_interests_is_hashable() -> None:
    """Traveller interests should be usable in immutable collections."""

    traveller_interests = TravellerInterests(interests=("history", "food"))

    assert {traveller_interests, traveller_interests} == {traveller_interests}


def test_traveller_interests_is_immutable() -> None:
    """Interest values must not change after construction."""

    traveller_interests = TravellerInterests(interests=("history",))

    with pytest.raises(FrozenInstanceError):
        traveller_interests.interests = ("nature",)


def test_traveller_preferences_accepts_interests_only() -> None:
    """Traveller preferences may initially contain only stated interests."""

    interests = TravellerInterests(
        interests=("history", "food"),
    )

    preferences = TravellerPreferences(
        interests=interests,
    )

    assert preferences.interests == interests
    assert preferences.preferred_pace is None
    assert preferences.preferred_climate is None


def test_traveller_preferences_accepts_optional_pace_and_climate() -> None:
    """A traveller may express simple pace and climate preferences."""

    preferences = TravellerPreferences(
        interests=TravellerInterests(
            interests=("history", "architecture"),
        ),
        preferred_pace="moderate",
        preferred_climate="mild",
    )

    assert preferences.preferred_pace == "moderate"
    assert preferences.preferred_climate == "mild"


def test_traveller_preferences_allows_no_stated_interests() -> None:
    """A recommendation request may exist without explicit interests."""

    preferences = TravellerPreferences()

    assert preferences.interests is None
    assert preferences.preferred_pace is None
    assert preferences.preferred_climate is None


def test_traveller_preferences_rejects_invalid_interests_type() -> None:
    """Interests must use the TravellerInterests domain value when supplied."""

    with pytest.raises(
        TypeError,
        match="interests must be TravellerInterests or None",
    ):
        TravellerPreferences(
            interests=("history", "food"),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "preferred_pace",
    [
        "",
        " ",
        "\t",
        "\n",
    ],
)
def test_traveller_preferences_rejects_blank_preferred_pace(
    preferred_pace: str,
) -> None:
    """A supplied pace preference must contain meaningful text."""

    with pytest.raises(
        ValueError,
        match="preferred pace must not be blank",
    ):
        TravellerPreferences(
            preferred_pace=preferred_pace,
        )


@pytest.mark.parametrize(
    "preferred_climate",
    [
        "",
        " ",
        "\t",
        "\n",
    ],
)
def test_traveller_preferences_rejects_blank_preferred_climate(
    preferred_climate: str,
) -> None:
    """A supplied climate preference must contain meaningful text."""

    with pytest.raises(
        ValueError,
        match="preferred climate must not be blank",
    ):
        TravellerPreferences(
            preferred_climate=preferred_climate,
        )


@pytest.mark.parametrize(
    "preferred_pace",
    [
        42,
        ["moderate"],
        {"pace": "moderate"},
    ],
)
def test_traveller_preferences_rejects_non_string_preferred_pace(
    preferred_pace: object,
) -> None:
    """A supplied pace preference must be represented as text."""

    with pytest.raises(
        TypeError,
        match="preferred pace must be a string or None",
    ):
        TravellerPreferences(
            preferred_pace=preferred_pace,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "preferred_climate",
    [
        42,
        ["mild"],
        {"climate": "mild"},
    ],
)
def test_traveller_preferences_rejects_non_string_preferred_climate(
    preferred_climate: object,
) -> None:
    """A supplied climate preference must be represented as text."""

    with pytest.raises(
        TypeError,
        match="preferred climate must be a string or None",
    ):
        TravellerPreferences(
            preferred_climate=preferred_climate,  # type: ignore[arg-type]
        )


def test_traveller_preferences_preserves_supplied_text() -> None:
    """Preference validation should not silently normalize supplied text."""

    preferences = TravellerPreferences(
        preferred_pace=" Moderate ",
        preferred_climate=" Mild ",
    )

    assert preferences.preferred_pace == " Moderate "
    assert preferences.preferred_climate == " Mild "


def test_traveller_preferences_uses_value_equality() -> None:
    """Equivalent traveller preferences should compare equally."""

    first = TravellerPreferences(
        interests=TravellerInterests(
            interests=("history", "food"),
        ),
        preferred_pace="moderate",
        preferred_climate="mild",
    )
    second = TravellerPreferences(
        interests=TravellerInterests(
            interests=("history", "food"),
        ),
        preferred_pace="moderate",
        preferred_climate="mild",
    )

    assert first == second


def test_traveller_preferences_is_hashable() -> None:
    """Traveller preferences should remain usable as immutable values."""

    preferences = TravellerPreferences(
        interests=TravellerInterests(
            interests=("history",),
        ),
        preferred_pace="slow",
    )

    assert {preferences, preferences} == {preferences}


def test_traveller_preferences_is_immutable() -> None:
    """Traveller preferences must not change after construction."""

    preferences = TravellerPreferences(
        preferred_pace="moderate",
    )

    with pytest.raises(FrozenInstanceError):
        preferences.preferred_pace = "fast"