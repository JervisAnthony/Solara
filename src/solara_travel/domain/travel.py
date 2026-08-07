"""Travel-period value objects used by the Solara domain."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class TravelPeriod:
    """An immutable inclusive calendar period representing a trip.

    The start and end values must be calendar dates rather than datetimes.
    A period may represent a single-day trip when both dates are equal.
    """

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        """Validate the travel period's date values and ordering."""

        if (
            not isinstance(self.start_date, date)
            or isinstance(self.start_date, datetime)
            or not isinstance(self.end_date, date)
            or isinstance(self.end_date, datetime)
        ):
            raise TypeError("start date and end date must be date values")

        if self.end_date < self.start_date:
            raise ValueError("end date must not be before start date")

    @property
    def duration_days(self) -> int:
        """Return the inclusive number of calendar days in the trip."""

        return (self.end_date - self.start_date).days + 1