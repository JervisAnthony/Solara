"""Tests for OpenAI Responses API narration infrastructure."""

from dataclasses import FrozenInstanceError

import pytest

from solara_travel.infrastructure.http import JsonHttpDecodeError, JsonHttpResponse
from solara_travel.infrastructure.narration import OpenAIResponsesNarrationProvider
from solara_travel.ports import NarrationPrompt
from solara_travel.ports.errors import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)


class FakeTransport:
    """Record one request and return or raise a configured outcome."""

    def __init__(self, outcome: JsonHttpResponse | Exception) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, object]] = []

    def post_json(self, **kwargs: object) -> JsonHttpResponse:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def completed_response(*texts: object) -> JsonHttpResponse:
    """Build a completed response containing the supplied content fragments."""

    return JsonHttpResponse(
        status_code=200,
        payload={
            "status": "completed",
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": text} for text in texts],
                },
            ],
        },
    )


def make_provider(
    outcome: JsonHttpResponse | Exception | None = None,
    **overrides: object,
) -> OpenAIResponsesNarrationProvider:
    """Build a provider with explicitly fake credentials and transport."""

    values: dict[str, object] = {
        "api_key": "fake-openai-key-for-tests",
        "model": "test-model",
        "transport": FakeTransport(outcome or completed_response("Narration")),
    }
    values.update(overrides)
    return OpenAIResponsesNarrationProvider(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "error", "message"),
    [
        ("api_key", None, TypeError, "api_key must be a string"),
        ("api_key", "  ", ValueError, "api_key must not be blank"),
        ("model", None, TypeError, "model must be a string"),
        ("model", "\t", ValueError, "model must not be blank"),
        ("timeout_seconds", True, TypeError, "timeout_seconds must be a real number"),
        ("timeout_seconds", "30", TypeError, "timeout_seconds must be a real number"),
        ("timeout_seconds", float("inf"), ValueError, "timeout_seconds must be finite"),
        ("timeout_seconds", 0, ValueError, "timeout_seconds must be greater than zero"),
        ("max_output_tokens", True, TypeError, "max_output_tokens must be an integer"),
        ("max_output_tokens", 1.5, TypeError, "max_output_tokens must be an integer"),
        ("max_output_tokens", 0, ValueError, "max_output_tokens must be greater than zero"),
    ],
)
def test_provider_validates_configuration(
    field: str,
    value: object,
    error: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error, match=message):
        make_provider(**{field: value})


def test_provider_is_immutable_and_hides_api_key_from_repr() -> None:
    provider = make_provider(timeout_seconds=12.5, max_output_tokens=800)

    assert provider.timeout_seconds == 12.5
    assert provider.max_output_tokens == 800
    assert "fake-openai-key-for-tests" not in repr(provider)
    with pytest.raises(FrozenInstanceError):
        provider.model = "different"  # type: ignore[misc]


def test_generate_sends_exact_stateless_responses_request() -> None:
    transport = FakeTransport(completed_response("  First", "second  "))
    provider = make_provider(
        transport=transport,
        model="caller-model",
        timeout_seconds=7.5,
        max_output_tokens=321,
    )
    prompt = NarrationPrompt(
        instructions="Trusted instructions",
        input_text='{"grounded":true}',
    )

    assert provider.generate(prompt) == "First\nsecond"
    assert transport.calls == [
        {
            "url": "https://api.openai.com/v1/responses",
            "headers": {
                "Authorization": "Bearer fake-openai-key-for-tests",
                "Content-Type": "application/json",
            },
            "payload": {
                "model": "caller-model",
                "instructions": "Trusted instructions",
                "input": '{"grounded":true}',
                "max_output_tokens": 321,
                "store": False,
            },
            "timeout_seconds": 7.5,
        }
    ]


def test_generate_requires_narration_prompt() -> None:
    with pytest.raises(TypeError, match="prompt must be NarrationPrompt"):
        make_provider().generate("prompt")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("status_code", "error"),
    [
        (401, ProviderAuthenticationError),
        (403, ProviderAuthenticationError),
        (429, ProviderRateLimitError),
        (400, ProviderResponseError),
        (599, ProviderUnavailableError),
        (199, ProviderResponseError),
    ],
)
def test_generate_maps_http_failures(
    status_code: int,
    error: type[Exception],
) -> None:
    response = JsonHttpResponse(status_code=status_code, payload={})

    with pytest.raises(error):
        make_provider(response).generate(NarrationPrompt("instructions", "input"))


def test_generate_maps_invalid_json_with_chaining() -> None:
    cause = JsonHttpDecodeError("invalid")

    with pytest.raises(ProviderResponseError) as raised:
        make_provider(cause).generate(NarrationPrompt("instructions", "input"))

    assert raised.value.__cause__ is cause


def test_generate_maps_transport_failure_with_chaining() -> None:
    cause = TimeoutError("offline")

    with pytest.raises(ProviderUnavailableError) as raised:
        make_provider(cause).generate(NarrationPrompt("instructions", "input"))

    assert raised.value.__cause__ is cause
    assert "fake-openai-key-for-tests" not in str(raised.value)


def test_generate_collects_text_across_all_messages_in_order() -> None:
    response = JsonHttpResponse(
        status_code=201,
        payload={
            "status": "completed",
            "output": [
                {"type": "reasoning", "content": "ignored"},
                {
                    "type": "message",
                    "content": [
                        {"type": "refusal", "refusal": "ignored"},
                        {"type": "output_text", "text": "One"},
                        "malformed",
                    ],
                },
                {"type": "message", "content": "malformed"},
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": 2},
                        {"type": "output_text", "text": "  "},
                        {"type": "output_text", "text": "Two"},
                    ],
                },
                "malformed",
            ],
        },
    )

    result = make_provider(response).generate(NarrationPrompt("instructions", "input"))

    assert result == "One\nTwo"


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"status": "incomplete", "output": []},
        {"status": "failed", "output": []},
        {"status": "completed"},
        {"status": "completed", "output": "not-a-list"},
        {"status": "completed", "output": []},
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "refusal", "refusal": "No"}],
                }
            ],
        },
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "  "}],
                }
            ],
        },
    ],
)
def test_generate_rejects_malformed_incomplete_or_textless_payloads(payload: object) -> None:
    response = JsonHttpResponse(status_code=200, payload=payload)

    with pytest.raises(ProviderResponseError, match="usable completed narration"):
        make_provider(response).generate(NarrationPrompt("instructions", "input"))
