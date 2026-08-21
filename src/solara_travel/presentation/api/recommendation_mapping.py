"""Pure mappings between recommendation HTTP schemas and Solara values."""

from solara_travel.application import RecommendationNarration, RecommendationResult
from solara_travel.domain import (
    Attraction,
    Destination,
    GeoCoordinates,
    RecommendationRequest,
    TravellerInterests,
    TravellerPreferences,
    TravelPeriod,
)
from solara_travel.presentation.api.recommendation_schemas import (
    AttractionResponse,
    CoordinatesResponse,
    DestinationRecommendationResponse,
    DestinationResponse,
    RecommendationEvidenceResponse,
    RecommendationRequestBody,
    RecommendationRequestResponse,
    RecommendationResponse,
    ScoreComponentResponse,
    SeasonalWeatherResponse,
    TemperatureComfortRangeResponse,
    TemperatureComfortResponse,
    TravellerPreferencesResponse,
    TravelPeriodResponse,
)


def to_domain_recommendation_request(
    request_body: RecommendationRequestBody,
) -> RecommendationRequest:
    """Construct the authoritative domain request from typed HTTP input."""

    interests = (
        None
        if request_body.preferences.interests is None
        else TravellerInterests(tuple(request_body.preferences.interests))
    )
    preferences = TravellerPreferences(
        interests=interests,
        preferred_pace=request_body.preferences.preferred_pace,
        preferred_climate=request_body.preferences.preferred_climate,
    )
    destination = (
        None
        if request_body.destination is None
        else Destination(
            name=request_body.destination.name,
            country=request_body.destination.country,
            coordinates=GeoCoordinates(
                latitude=request_body.destination.coordinates.latitude,
                longitude=request_body.destination.coordinates.longitude,
            ),
        )
    )
    return RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=request_body.travel_period.start_date,
            end_date=request_body.travel_period.end_date,
        ),
        preferences=preferences,
        destination=destination,
    )


def recommendation_result_to_response(
    result: RecommendationResult,
    narration: RecommendationNarration | None,
) -> RecommendationResponse:
    """Serialize selected authoritative values without rescoring or reordering."""

    recommendations = [
        DestinationRecommendationResponse(
            rank=rank,
            destination=_destination_response(recommendation.destination),
            score=recommendation.score,
            components=[
                ScoreComponentResponse(
                    name=component.name,
                    score=component.score,
                    weight=component.weight,
                    weighted_contribution=component.weighted_contribution,
                )
                for component in recommendation.components
            ],
            evidence=RecommendationEvidenceResponse(
                attractions=[
                    _attraction_response(attraction)
                    for attraction in recommendation.evidence.attractions
                ],
                seasonal_weather=SeasonalWeatherResponse(
                    target_period=_travel_period_response(
                        recommendation.evidence.seasonal_weather.target_period
                    ),
                    observation_count=(recommendation.evidence.seasonal_weather.observation_count),
                    historical_years=list(
                        recommendation.evidence.seasonal_weather.historical_years
                    ),
                    historical_year_count=(
                        recommendation.evidence.seasonal_weather.historical_year_count
                    ),
                    mean_temperature_celsius=(
                        recommendation.evidence.seasonal_weather.mean_temperature_celsius
                    ),
                    minimum_temperature_celsius=(
                        recommendation.evidence.seasonal_weather.minimum_temperature_celsius
                    ),
                    maximum_temperature_celsius=(
                        recommendation.evidence.seasonal_weather.maximum_temperature_celsius
                    ),
                    mean_relative_humidity_percent=(
                        recommendation.evidence.seasonal_weather.mean_relative_humidity_percent
                    ),
                    mean_daily_precipitation_mm=(
                        recommendation.evidence.seasonal_weather.mean_daily_precipitation_mm
                    ),
                ),
                temperature_comfort=TemperatureComfortResponse(
                    score=recommendation.evidence.seasonal_temperature_comfort.score,
                    comfort_range=TemperatureComfortRangeResponse(
                        minimum_celsius=(
                            recommendation.evidence.seasonal_temperature_comfort.comfort_range.minimum_celsius
                        ),
                        maximum_celsius=(
                            recommendation.evidence.seasonal_temperature_comfort.comfort_range.maximum_celsius
                        ),
                        tolerance_celsius=(
                            recommendation.evidence.seasonal_temperature_comfort.comfort_range.tolerance_celsius
                        ),
                    ),
                    within_preferred_fraction=(
                        recommendation.evidence.seasonal_temperature_comfort.within_preferred_fraction
                    ),
                    mean_deviation_celsius=(
                        recommendation.evidence.seasonal_temperature_comfort.mean_deviation_celsius
                    ),
                ),
            ),
        )
        for rank, recommendation in enumerate(result.recommendations, start=1)
    ]
    return RecommendationResponse(
        request=_request_response(result.request),
        recommendation_count=result.recommendation_count,
        has_recommendations=result.has_recommendations,
        recommendations=recommendations,
        has_narration=narration is not None,
        narration=None if narration is None else narration.text,
    )


def _request_response(request: RecommendationRequest) -> RecommendationRequestResponse:
    interests = request.preferences.interests
    return RecommendationRequestResponse(
        travel_period=_travel_period_response(request.travel_period),
        preferences=TravellerPreferencesResponse(
            interests=None if interests is None else list(interests.interests),
            preferred_pace=request.preferences.preferred_pace,
            preferred_climate=request.preferences.preferred_climate,
        ),
        destination=(
            None if request.destination is None else _destination_response(request.destination)
        ),
    )


def _travel_period_response(period: TravelPeriod) -> TravelPeriodResponse:
    return TravelPeriodResponse(start_date=period.start_date, end_date=period.end_date)


def _coordinates_response(coordinates: GeoCoordinates) -> CoordinatesResponse:
    return CoordinatesResponse(
        latitude=coordinates.latitude,
        longitude=coordinates.longitude,
    )


def _destination_response(destination: Destination) -> DestinationResponse:
    return DestinationResponse(
        name=destination.name,
        country=destination.country,
        coordinates=_coordinates_response(destination.coordinates),
    )


def _attraction_response(attraction: Attraction) -> AttractionResponse:
    return AttractionResponse(
        name=attraction.name,
        category=attraction.category,
        coordinates=_coordinates_response(attraction.coordinates),
    )
