"""End-to-end HTTP contracts for scoped and global locality discovery."""

from datetime import date

from fastapi.testclient import TestClient

from solara_travel.application import RecommendationService
from solara_travel.domain import (
    Attraction,
    Destination,
    DestinationCandidateProposal,
    DestinationQuery,
    GeoCoordinates,
    RecommendationRequest,
    TemperatureComfortRange,
    TravelPeriod,
    TravelScope,
    TravelScopeKind,
    WeatherObservation,
)
from solara_travel.ports import ProviderUnavailableError
from solara_travel.presentation.api import ApiDependencies, create_app


def _locality(name: str) -> TravelScope:
    coordinates = {
        "Porto": GeoCoordinates(41.15, -8.61),
        "Lisbon": GeoCoordinates(38.72, -9.14),
    }[name]
    return TravelScope(
        f"{name}, Portugal",
        TravelScopeKind.LOCALITY,
        "Portugal",
        "PT",
        canonical_name=name,
        center=coordinates,
    )


class DiscoveryPlaces:
    def __init__(self) -> None:
        self.scopes = {
            "Portugal": TravelScope("Portugal", TravelScopeKind.COUNTRY, "Portugal", "PT"),
            "Porto": _locality("Porto"),
            "Porto, Portugal": _locality("Porto"),
            "Lisbon": _locality("Lisbon"),
            "Lisbon, Portugal": _locality("Lisbon"),
        }

    def discover_destinations(self, request: RecommendationRequest) -> tuple[Destination, ...]:
        return ()

    def resolve_travel_scope(self, query: DestinationQuery) -> TravelScope | None:
        return self.scopes.get(query.value)

    def discover_attractions(self, destination: Destination) -> tuple[Attraction, ...]:
        return ()


class DiscoveryWeather:
    def get_historical_weather(
        self, destination: Destination, period: TravelPeriod
    ) -> tuple[WeatherObservation, ...]:
        return (WeatherObservation(date(2023, 5, 2), 22, 60, 0),)


class CandidateProvider:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[TravelScope | None] = []

    def propose_candidates(
        self, request: RecommendationRequest, scope: TravelScope | None
    ) -> DestinationCandidateProposal:
        self.calls.append(scope)
        if self.error is not None:
            raise self.error
        names = ("Porto",) if scope is not None else ("Lisbon", "Porto")
        return DestinationCandidateProposal((), (), (), names)


def _client(
    proposal: CandidateProvider | None = None,
) -> tuple[TestClient, CandidateProvider]:
    provider = proposal or CandidateProvider()
    places = DiscoveryPlaces()
    service = RecommendationService(
        places,
        DiscoveryWeather(),
        TravelPeriod(date(2020, 1, 1), date(2024, 12, 31)),
        TemperatureComfortRange(18, 28, 10),
        scope_resolver=places,
        candidate_proposal_provider=provider,
    )
    return TestClient(create_app(dependencies=ApiDependencies(service))), provider


def _payload(*queries: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "travel_period": {"start_date": "2027-05-01", "end_date": "2027-05-05"},
        "preferences": {
            "interests": ["food"],
            "preferred_pace": "balanced",
            "preferred_climate": "mild",
            "trip_description": "  Cafés, coast, and a relaxed pace.  ",
        },
    }
    if queries:
        payload["destination_queries"] = list(queries)
    return payload


def test_country_scope_returns_only_validated_locality_and_scope_metadata() -> None:
    client, proposal = _client()
    response = client.post("/api/v1/recommendations", json=_payload("Portugal"))
    assert response.status_code == 200
    request = response.json()["request"]
    assert request["destination_mode"] == "scope_discovery"
    assert request["travel_scope"] == {"display_name": "Portugal", "kind": "country"}
    assert request["preferences"]["trip_description"] == "Cafés, coast, and a relaxed pace."
    assert response.json()["recommendations"][0]["destination"]["name"] == "Porto"
    assert proposal.calls[0].kind is TravelScopeKind.COUNTRY  # type: ignore[union-attr]


def test_blank_discovery_returns_nonempty_validated_shortlist() -> None:
    client, proposal = _client()
    response = client.post("/api/v1/recommendations", json=_payload())
    assert response.status_code == 200
    assert response.json()["recommendation_count"] == 2
    assert response.json()["request"]["destination_mode"] == "discovery"
    assert proposal.calls == [None]


def test_explicit_locality_bypasses_ai_and_broad_combination_is_rejected() -> None:
    client, proposal = _client()
    explicit = client.post("/api/v1/recommendations", json=_payload("Porto"))
    assert explicit.status_code == 200
    assert explicit.json()["request"]["destination_mode"] == "explicit_queries"
    assert proposal.calls == []
    mixed = client.post("/api/v1/recommendations", json=_payload("Portugal", "Lisbon"))
    assert mixed.status_code == 422
    assert mixed.json()["detail"]["code"] == "broad_scope_combination_not_supported"


def test_candidate_ai_failure_is_safe_and_optional_field_remains_backward_compatible() -> None:
    client, _ = _client(CandidateProvider(ProviderUnavailableError("secret provider detail")))
    response = client.post("/api/v1/recommendations", json=_payload())
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "destination_discovery_unavailable"
    assert "secret provider detail" not in response.text

    compatible, _ = _client()
    payload = _payload("Porto")
    payload["preferences"].pop("trip_description")  # type: ignore[union-attr]
    assert compatible.post("/api/v1/recommendations", json=payload).status_code == 200
