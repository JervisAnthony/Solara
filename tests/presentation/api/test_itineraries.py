"""HTTP tests for the bounded, provider-backed Itinerary Studio palette."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from solara_travel.application import RecommendationService
from solara_travel.domain import (
    Attraction,
    Destination,
    GeoCoordinates,
    RecommendationRequest,
    TemperatureComfortRange,
    TravelPeriod,
    TravelScope,
    TravelScopeKind,
    WeatherObservation,
)
from solara_travel.ports import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.presentation.api import (
    ApiDependencies,
    ApiSettings,
    PublicAlphaSafeguardSettings,
    create_app,
)
from solara_travel.workflows import build_offline_recommendation_service


class StudioPlaces:
    def __init__(self, scope: TravelScope | None, attractions: object = ()) -> None:
        self.scope = scope
        self.attractions = attractions

    def discover_destinations(self, request: RecommendationRequest) -> tuple[Destination, ...]:
        del request
        return ()

    def discover_attractions(self, destination: Destination) -> tuple[Attraction, ...]:
        del destination
        if isinstance(self.attractions, BaseException):
            raise self.attractions
        return self.attractions  # type: ignore[return-value]

    def resolve_travel_scope(self, query: object) -> TravelScope | None:
        del query
        return self.scope


class StudioWeather:
    def get_historical_weather(
        self, destination: Destination, period: TravelPeriod
    ) -> tuple[WeatherObservation, ...]:
        del destination, period
        return (WeatherObservation(date(2020, 1, 1), 20, 50, 0),)


def locality() -> TravelScope:
    return TravelScope(
        "Bangkok, Thailand",
        TravelScopeKind.LOCALITY,
        "Thailand",
        "TH",
        canonical_name="Bangkok",
        center=GeoCoordinates(13.75, 100.5),
    )


def service(places: StudioPlaces, *, explicit_resolver: bool = True) -> RecommendationService:
    return RecommendationService(
        places,
        StudioWeather(),
        TravelPeriod(date(2020, 1, 1), date(2024, 12, 31)),
        TemperatureComfortRange(18, 28, 10),
        scope_resolver=places if explicit_resolver else None,
    )


def client(places: StudioPlaces, settings: ApiSettings | None = None) -> TestClient:
    return TestClient(
        create_app(settings, dependencies=ApiDependencies(recommendation_service=service(places)))
    )


def test_activity_palette_returns_typed_trust_metadata_and_bounded_options() -> None:
    attractions = (
        Attraction("Grand Palace", "museum", GeoCoordinates(13.75, 100.49)),
        Attraction("Unknown Place", "other", GeoCoordinates(13.76, 100.50)),
    )
    response = client(StudioPlaces(locality(), attractions)).post(
        "/api/v1/itinerary-activities",
        json={"destination_query": " Bangkok, Thailand "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["destination"]["name"] == "Bangkok"
    assert payload["maximum_options"] == 12
    assert payload["activities"][0]["duration"] == {
        "minimum_minutes": 60,
        "maximum_minutes": 120,
        "typical_minutes": 90,
        "provenance": "category_heuristic",
        "confidence": "medium",
        "is_estimate": True,
    }
    assert payload["activities"][0]["accessibility"] == "unknown"
    assert payload["activities"][1]["duration"] is None
    assert "not live" in payload["duration_notice"]


def test_activity_palette_requires_configuration_and_locality_resolution() -> None:
    unconfigured = TestClient(create_app()).post(
        "/api/v1/itinerary-activities", json={"destination_query": "Bangkok"}
    )
    assert unconfigured.status_code == 503

    no_resolver = TestClient(
        create_app(
            dependencies=ApiDependencies(
                build_offline_recommendation_service(
                    comfort_range=TemperatureComfortRange(18, 28, 10)
                )
            )
        )
    ).post("/api/v1/itinerary-activities", json={"destination_query": "Bangkok"})
    assert no_resolver.status_code == 503

    fallback_client = TestClient(
        create_app(
            dependencies=ApiDependencies(
                recommendation_service=service(StudioPlaces(locality()), explicit_resolver=False)
            )
        )
    )
    assert (
        fallback_client.post(
            "/api/v1/itinerary-activities", json={"destination_query": "Bangkok"}
        ).status_code
        == 200
    )

    for scope in (
        None,
        TravelScope("Thailand", TravelScopeKind.COUNTRY, "Thailand", "TH"),
    ):
        response = client(StudioPlaces(scope)).post(
            "/api/v1/itinerary-activities", json={"destination_query": "Thailand"}
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "destination_not_found"


@pytest.mark.parametrize(
    ("outcome", "status_code"),
    [
        (ProviderUnavailableError("offline"), 503),
        (ProviderAuthenticationError("misconfigured"), 503),
        (ProviderRateLimitError("busy"), 503),
        (ProviderResponseError("bad"), 502),
        (ProviderError("failed"), 502),
        ([], 502),
    ],
)
def test_activity_palette_degrades_safely_for_provider_failures(
    outcome: object, status_code: int
) -> None:
    response = client(StudioPlaces(locality(), outcome)).post(
        "/api/v1/itinerary-activities", json={"destination_query": "Bangkok"}
    )
    assert response.status_code == status_code


def test_activity_palette_uses_existing_process_local_discovery_safeguard() -> None:
    settings = ApiSettings(
        public_alpha_safeguards=PublicAlphaSafeguardSettings(suggestion_rate_limit=1)
    )
    configured = client(StudioPlaces(locality()), settings)
    assert (
        configured.post(
            "/api/v1/itinerary-activities", json={"destination_query": "Bangkok"}
        ).status_code
        == 200
    )
    rejected = configured.post(
        "/api/v1/itinerary-activities", json={"destination_query": "Bangkok"}
    )
    assert rejected.status_code == 429
    assert rejected.json()["detail"]["code"] == "suggestion_rate_limited"


def test_activity_palette_rejects_malformed_or_unknown_input() -> None:
    configured = client(StudioPlaces(locality()))
    assert (
        configured.post("/api/v1/itinerary-activities", json={"destination_query": " "}).status_code
        == 422
    )
    assert (
        configured.post(
            "/api/v1/itinerary-activities",
            json={"destination_query": "Bangkok", "unexpected": True},
        ).status_code
        == 422
    )
