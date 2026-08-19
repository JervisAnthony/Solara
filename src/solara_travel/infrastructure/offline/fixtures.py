"""Bundled, unmistakably synthetic fixture data for explicit offline workflows."""

from datetime import date

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation
from solara_travel.infrastructure.offline.dataset import (
    OfflineDestinationFixture,
    OfflineTravelDataset,
)

_HISTORICAL_YEARS = (2020, 2021, 2022, 2023, 2024)
_APRIL_DAYS = (10, 11, 12)


def _weather_series(
    temperatures: tuple[float, float, float],
    *,
    base_humidity: float,
    base_precipitation: float,
) -> tuple[WeatherObservation, ...]:
    """Build five years of ordered synthetic evidence for April 10 through 12."""

    return tuple(
        WeatherObservation(
            observed_on=date(year, 4, day),
            temperature_celsius=temperatures[day_offset] + year_offset * 0.1,
            relative_humidity_percent=base_humidity + year_offset + day_offset,
            precipitation_mm=base_precipitation + year_offset * 0.1 + day_offset * 0.2,
        )
        for year_offset, year in enumerate(_HISTORICAL_YEARS)
        for day_offset, day in enumerate(_APRIL_DAYS)
    )


_SUNSPIRE_BAY = Destination(
    name="Sunspire Bay",
    country="Fixtureland",
    coordinates=GeoCoordinates(latitude=12.0, longitude=24.0),
)
_MISTRAL_HOLLOW = Destination(
    name="Mistral Hollow",
    country="Fixtureland",
    coordinates=GeoCoordinates(latitude=32.0, longitude=44.0),
)
_FROSTGLASS_VALE = Destination(
    name="Frostglass Vale",
    country="Fixtureland",
    coordinates=GeoCoordinates(latitude=-22.0, longitude=64.0),
)

DEFAULT_OFFLINE_HISTORICAL_PERIOD = TravelPeriod(
    start_date=date(2020, 4, 10),
    end_date=date(2024, 4, 12),
)

DEFAULT_OFFLINE_DATASET = OfflineTravelDataset(
    fixtures=(
        OfflineDestinationFixture(
            destination=_SUNSPIRE_BAY,
            attractions=(
                Attraction(
                    "Prism Tidewalk",
                    "synthetic waterfront",
                    GeoCoordinates(12.1, 24.1),
                ),
                Attraction(
                    "Lantern Cloud Garden",
                    "synthetic garden",
                    GeoCoordinates(12.2, 24.2),
                ),
            ),
            historical_weather=_weather_series(
                (22.0, 23.0, 24.0),
                base_humidity=54.0,
                base_precipitation=0.4,
            ),
        ),
        OfflineDestinationFixture(
            destination=_MISTRAL_HOLLOW,
            attractions=(
                Attraction(
                    "Copperwind Observatory",
                    "synthetic observatory",
                    GeoCoordinates(32.1, 44.1),
                ),
                Attraction(
                    "Echo Ribbon Market",
                    "synthetic market",
                    GeoCoordinates(32.2, 44.2),
                ),
            ),
            historical_weather=_weather_series(
                (30.0, 31.0, 32.0),
                base_humidity=42.0,
                base_precipitation=0.1,
            ),
        ),
        OfflineDestinationFixture(
            destination=_FROSTGLASS_VALE,
            attractions=(
                Attraction(
                    "Aurora Bell Archive",
                    "synthetic archive",
                    GeoCoordinates(-21.9, 64.1),
                ),
                Attraction(
                    "Crystal Moss Crossing",
                    "synthetic trail",
                    GeoCoordinates(-21.8, 64.2),
                ),
            ),
            historical_weather=_weather_series(
                (4.0, 5.0, 6.0),
                base_humidity=68.0,
                base_precipitation=1.2,
            ),
        ),
    )
)
