"""Immutable normalized fixture values for explicit offline infrastructure."""

from dataclasses import dataclass

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.destination import Destination
from solara_travel.domain.weather import WeatherObservation


@dataclass(frozen=True, slots=True)
class OfflineDestinationFixture:
    """Normalized synthetic evidence associated with one destination."""

    destination: Destination
    attractions: tuple[Attraction, ...]
    historical_weather: tuple[WeatherObservation, ...]

    def __post_init__(self) -> None:
        """Validate types, uniqueness, and chronological weather ordering."""

        if not isinstance(self.destination, Destination):
            raise TypeError("destination must be a Destination")

        if not isinstance(self.attractions, tuple):
            raise TypeError("attractions must be a tuple")

        if not all(isinstance(attraction, Attraction) for attraction in self.attractions):
            raise TypeError("every attraction must be an Attraction")

        if len(self.attractions) != len(set(self.attractions)):
            raise ValueError("attractions must not contain duplicates")

        if not isinstance(self.historical_weather, tuple):
            raise TypeError("historical_weather must be a tuple")

        if not all(
            isinstance(observation, WeatherObservation) for observation in self.historical_weather
        ):
            raise TypeError("every historical observation must be a WeatherObservation")

        observation_dates = tuple(
            observation.observed_on for observation in self.historical_weather
        )
        if len(observation_dates) != len(set(observation_dates)):
            raise ValueError("historical observation dates must be unique")

        if any(
            current < previous
            for previous, current in zip(
                observation_dates,
                observation_dates[1:],
                strict=False,
            )
        ):
            raise ValueError("historical observations must be strictly increasing by date")


@dataclass(frozen=True, slots=True)
class OfflineTravelDataset:
    """Ordered collection of normalized synthetic destination fixtures."""

    fixtures: tuple[OfflineDestinationFixture, ...]

    def __post_init__(self) -> None:
        """Validate fixture types and unique full-value destinations."""

        if not isinstance(self.fixtures, tuple):
            raise TypeError("fixtures must be a tuple")

        if not all(isinstance(fixture, OfflineDestinationFixture) for fixture in self.fixtures):
            raise TypeError("every fixture must be an OfflineDestinationFixture")

        destinations = tuple(fixture.destination for fixture in self.fixtures)
        if len(destinations) != len(set(destinations)):
            raise ValueError("fixture destinations must be unique")
