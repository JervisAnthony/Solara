"""HTTP tests for the versioned recommendation API."""

from datetime import date
from threading import Event, Thread

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from solara_travel.application import RecommendationNarrationService, RecommendationService
from solara_travel.domain import (
    Destination,
    TemperatureComfortRange,
    TravelPeriod,
)
from solara_travel.infrastructure.offline import DEFAULT_OFFLINE_DATASET, OfflineTravelDataset
from solara_travel.ports import (
    NarrationPrompt,
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
from solara_travel.presentation.api.recommendation_schemas import RecommendationRequestBody
from solara_travel.presentation.api.routes import recommendations as recommendation_routes
from solara_travel.presentation.api.safeguards import ApiSafeguards
from solara_travel.workflows import build_offline_recommendation_service


def _valid_payload() -> dict[str, object]:
    return {
        "travel_period": {"start_date": "2026-04-10", "end_date": "2026-04-12"},
        "preferences": {
            "interests": ["nature"],
            "preferred_pace": "relaxed",
            "preferred_climate": "warm",
        },
        "destination": None,
    }


def _offline_service(*, empty: bool = False) -> RecommendationService:
    kwargs = {"dataset": OfflineTravelDataset(())} if empty else {}
    return build_offline_recommendation_service(
        comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0),
        **kwargs,
    )


def _configured_client(
    recommendation_service: RecommendationService | None = None,
    narration_service: RecommendationNarrationService | None = None,
    *,
    raise_server_exceptions: bool = True,
) -> TestClient:
    dependencies = ApiDependencies(recommendation_service or _offline_service(), narration_service)
    return TestClient(
        create_app(dependencies=dependencies),
        raise_server_exceptions=raise_server_exceptions,
    )


class FakeNarrationProvider:
    """Return or raise one configured narration outcome."""

    def __init__(self, outcome: str | BaseException) -> None:
        self.outcome = outcome
        self.prompts: list[NarrationPrompt] = []

    def generate(self, prompt: NarrationPrompt) -> str:
        self.prompts.append(prompt)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class ErrorPlacesProvider:
    """Raise one configured error during destination discovery."""

    def __init__(self, error: BaseException) -> None:
        self.error = error

    def discover_destinations(self, request: object) -> tuple[Destination, ...]:
        raise self.error

    def discover_attractions(self, destination: Destination) -> tuple[object, ...]:
        return ()


class UnusedWeatherProvider:
    """Satisfy the weather port for discovery-failure tests."""

    def get_historical_weather(
        self, destination: Destination, period: TravelPeriod
    ) -> tuple[object, ...]:
        return ()


def _error_service(error: BaseException) -> RecommendationService:
    return RecommendationService(
        places_provider=ErrorPlacesProvider(error),
        weather_provider=UnusedWeatherProvider(),
        historical_period=TravelPeriod(date(2020, 1, 1), date(2024, 12, 31)),
        comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0),
    )


def test_default_app_is_healthy_but_recommendation_service_is_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr(
        recommendation_routes,
        "emit_event",
        lambda event, **fields: events.append({"event": event, **fields}),
    )
    client = TestClient(create_app())

    assert client.get("/health").json() == {"status": "ok"}
    response = client.post("/api/v1/recommendations", json=_valid_payload())

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "recommendation_service_unconfigured",
            "message": "Recommendation service is not configured.",
        }
    }
    assert events == [
        {
            "event": "recommendation.rejected",
            "request_id": response.headers["X-Request-ID"],
            "code": "recommendation_service_unconfigured",
            "stage": "configuration",
        }
    ]


def test_offline_http_pipeline_returns_ranked_deterministic_evidence() -> None:
    response = _configured_client().post("/api/v1/recommendations", json=_valid_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["request"] == _valid_payload()
    assert body["recommendation_count"] == 3
    assert body["has_recommendations"] is True
    assert body["has_narration"] is False
    assert body["narration"] is None
    assert [item["rank"] for item in body["recommendations"]] == [1, 2, 3]
    assert [item["destination"]["name"] for item in body["recommendations"]] == [
        "Sunspire Bay",
        "Mistral Hollow",
        "Frostglass Vale",
    ]
    assert [item["score"] for item in body["recommendations"]] == pytest.approx([1.0, 0.68, 0.0])
    for item in body["recommendations"]:
        assert item["components"][0]["name"] == "seasonal_temperature_comfort"
        assert len(item["evidence"]["attractions"]) == 2
        weather = item["evidence"]["seasonal_weather"]
        assert weather["observation_count"] == 15
        assert weather["historical_years"] == [2020, 2021, 2022, 2023, 2024]
        assert "observations" not in weather
        assert item["evidence"]["temperature_comfort"]["comfort_range"] == {
            "minimum_celsius": 18.0,
            "maximum_celsius": 28.0,
            "tolerance_celsius": 10.0,
        }


def test_preselected_destination_and_preferences_are_preserved() -> None:
    destination = DEFAULT_OFFLINE_DATASET.fixtures[1].destination
    payload = _valid_payload()
    payload["preferences"] = {
        "interests": ["History", "Nature"],
        "preferred_pace": " Relaxed ",
        "preferred_climate": "Warm",
    }
    payload["destination"] = {
        "name": destination.name,
        "country": destination.country,
        "coordinates": {
            "latitude": destination.coordinates.latitude,
            "longitude": destination.coordinates.longitude,
        },
    }

    response = _configured_client().post("/api/v1/recommendations", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["request"] == payload
    assert body["recommendation_count"] == 1
    assert body["recommendations"][0]["destination"] == payload["destination"]


def test_omitted_preferences_become_authoritative_empty_preferences() -> None:
    payload = {"travel_period": _valid_payload()["travel_period"]}

    response = _configured_client().post("/api/v1/recommendations", json=payload)

    assert response.status_code == 200
    assert response.json()["request"]["preferences"] == {
        "interests": None,
        "preferred_pace": None,
        "preferred_climate": None,
    }


def test_empty_recommendation_result_is_a_valid_success() -> None:
    response = _configured_client(_offline_service(empty=True)).post(
        "/api/v1/recommendations", json=_valid_payload()
    )

    assert response.status_code == 200
    assert response.json() | {"request": None} == {
        "request": None,
        "recommendation_count": 0,
        "has_recommendations": False,
        "recommendations": [],
        "has_narration": False,
        "narration": None,
    }


def test_successful_narration_enriches_without_changing_deterministic_result() -> None:
    provider = FakeNarrationProvider("Fixed grounded narration")
    recommendation_service = _offline_service()
    client = _configured_client(
        recommendation_service,
        RecommendationNarrationService(provider),
    )
    deterministic = _configured_client(recommendation_service).post(
        "/api/v1/recommendations", json=_valid_payload()
    )

    response = client.post("/api/v1/recommendations", json=_valid_payload())

    assert response.status_code == 200
    body = response.json()
    baseline = deterministic.json()
    assert body["recommendations"] == baseline["recommendations"]
    assert body["request"] == baseline["request"]
    assert body["has_narration"] is True
    assert body["narration"] == "Fixed grounded narration"
    assert len(provider.prompts) == 1


def test_narration_provider_failure_still_returns_deterministic_success() -> None:
    provider = FakeNarrationProvider(ProviderUnavailableError("private AI failure detail"))
    response = _configured_client(narration_service=RecommendationNarrationService(provider)).post(
        "/api/v1/recommendations", json=_valid_payload()
    )

    assert response.status_code == 200
    assert response.json()["recommendation_count"] == 3
    assert response.json()["has_narration"] is False
    assert response.json()["narration"] is None


@pytest.mark.parametrize(
    ("mutate", "expected_fragment"),
    [
        (lambda payload: payload.update(unknown=True), "Extra inputs are not permitted"),
        (
            lambda payload: payload["travel_period"].update(start_date="not-a-date"),
            "Input should be a valid date",
        ),
        (
            lambda payload: payload["preferences"].update(preferred_pace=3),
            "Input should be a valid string",
        ),
        (
            lambda payload: payload.update(
                destination={
                    "name": "Test",
                    "country": "Fixtureland",
                    "coordinates": {"latitude": True, "longitude": 24.0},
                }
            ),
            "Input should be a valid number",
        ),
    ],
)
def test_structurally_invalid_http_input_uses_fastapi_422(
    mutate: object, expected_fragment: str
) -> None:
    payload = _valid_payload()
    mutate(payload)  # type: ignore[operator]

    response = _configured_client().post("/api/v1/recommendations", json=payload)

    assert response.status_code == 422
    assert expected_fragment in response.text


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("travel_period", "end_date"), "2026-04-09", "end date must not be before start date"),
        (("preferences", "interests"), [], "at least one interest must be provided"),
        (("preferences", "interests"), [""], "interests must not be blank"),
        (("preferences", "interests"), ["Nature", " nature "], "duplicates"),
        (("preferences", "preferred_pace"), " ", "preferred pace must not be blank"),
        (("preferences", "preferred_climate"), "", "preferred climate must not be blank"),
        (("destination", "name"), " ", "destination name must not be blank"),
        (("destination", "country"), "", "destination country must not be blank"),
        (("destination", "coordinates", "latitude"), 91, "latitude must be between"),
        (("destination", "coordinates", "longitude"), -181, "longitude must be between"),
    ],
)
def test_domain_invalid_input_maps_to_safe_422(
    path: tuple[str, ...], value: object, message: str
) -> None:
    payload = _valid_payload()
    if path[0] == "destination":
        payload["destination"] = {
            "name": "Sunspire Bay",
            "country": "Fixtureland",
            "coordinates": {"latitude": 12.0, "longitude": 24.0},
        }
    current = payload
    for part in path[:-1]:
        current = current[part]  # type: ignore[assignment,index]
    current[path[-1]] = value  # type: ignore[index]

    response = _configured_client().post("/api/v1/recommendations", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_recommendation_request"
    assert message in response.json()["detail"]["message"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_coordinate_is_rejected_during_model_validation(value: float) -> None:
    payload = _valid_payload()
    payload["destination"] = {
        "name": "Test",
        "country": "Fixtureland",
        "coordinates": {"latitude": value, "longitude": 24.0},
    }

    with pytest.raises(ValidationError):
        RecommendationRequestBody.model_validate(payload)


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (ProviderAuthenticationError("secret auth detail"), 503, "provider_authentication_failed"),
        (ProviderRateLimitError("secret rate detail"), 503, "provider_rate_limited"),
        (ProviderResponseError("secret payload detail"), 502, "provider_invalid_response"),
        (ProviderUnavailableError("secret outage detail"), 503, "provider_unavailable"),
        (ProviderError("secret future detail"), 502, "provider_error"),
    ],
)
def test_provider_errors_map_to_safe_stable_http_responses(
    error: ProviderError,
    status_code: int,
    code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr(
        recommendation_routes,
        "emit_event",
        lambda event, **fields: events.append({"event": event, **fields}),
    )
    response = _configured_client(_error_service(error)).post(
        "/api/v1/recommendations", json=_valid_payload()
    )

    assert response.status_code == status_code
    body = response.json()
    assert body["detail"]["code"] == code
    assert body["detail"]["message"]
    assert str(error) not in response.text
    assert "Google" not in response.text
    assert "Open-Meteo" not in response.text
    assert "OpenAI" not in response.text
    assert len(events) == 1
    duration_ms = events[0]["duration_ms"]
    assert {key: value for key, value in events[0].items() if key != "duration_ms"} == {
        "event": "recommendation.failed",
        "request_id": response.headers["X-Request-ID"],
        "code": code,
        "stage": "recommendation",
    }
    assert isinstance(duration_ms, (int, float))
    assert duration_ms >= 0
    assert str(error) not in str(events[0])


def test_domain_rejection_emits_only_a_safe_code(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr(
        recommendation_routes,
        "emit_event",
        lambda event, **fields: events.append({"event": event, **fields}),
    )
    payload = _valid_payload()
    payload["travel_period"]["end_date"] = "2026-04-09"  # type: ignore[index]

    response = _configured_client().post("/api/v1/recommendations", json=payload)

    assert response.status_code == 422
    assert events == [
        {
            "event": "recommendation.rejected",
            "request_id": response.headers["X-Request-ID"],
            "code": "invalid_recommendation_request",
            "stage": "validation",
        }
    ]
    assert "2026-04" not in str(events)


def test_unexpected_programming_error_is_not_silently_translated() -> None:
    error = RuntimeError("programming defect")

    with pytest.raises(RuntimeError, match="programming defect"):
        _configured_client(_error_service(error)).post(
            "/api/v1/recommendations", json=_valid_payload()
        )

    response = _configured_client(_error_service(error), raise_server_exceptions=False).post(
        "/api/v1/recommendations", json=_valid_payload()
    )
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


@pytest.mark.parametrize("path", ["/recommendations", "/api/recommendations"])
def test_recommendation_aliases_remain_absent(path: str) -> None:
    assert _configured_client().post(path, json=_valid_payload()).status_code == 404


def test_configured_recommendation_app_also_serves_web_shell() -> None:
    response = _configured_client().get("/")

    assert response.status_code == 200
    assert "Solara" in response.text


def test_recommendation_rate_limit_returns_safe_429_without_calling_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    events: list[dict[str, object]] = []
    service = _offline_service()
    original_recommend = RecommendationService.recommend

    def counted_recommend(self: RecommendationService, request: object) -> object:
        nonlocal calls
        calls += 1
        return original_recommend(self, request)  # type: ignore[arg-type]

    monkeypatch.setattr(RecommendationService, "recommend", counted_recommend)
    monkeypatch.setattr(
        recommendation_routes,
        "emit_event",
        lambda event, **fields: events.append({"event": event, **fields}),
    )
    settings = ApiSettings(
        public_alpha_safeguards=PublicAlphaSafeguardSettings(recommendation_rate_limit=1)
    )
    client = TestClient(create_app(settings, dependencies=ApiDependencies(service)))

    assert client.post("/api/v1/recommendations", json=_valid_payload()).status_code == 200
    rejected = client.post("/api/v1/recommendations", json=_valid_payload())

    assert rejected.status_code == 429
    assert rejected.headers["Retry-After"] == "60"
    assert rejected.json() == {
        "detail": {
            "code": "recommendation_rate_limited",
            "message": (
                "This public preview is receiving too many recommendation requests. "
                "Please try again shortly."
            ),
        }
    }
    assert calls == 1
    assert events[-1] == {
        "event": "recommendation.rejected",
        "request_id": rejected.headers["X-Request-ID"],
        "code": "recommendation_rate_limited",
        "stage": "safeguard",
        "retry_after_seconds": 60,
    }


def test_recommendation_long_budget_has_distinct_safe_response() -> None:
    settings = ApiSettings(
        public_alpha_safeguards=PublicAlphaSafeguardSettings(
            recommendation_rate_limit=10,
            recommendation_budget_limit=1,
        )
    )
    client = TestClient(create_app(settings, dependencies=ApiDependencies(_offline_service())))

    assert client.post("/api/v1/recommendations", json=_valid_payload()).status_code == 200
    rejected = client.post("/api/v1/recommendations", json=_valid_payload())

    assert rejected.status_code == 429
    assert rejected.headers["Retry-After"] == "3600"
    assert rejected.json()["detail"]["code"] == "recommendation_budget_exhausted"
    assert "allowance" in rejected.json()["detail"]["message"]


def test_invalid_and_unconfigured_requests_do_not_consume_recommendation_quota() -> None:
    settings = ApiSettings(
        public_alpha_safeguards=PublicAlphaSafeguardSettings(recommendation_rate_limit=1)
    )
    application = create_app(settings)
    client = TestClient(application)
    invalid = _valid_payload()
    invalid["travel_period"]["end_date"] = "2026-04-09"  # type: ignore[index]

    assert client.post("/api/v1/recommendations", json=_valid_payload()).status_code == 503
    assert client.post("/api/v1/recommendations", json=invalid).status_code == 503
    application.state.api_dependencies = ApiDependencies(_offline_service())
    assert client.post("/api/v1/recommendations", json=invalid).status_code == 422
    assert client.post("/api/v1/recommendations", json=_valid_payload()).status_code == 200
    assert client.post("/api/v1/recommendations", json=_valid_payload()).status_code == 429


def test_provider_attempt_failure_consumes_quota_and_preserves_503_mapping() -> None:
    settings = ApiSettings(
        public_alpha_safeguards=PublicAlphaSafeguardSettings(recommendation_rate_limit=2)
    )
    client = TestClient(
        create_app(
            settings,
            dependencies=ApiDependencies(
                _error_service(ProviderRateLimitError("private provider detail"))
            ),
        )
    )

    first = client.post("/api/v1/recommendations", json=_valid_payload())
    second = client.post("/api/v1/recommendations", json=_valid_payload())
    third = client.post("/api/v1/recommendations", json=_valid_payload())

    assert first.status_code == 503
    assert first.json()["detail"]["code"] == "provider_rate_limited"
    assert "Retry-After" not in first.headers
    assert second.status_code == 503
    assert second.json()["detail"]["code"] == "provider_rate_limited"
    assert third.status_code == 429
    assert third.json()["detail"]["code"] == "recommendation_rate_limited"


def test_capacity_rejection_does_not_call_service_and_slot_releases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = Event()
    release = Event()
    calls = 0
    service = _offline_service()
    original_recommend = RecommendationService.recommend

    def blocking_recommend(self: RecommendationService, request: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            assert release.wait(timeout=5)
        return original_recommend(self, request)  # type: ignore[arg-type]

    monkeypatch.setattr(RecommendationService, "recommend", blocking_recommend)
    settings = ApiSettings(
        public_alpha_safeguards=PublicAlphaSafeguardSettings(
            recommendation_rate_limit=10,
            recommendation_concurrency_limit=1,
        )
    )
    application = create_app(settings, dependencies=ApiDependencies(service))
    first_client = TestClient(application)
    second_client = TestClient(application)
    responses: list[object] = []
    thread = Thread(
        target=lambda: responses.append(
            first_client.post("/api/v1/recommendations", json=_valid_payload())
        )
    )
    thread.start()
    assert started.wait(timeout=5)

    rejected = second_client.post("/api/v1/recommendations", json=_valid_payload())
    assert rejected.status_code == 429
    assert rejected.headers["Retry-After"] == "1"
    assert rejected.json()["detail"]["code"] == "recommendation_capacity_reached"
    assert calls == 1

    release.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert responses[0].status_code == 200  # type: ignore[attr-defined]
    assert second_client.post("/api/v1/recommendations", json=_valid_payload()).status_code == 200
    assert calls == 2


def test_narration_budget_skips_enrichment_then_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    events: list[dict[str, object]] = []
    provider = FakeNarrationProvider("Fixed grounded narration")
    settings = ApiSettings(
        public_alpha_safeguards=PublicAlphaSafeguardSettings(
            recommendation_rate_limit=10,
            narration_budget_limit=1,
            narration_budget_window_seconds=10,
        )
    )
    application = create_app(
        settings,
        dependencies=ApiDependencies(_offline_service(), RecommendationNarrationService(provider)),
    )
    application.state.api_safeguards = ApiSafeguards(
        settings.public_alpha_safeguards, clock=lambda: now[0]
    )
    monkeypatch.setattr(
        recommendation_routes,
        "emit_event",
        lambda event, **fields: events.append({"event": event, **fields}),
    )
    client = TestClient(application)

    first = client.post("/api/v1/recommendations", json=_valid_payload())
    skipped = client.post("/api/v1/recommendations", json=_valid_payload())

    assert first.status_code == skipped.status_code == 200
    assert first.json()["has_narration"] is True
    assert skipped.json()["has_narration"] is False
    assert skipped.json()["narration"] is None
    assert len(provider.prompts) == 1
    assert [event for event in events if event["event"] == "narration.skipped"] == [
        {
            "event": "narration.skipped",
            "request_id": skipped.headers["X-Request-ID"],
            "code": "narration_budget_exhausted",
            "stage": "safeguard",
        }
    ]
    skipped_completed = [
        event
        for event in events
        if event["event"] == "recommendation.completed"
        and event["request_id"] == skipped.headers["X-Request-ID"]
    ][0]
    assert skipped_completed["narration_attempted"] is False
    assert skipped_completed["narration_duration_ms"] is None

    now[0] = 10.0
    renewed = client.post("/api/v1/recommendations", json=_valid_payload())
    assert renewed.status_code == 200
    assert renewed.json()["has_narration"] is True
    assert len(provider.prompts) == 2
