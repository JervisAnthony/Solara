"""Planning evidence independent of schedules, fares, availability and bookings."""

from dataclasses import dataclass
from datetime import date

from solara_travel.domain.itinerary import DurationProvenance, TravelLeg


@dataclass(frozen=True, slots=True)
class JourneyOption:
    """A dated, identified planning option grounded in normalized route evidence."""

    identity: str
    departure_date: date
    leg: TravelLeg

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str) or not self.identity.strip():
            raise ValueError("journey identity must be non-blank")
        if type(self.departure_date) is not date:
            raise TypeError("departure_date must be a date")
        if not isinstance(self.leg, TravelLeg):
            raise TypeError("leg must be TravelLeg")
        if not self.leg.verified or self.leg.duration is None:
            raise ValueError("journey options require verified timing evidence")
        if self.leg.duration.provenance is not DurationProvenance.PROVIDER:
            raise ValueError("journey timing must have provider provenance")

    @property
    def planning_only(self) -> bool:
        return True
