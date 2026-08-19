"""Credential-free providers backed by normalized in-memory fixture data."""

from dataclasses import dataclass

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.destination import Destination
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation
from solara_travel.infrastructure.offline.dataset import OfflineTravelDataset


@dataclass(frozen=True, slots=True)
class OfflinePlacesProvider:
    """Provide an explicit deterministic candidate pool and attraction evidence."""

    dataset: OfflineTravelDataset

    def __post_init__(self) -> None:
        """Require an immutable offline dataset."""

        if not isinstance(self.dataset, OfflineTravelDataset):
            raise TypeError("dataset must be an OfflineTravelDataset")

    def discover_destinations(
        self,
        request: RecommendationRequest,
    ) -> tuple[Destination, ...]:
        """Return fixture destinations in their declared order."""

        if not isinstance(request, RecommendationRequest):
            raise TypeError("request must be a RecommendationRequest")

        return tuple(fixture.destination for fixture in self.dataset.fixtures)

    def discover_attractions(
        self,
        destination: Destination,
    ) -> tuple[Attraction, ...]:
        """Return ordered fixture attractions for an exact destination match."""

        if not isinstance(destination, Destination):
            raise TypeError("destination must be a Destination")

        for fixture in self.dataset.fixtures:
            if fixture.destination == destination:
                return fixture.attractions

        return ()


@dataclass(frozen=True, slots=True)
class OfflineHistoricalWeatherProvider:
    """Provide normalized historical fixture weather without fabrication."""

    dataset: OfflineTravelDataset

    def __post_init__(self) -> None:
        """Require an immutable offline dataset."""

        if not isinstance(self.dataset, OfflineTravelDataset):
            raise TypeError("dataset must be an OfflineTravelDataset")

    def get_historical_weather(
        self,
        destination: Destination,
        period: TravelPeriod,
    ) -> tuple[WeatherObservation, ...]:
        """Return chronologically ordered observations inside an inclusive period."""

        if not isinstance(destination, Destination):
            raise TypeError("destination must be a Destination")

        if not isinstance(period, TravelPeriod):
            raise TypeError("period must be a TravelPeriod")

        for fixture in self.dataset.fixtures:
            if fixture.destination == destination:
                return tuple(
                    observation
                    for observation in fixture.historical_weather
                    if period.start_date <= observation.observed_on <= period.end_date
                )

        return ()
