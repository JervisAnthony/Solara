"""Provider contract for normalized historical weather evidence."""

from typing import Protocol, runtime_checkable

from solara_travel.domain.destination import Destination
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation


@runtime_checkable
class HistoricalWeatherProvider(Protocol):
    """Contract for retrieving normalized historical weather observations."""

    def get_historical_weather(
        self,
        destination: Destination,
        period: TravelPeriod,
    ) -> tuple[WeatherObservation, ...]:
        """Return historical observations for a destination and period."""
        ...
