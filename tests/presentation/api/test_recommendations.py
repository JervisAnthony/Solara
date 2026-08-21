"""HTTP tests for the versioned recommendation API."""

from datetime import date

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
from solara_travel.presentation.api import ApiDependencies, create_app
from solara_travel.presentation.api.recommendation_schemas import RecommendationRequestBody
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


def test_default_app_is_healthy_but_recommendation_service_is_unconfigured() -> None:
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
    error: ProviderError, status_code: int, code: str
) -> None:
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
