"""Tests for travel-period domain values."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from solara_travel.domain.travel import TravelPeriod


def test_travel_period_accepts_valid_date_range() -> None:
    """A period should accept a start date that precedes its end date."""

    period = TravelPeriod(
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 16),
    )

    assert period.start_date == date(2026, 11, 10)
    assert period.end_date == date(2026, 11, 16)


def test_travel_period_accepts_single_day_trip() -> None:
    """A travel period may begin and end on the same calendar date."""

    trip_date = date(2026, 11, 10)

    period = TravelPeriod(
        start_date=trip_date,
        end_date=trip_date,
    )

    assert period.start_date == trip_date
    assert period.end_date == trip_date


def test_travel_period_rejects_end_date_before_start_date() -> None:
    """A travel period cannot end before it begins."""

    with pytest.raises(
        ValueError,
        match="end date must not be before start date",
    ):
        TravelPeriod(
            start_date=date(2026, 11, 16),
            end_date=date(2026, 11, 10),
        )


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        ("2026-11-10", date(2026, 11, 16)),
        (date(2026, 11, 10), "2026-11-16"),
        (None, date(2026, 11, 16)),
        (date(2026, 11, 10), None),
        (datetime(2026, 11, 10, 10, 30), date(2026, 11, 16)),
        (date(2026, 11, 10), datetime(2026, 11, 16, 10, 30)),
    ],
)
def test_travel_period_rejects_non_date_values(
    start_date: object,
    end_date: object,
) -> None:
    """Travel periods require calendar dates rather than strings or datetimes."""

    with pytest.raises(
        TypeError,
        match="start date and end date must be date values",
    ):
        TravelPeriod(
            start_date=start_date,  # type: ignore[arg-type]
            end_date=end_date,  # type: ignore[arg-type]
        )


def test_travel_period_reports_inclusive_duration_days() -> None:
    """Trip duration should count both the arrival and departure dates."""

    period = TravelPeriod(
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 16),
    )

    assert period.duration_days == 7


def test_single_day_travel_period_has_one_day_duration() -> None:
    """A same-day travel period represents one calendar day."""

    trip_date = date(2026, 11, 10)

    period = TravelPeriod(
        start_date=trip_date,
        end_date=trip_date,
    )

    assert period.duration_days == 1


def test_travel_period_uses_value_equality() -> None:
    """Periods with the same dates should compare equally."""

    first = TravelPeriod(
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 16),
    )
    second = TravelPeriod(
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 16),
    )

    assert first == second


def test_travel_period_is_hashable() -> None:
    """Travel periods should behave as immutable domain values."""

    period = TravelPeriod(
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 16),
    )

    assert {period, period} == {period}


def test_travel_period_is_immutable() -> None:
    """Travel-period dates must not change after construction."""

    period = TravelPeriod(
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 16),
    )

    with pytest.raises(FrozenInstanceError):
        period.start_date = date(2026, 11, 11)