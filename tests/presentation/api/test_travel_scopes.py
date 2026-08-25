"""HTTP and safeguard tests for same-origin geographic suggestions."""

from threading import Event, Thread

import pytest
from fastapi.testclient import TestClient

from solara_travel.application import TravelScopeSuggestionService
from solara_travel.domain import DestinationQuery, TravelScopeKind, TravelScopeSuggestion
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
from solara_travel.presentation.api.safeguards import ApiSafeguards, SafeguardRejection


class FakeProvider:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.queries: list[DestinationQuery] = []

    def suggest_travel_scopes(self, query: DestinationQuery) -> object:
        self.queries.append(query)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _client(
    outcome: object,
    safeguards: PublicAlphaSafeguardSettings | None = None,
) -> tuple[TestClient, FakeProvider]:
    provider = FakeProvider(outcome)
    dependencies = ApiDependencies(
        travel_scope_suggestion_service=TravelScopeSuggestionService(provider)
    )
    settings = ApiSettings(public_alpha_safeguards=safeguards or PublicAlphaSafeguardSettings())
    return TestClient(create_app(settings, dependencies=dependencies)), provider


def test_suggestion_route_returns_bounded_provider_neutral_contract() -> None:
    values = tuple(
        TravelScopeSuggestion(name, kind)
        for name, kind in (
            ("Porto, Portugal", TravelScopeKind.LOCALITY),
            ("Portugal", TravelScopeKind.COUNTRY),
            ("Norte, Portugal", TravelScopeKind.REGION),
        )
    )
    client, provider = _client(values)

    response = client.post("/api/v1/travel-scope-suggestions", json={"query": "  Port  "})

    assert response.status_code == 200
    assert response.json() == {
        "suggestions": [
            {"display_name": "Porto, Portugal", "kind": "locality"},
            {"display_name": "Portugal", "kind": "country"},
            {"display_name": "Norte, Portugal", "kind": "region"},
        ],
        "attribution": "Google Maps",
    }
    assert provider.queries == [DestinationQuery("Port")]


def test_suggestion_route_is_unconfigured_and_structurally_validated() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/travel-scope-suggestions", json={"query": "Port"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "travel_scope_suggestions_unconfigured"
    configured, _ = _client(())
    for payload in ({"query": "P"}, {"query": "x" * 121}, {"query": "Port", "extra": 1}):
        assert configured.post("/api/v1/travel-scope-suggestions", json=payload).status_code == 422


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (ProviderRateLimitError("busy"), 503, "provider_rate_limited"),
        (ProviderAuthenticationError("bad"), 503, "provider_unavailable"),
        (ProviderUnavailableError("down"), 503, "provider_unavailable"),
        (ProviderResponseError("bad"), 502, "provider_invalid_response"),
        (ProviderError("bad"), 502, "provider_invalid_response"),
    ],
)
def test_suggestion_route_maps_provider_errors_safely(
    error: Exception, status: int, code: str
) -> None:
    client, _ = _client(error)
    response = client.post("/api/v1/travel-scope-suggestions", json={"query": "Port"})
    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    assert "Port" not in response.text


def test_suggestion_rate_and_budget_limits_have_retry_after() -> None:
    values = (TravelScopeSuggestion("Porto", TravelScopeKind.LOCALITY),)
    settings = PublicAlphaSafeguardSettings(
        suggestion_rate_limit=1,
        suggestion_budget_limit=2,
    )
    client, provider = _client(values, settings)
    assert client.post("/api/v1/travel-scope-suggestions", json={"query": "Po"}).status_code == 200
    rejected = client.post("/api/v1/travel-scope-suggestions", json={"query": "Por"})
    assert rejected.status_code == 429
    assert rejected.headers["Retry-After"] == "60"
    assert rejected.json()["detail"]["code"] == "suggestion_rate_limited"
    assert len(provider.queries) == 1

    budget_settings = PublicAlphaSafeguardSettings(
        suggestion_rate_limit=3,
        suggestion_budget_limit=1,
    )
    budget_client, _ = _client(values, budget_settings)
    assert (
        budget_client.post("/api/v1/travel-scope-suggestions", json={"query": "Po"}).status_code
        == 200
    )
    exhausted = budget_client.post("/api/v1/travel-scope-suggestions", json={"query": "Por"})
    assert exhausted.status_code == 429
    assert exhausted.json()["detail"]["code"] == "suggestion_budget_exhausted"


def test_suggestion_concurrency_rejects_then_lease_releases() -> None:
    started = Event()
    release = Event()

    class BlockingProvider(FakeProvider):
        def suggest_travel_scopes(self, query: DestinationQuery) -> object:
            started.set()
            assert release.wait(5)
            return self.outcome

    provider = BlockingProvider((TravelScopeSuggestion("Porto", TravelScopeKind.LOCALITY),))
    dependencies = ApiDependencies(
        travel_scope_suggestion_service=TravelScopeSuggestionService(provider)
    )
    settings = ApiSettings(
        public_alpha_safeguards=PublicAlphaSafeguardSettings(suggestion_concurrency_limit=1)
    )
    app = create_app(settings, dependencies=dependencies)
    responses: list[object] = []
    thread = Thread(
        target=lambda: responses.append(
            TestClient(app).post("/api/v1/travel-scope-suggestions", json={"query": "Port"})
        )
    )
    thread.start()
    assert started.wait(5)
    rejected = TestClient(app).post("/api/v1/travel-scope-suggestions", json={"query": "Porto"})
    assert rejected.status_code == 429
    assert rejected.json()["detail"]["code"] == "suggestion_capacity_reached"
    release.set()
    thread.join(5)
    assert responses[0].status_code == 200  # type: ignore[attr-defined]


def test_discovery_budget_is_separate_and_expires() -> None:
    now = [0.0]
    settings = PublicAlphaSafeguardSettings(
        discovery_budget_limit=1,
        discovery_budget_window_seconds=10,
    )
    safeguards = ApiSafeguards(settings, clock=lambda: now[0])
    assert safeguards.admit_discovery() is None
    rejected = safeguards.admit_discovery()
    assert isinstance(rejected, SafeguardRejection)
    assert rejected.code == "discovery_budget_exhausted"
    assert rejected.retry_after_seconds == 10
    now[0] = 11
    assert safeguards.admit_discovery() is None


def test_dependencies_validate_suggestion_service() -> None:
    with pytest.raises(TypeError, match="travel_scope_suggestion_service"):
        ApiDependencies(travel_scope_suggestion_service="bad")  # type: ignore[arg-type]
