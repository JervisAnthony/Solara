"""Pure mappings between recommendation HTTP schemas and Solara values."""

from solara_travel.application import (
    PostcardCollection,
    RecommendationNarration,
    RecommendationResult,
    WayfinderNarrative,
)
from solara_travel.domain import (
    Attraction,
    Destination,
    DestinationQuery,
    GeoCoordinates,
    RecommendationRequest,
    TravellerInterests,
    TravellerPreferences,
    TravelPeriod,
    TravelScope,
)
from solara_travel.presentation.api.recommendation_schemas import (
    AttractionResponse,
    CoordinatesResponse,
    DestinationRecommendationResponse,
    DestinationResponse,
    PhotoAuthorAttributionResponse,
    PostcardPhotoResponse,
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
    TravelScopeResponse,
    WayfinderDestinationNoteResponse,
    WayfinderNarrativeResponse,
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
        trip_description=request_body.preferences.trip_description,
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
        destination_queries=tuple(
            DestinationQuery(value) for value in (request_body.destination_queries or [])
        ),
    )


def recommendation_result_to_response(
    result: RecommendationResult,
    narration: RecommendationNarration | None,
    *,
    wayfinder: WayfinderNarrative | None = None,
    postcards: PostcardCollection | None = None,
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
            postcards=_postcard_responses(postcards, recommendation.destination),
        )
        for rank, recommendation in enumerate(result.recommendations, start=1)
    ]
    return RecommendationResponse(
        request=_request_response(
            result.request,
            destination_mode=result.destination_mode,
            travel_scope=result.travel_scope,
        ),
        recommendation_count=result.recommendation_count,
        has_recommendations=result.has_recommendations,
        recommendations=recommendations,
        has_narration=narration is not None,
        narration=None if narration is None else narration.text,
        wayfinder=(
            None
            if wayfinder is None
            else WayfinderNarrativeResponse(
                opening=wayfinder.opening,
                destination_notes=[
                    WayfinderDestinationNoteResponse(
                        destination=note.destination,
                        why_it_fits=note.why_it_fits,
                        seasonal_feel=note.seasonal_feel,
                        good_to_know=note.good_to_know,
                        signature_highlights=list(note.signature_highlights),
                    )
                    for note in wayfinder.destination_notes
                ],
                comparison_note=wayfinder.comparison_note,
            )
        ),
    )


def _postcard_responses(
    postcards: PostcardCollection | None,
    destination: Destination,
) -> list[PostcardPhotoResponse]:
    destination_postcards = None if postcards is None else postcards.for_destination(destination)
    if destination_postcards is None:
        return []
    return [
        PostcardPhotoResponse(
            image_path=photo.image_path,
            place_name=photo.place_name,
            width_px=photo.width_px,
            height_px=photo.height_px,
            google_maps_uri=photo.google_maps_uri,
            author_attributions=[
                PhotoAuthorAttributionResponse(
                    display_name=attribution.display_name,
                    profile_uri=attribution.profile_uri,
                )
                for attribution in photo.author_attributions
            ],
        )
        for photo in destination_postcards.photos
    ]


def _request_response(
    request: RecommendationRequest,
    *,
    destination_mode: str | None,
    travel_scope: TravelScope | None,
) -> RecommendationRequestResponse:
    interests = request.preferences.interests
    return RecommendationRequestResponse(
        travel_period=_travel_period_response(request.travel_period),
        preferences=TravellerPreferencesResponse(
            interests=None if interests is None else list(interests.interests),
            preferred_pace=request.preferences.preferred_pace,
            preferred_climate=request.preferences.preferred_climate,
            trip_description=request.preferences.trip_description,
        ),
        destination=(
            None if request.destination is None else _destination_response(request.destination)
        ),
        destination_queries=[query.value for query in request.destination_queries],
        destination_mode=destination_mode
        or ("pre_resolved" if request.destination is not None else "discovery"),
        travel_scope=(
            None
            if travel_scope is None
            else TravelScopeResponse(
                display_name=travel_scope.display_name,
                kind=travel_scope.kind.value,
            )
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
