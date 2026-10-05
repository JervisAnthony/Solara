"""Bounded route evidence orchestration that degrades to unresolved planning."""

from dataclasses import dataclass
from datetime import date

from solara_travel.domain.destination import Destination
from solara_travel.domain.itinerary import TravelLeg
from solara_travel.domain.journey import JourneyOption
from solara_travel.ports.errors import ProviderError
from solara_travel.ports.journeys import JourneyEvidencePort


@dataclass(frozen=True, slots=True)
class JourneyPlanningService:
    provider: JourneyEvidencePort | None = None

    def options(
        self, origin: Destination, destination: Destination, departure_date: date
    ) -> tuple[JourneyOption, ...]:
        """One call per explicit request, at most three applicable options."""
        TravelLeg(origin, destination)  # validate route before invoking any adapter
        if self.provider is None:
            return ()
        try:
            result = self.provider.options(origin, destination, departure_date, limit=3)
            if not isinstance(result, tuple) or len(result) > 3:
                return ()
            if not all(
                isinstance(option, JourneyOption)
                and option.leg.origin == origin
                and option.leg.destination == destination
                and option.departure_date == departure_date
                for option in result
            ):
                return ()
            if len({option.identity for option in result}) != len(result):
                return ()
            return result
        except ProviderError:
            return ()
