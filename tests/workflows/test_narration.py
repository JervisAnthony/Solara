"""End-to-end tests for explicit grounded narration composition."""

import json
from datetime import date

from solara_travel.application import RecommendationNarrationService
from solara_travel.domain import RecommendationRequest, TemperatureComfortRange, TravelPeriod
from solara_travel.infrastructure.http import JsonHttpResponse, UrllibJsonHttpTransport
from solara_travel.infrastructure.narration import OpenAIResponsesNarrationProvider
from solara_travel.workflows import (
    build_offline_recommendation_service,
    build_openai_recommendation_narration_service,
)


class FalseyFakeTransport:
    """A falsey custom transport that records requests without network access."""

    def __init__(self, outcome: JsonHttpResponse | Exception) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, object]] = []

    def __bool__(self) -> bool:
        return False

    def post_json(self, **kwargs: object) -> JsonHttpResponse:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _completed_response(text: str) -> JsonHttpResponse:
    return JsonHttpResponse(
        status_code=200,
        payload={
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": text}],
                }
            ],
        },
    )


def _recommendation_result():
    service = build_offline_recommendation_service(
        comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0)
    )
    return service.recommend(
        RecommendationRequest(TravelPeriod(date(2026, 4, 10), date(2026, 4, 12)))
    )


def _wayfinder_json() -> str:
    names = ("Sunspire Bay", "Mistral Hollow", "Frostglass Vale")
    return json.dumps(
        {
            "opening": "A grounded seasonal shortlist.",
            "destination_notes": [
                {
                    "destination": name,
                    "why_it_fits": f"{name} is worth considering for these dates.",
                    "seasonal_feel": "Historically, this is a distinct seasonal window.",
                    "good_to_know": "Use this as historical context, not a forecast.",
                    "signature_highlights": [],
                }
                for name in names
            ],
            "comparison_note": "Compare all three before choosing.",
        }
    )


def test_factory_uses_supplied_transport_exactly_and_explicit_configuration() -> None:
    transport = FalseyFakeTransport(_completed_response("Narration"))

    service = build_openai_recommendation_narration_service(
        api_key="fake-openai-key-for-tests",
        model="caller-model",
        timeout_seconds=8.0,
        max_output_tokens=456,
        transport=transport,
    )

    assert isinstance(service, RecommendationNarrationService)
    assert isinstance(service.provider, OpenAIResponsesNarrationProvider)
    assert service.provider.transport is transport
    assert service.provider.model == "caller-model"
    assert service.provider.timeout_seconds == 8.0
    assert service.provider.max_output_tokens == 456


def test_factory_builds_default_standard_library_transport() -> None:
    service = build_openai_recommendation_narration_service(
        api_key="fake-openai-key-for-tests",
        model="caller-model",
    )

    assert isinstance(service.provider.transport, UrllibJsonHttpTransport)


def test_real_offline_recommendations_are_narrated_without_mutation() -> None:
    result = _recommendation_result()
    transport = FalseyFakeTransport(_completed_response(_wayfinder_json()))
    service = build_openai_recommendation_narration_service(
        api_key="fake-openai-key-for-tests",
        model="caller-model",
        transport=transport,
    )

    narrated = service.narrate(result)

    assert narrated.recommendation_result is result
    assert narrated.recommendation_result.recommendations == result.recommendations
    assert narrated.narration is not None
    assert narrated.wayfinder is not None
    assert narrated.wayfinder.opening == "A grounded seasonal shortlist."
    assert narrated.has_narration
    assert [item.destination.name for item in result.recommendations] == [
        "Sunspire Bay",
        "Mistral Hollow",
        "Frostglass Vale",
    ]
    grounding = json.loads(transport.calls[0]["payload"]["input"])  # type: ignore[index]
    assert [item["rank"] for item in grounding["recommendations"]] == [1, 2, 3]


def test_real_offline_result_survives_openai_transport_failure() -> None:
    result = _recommendation_result()
    service = build_openai_recommendation_narration_service(
        api_key="fake-openai-key-for-tests",
        model="caller-model",
        transport=FalseyFakeTransport(TimeoutError("simulated outage")),
    )

    narrated = service.narrate(result)

    assert narrated.recommendation_result is result
    assert narrated.recommendation_result.recommendations == result.recommendations
    assert narrated.narration is None
    assert not narrated.has_narration


def test_public_narration_workflow_import_is_available() -> None:
    assert callable(build_openai_recommendation_narration_service)
