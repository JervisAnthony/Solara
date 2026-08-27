"""Core travel-domain models exposed by Solara."""

from solara_travel.domain.attraction import Attraction
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.constraints import (
    ClimateCondition,
    ClimateConstraint,
    ConstraintSeverity,
)
from solara_travel.domain.destination import Destination, DestinationQuery
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.itinerary import (
    AccessibilityStatus,
    ActivityOption,
    DayPeriod,
    DestinationStay,
    DurationEstimate,
    DurationProvenance,
    EstimateConfidence,
    FeasibilityAssessment,
    FeasibilityLevel,
    Itinerary,
    ItineraryActivity,
    ItineraryDay,
    Pace,
    TravelLeg,
    TravellerParty,
    TravellerProfile,
    TravelMode,
    TravelRequirement,
)
from solara_travel.domain.preferences import TravellerInterests, TravellerPreferences
from solara_travel.domain.recommendation import (
    MAX_SELECTED_TRAVEL_SCOPES,
    RecommendationRequest,
)
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.travel_intent import DestinationCandidateProposal
from solara_travel.domain.travel_scope import (
    GeoViewport,
    TravelScope,
    TravelScopeKind,
    TravelScopeSuggestion,
)
from solara_travel.domain.weather import WeatherObservation

__all__ = [
    "Attraction",
    "ActivityOption",
    "ClimateCondition",
    "ClimateConstraint",
    "ConstraintSeverity",
    "Destination",
    "DestinationQuery",
    "DestinationCandidateProposal",
    "DestinationStay",
    "DayPeriod",
    "DurationEstimate",
    "DurationProvenance",
    "EstimateConfidence",
    "AccessibilityStatus",
    "FeasibilityAssessment",
    "FeasibilityLevel",
    "GeoCoordinates",
    "GeoViewport",
    "MAX_SELECTED_TRAVEL_SCOPES",
    "RecommendationRequest",
    "Itinerary",
    "ItineraryActivity",
    "ItineraryDay",
    "Pace",
    "TemperatureComfortRange",
    "TravellerInterests",
    "TravellerPreferences",
    "TravelPeriod",
    "TravellerParty",
    "TravellerProfile",
    "TravelLeg",
    "TravelMode",
    "TravelRequirement",
    "TravelScope",
    "TravelScopeKind",
    "TravelScopeSuggestion",
    "WeatherObservation",
]
