"""Core travel-domain models exposed by Solara."""

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.preferences import TravellerInterests, TravellerPreferences
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation

__all__ = [
    "Attraction",
    "Destination",
    "GeoCoordinates",
    "RecommendationRequest",
    "TemperatureComfortRange",
    "TravellerInterests",
    "TravellerPreferences",
    "TravelPeriod",
    "WeatherObservation",
]