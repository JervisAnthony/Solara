"""Tests for provider-independent destination query values."""

from dataclasses import FrozenInstanceError

import pytest

from solara_travel.domain import DestinationQuery
from solara_travel.domain.destination import DESTINATION_QUERY_MAX_LENGTH


def test_destination_query_normalizes_outer_whitespace_and_preserves_unicode() -> None:
    query = DestinationQuery("  São Tomé, São Tomé and Príncipe  ")

    assert query.value == "São Tomé, São Tomé and Príncipe"


@pytest.mark.parametrize("value", [None, 42, object()])
def test_destination_query_rejects_non_strings(value: object) -> None:
    with pytest.raises(TypeError, match="must be a string"):
        DestinationQuery(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["", "   ", "Budapest\nHungary", "Paris\u200b"])
def test_destination_query_rejects_blank_or_non_printable_values(value: str) -> None:
    with pytest.raises(ValueError):
        DestinationQuery(value)


def test_destination_query_enforces_bounded_length() -> None:
    assert DestinationQuery("x" * DESTINATION_QUERY_MAX_LENGTH).value
    with pytest.raises(ValueError, match="must not exceed"):
        DestinationQuery("x" * (DESTINATION_QUERY_MAX_LENGTH + 1))


def test_destination_query_is_immutable() -> None:
    query = DestinationQuery("Budapest, Hungary")

    with pytest.raises(FrozenInstanceError):
        query.value = "Vienna"  # type: ignore[misc]
