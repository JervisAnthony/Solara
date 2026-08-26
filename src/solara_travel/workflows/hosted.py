"""Composition for the explicitly configured hosted recommendation workflow."""

from dataclasses import dataclass

from solara_travel.application import (
    PhotoDeliveryService,
    PostcardEnrichmentService,
    RecommendationNarrationService,
    RecommendationService,
    TravelScopeSuggestionService,
)
from solara_travel.config import DeploymentSettings
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.travel import TravelPeriod
from solara_travel.infrastructure.discovery import OpenAIDestinationCandidateProposalProvider
from solara_travel.infrastructure.http import UrllibJsonHttpTransport
from solara_travel.infrastructure.places import (
    GooglePhotoMediaProvider,
    GooglePlacesHttpClient,
    GooglePlacesProvider,
    GooglePostcardMetadataProvider,
    SignedPhotoHandleCodec,
)
from solara_travel.infrastructure.weather import (
    OpenMeteoHistoricalWeatherHttpClient,
    OpenMeteoHistoricalWeatherProvider,
)
from solara_travel.workflows.narration import (
    build_openai_recommendation_narration_service,
)


@dataclass(frozen=True, slots=True)
class HostedServices:
    """Application services composed for one hosted application instance."""

    recommendation_service: RecommendationService
    narration_service: RecommendationNarrationService
    travel_scope_suggestion_service: TravelScopeSuggestionService
    postcard_enrichment_service: PostcardEnrichmentService
    photo_delivery_service: PhotoDeliveryService


def build_hosted_services(settings: DeploymentSettings) -> HostedServices:
    """Compose live providers without contacting them during construction."""

    if not isinstance(settings, DeploymentSettings):
        raise TypeError("settings must be DeploymentSettings")

    transport = UrllibJsonHttpTransport()
    google = settings.google_places
    weather = settings.open_meteo
    policy = settings.recommendation_policy
    narration = settings.openai_narration

    places_provider = GooglePlacesProvider(
        GooglePlacesHttpClient(
            api_key=google.api_key,
            transport=transport,
            timeout_seconds=google.timeout_seconds,
            destination_page_size=google.destination_page_size,
            attraction_max_results=google.attraction_max_results,
            attraction_radius_meters=google.attraction_radius_meters,
        )
    )
    recommendation_service = RecommendationService(
        places_provider=places_provider,
        weather_provider=OpenMeteoHistoricalWeatherProvider(
            OpenMeteoHistoricalWeatherHttpClient(
                transport=transport,
                timeout_seconds=weather.timeout_seconds,
            )
        ),
        historical_period=TravelPeriod(
            policy.historical_start_date,
            policy.historical_end_date,
        ),
        comfort_range=TemperatureComfortRange(
            policy.comfort_min_celsius,
            policy.comfort_max_celsius,
            policy.comfort_tolerance_celsius,
        ),
        seasonal_weight=policy.seasonal_weight,
        scope_resolver=places_provider,
        candidate_proposal_provider=OpenAIDestinationCandidateProposalProvider(
            api_key=narration.api_key,
            model=narration.model,
            transport=transport,
            timeout_seconds=narration.timeout_seconds,
            max_output_tokens=min(narration.max_output_tokens, 900),
        ),
    )
    narration_service = build_openai_recommendation_narration_service(
        api_key=narration.api_key,
        model=narration.model,
        timeout_seconds=narration.timeout_seconds,
        max_output_tokens=narration.max_output_tokens,
        transport=transport,
    )
    photo_handle_codec = SignedPhotoHandleCodec()
    photo_metadata_provider = GooglePostcardMetadataProvider(
        api_key=google.api_key,
        transport=transport,
        timeout_seconds=google.timeout_seconds,
    )
    photo_media_provider = GooglePhotoMediaProvider(
        api_key=google.api_key,
        json_transport=transport,
        binary_transport=transport,
        timeout_seconds=google.timeout_seconds,
    )
    return HostedServices(
        recommendation_service,
        narration_service,
        TravelScopeSuggestionService(places_provider),
        PostcardEnrichmentService(photo_metadata_provider, photo_handle_codec),
        PhotoDeliveryService(photo_handle_codec, photo_media_provider),
    )
