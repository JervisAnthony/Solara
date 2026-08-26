"""OpenAI Responses API adapter for grounded recommendation narration."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real

from solara_travel.infrastructure.http import JsonHttpDecodeError, JsonHttpTransport
from solara_travel.ports.errors import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.ports.narration import NarrationPrompt

_RESPONSES_URL = "https://api.openai.com/v1/responses"


@dataclass(frozen=True, slots=True)
class OpenAIResponsesNarrationProvider:
    """Generate grounded prose through OpenAI's stateless Responses API."""

    api_key: str = field(repr=False)
    model: str
    transport: JsonHttpTransport
    timeout_seconds: float = 30.0
    max_output_tokens: int = 1200

    def __post_init__(self) -> None:
        """Validate explicit caller-supplied provider configuration."""

        if not isinstance(self.api_key, str):
            raise TypeError("api_key must be a string")
        if not self.api_key.strip():
            raise ValueError("api_key must not be blank")

        if not isinstance(self.model, str):
            raise TypeError("model must be a string")
        if not self.model.strip():
            raise ValueError("model must not be blank")

        if not isinstance(self.timeout_seconds, Real) or isinstance(self.timeout_seconds, bool):
            raise TypeError("timeout_seconds must be a real number")
        if not isfinite(self.timeout_seconds):
            raise ValueError("timeout_seconds must be finite")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        if not isinstance(self.max_output_tokens, int) or isinstance(self.max_output_tokens, bool):
            raise TypeError("max_output_tokens must be an integer")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be greater than zero")

    def generate(self, prompt: NarrationPrompt) -> str:
        """Generate and normalize one completed grounded narration."""

        if not isinstance(prompt, NarrationPrompt):
            raise TypeError("prompt must be NarrationPrompt")

        try:
            response = self.transport.post_json(
                url=_RESPONSES_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                payload={
                    "model": self.model,
                    "instructions": prompt.instructions,
                    "input": prompt.input_text,
                    "max_output_tokens": self.max_output_tokens,
                    "store": False,
                },
                timeout_seconds=self.timeout_seconds,
            )
        except JsonHttpDecodeError as exc:
            raise ProviderResponseError("OpenAI returned invalid JSON") from exc
        except Exception as exc:
            raise ProviderUnavailableError("OpenAI narration request failed") from exc

        status_code = response.status_code
        if 200 <= status_code < 300:
            return _normalize_completed_narration(response.payload)
        if status_code in {401, 403}:
            raise ProviderAuthenticationError("OpenAI authentication failed")
        if status_code == 429:
            raise ProviderRateLimitError("OpenAI rate limit exceeded")
        if 400 <= status_code < 500:
            raise ProviderResponseError("OpenAI rejected the narration request")
        if 500 <= status_code < 600:
            raise ProviderUnavailableError("OpenAI narration service unavailable")
        raise ProviderResponseError("OpenAI returned an unexpected HTTP status")


def _normalize_completed_narration(payload: object) -> str:
    """Collect all usable output-text fragments from a completed response."""

    if not isinstance(payload, Mapping) or payload.get("status") != "completed":
        raise ProviderResponseError("OpenAI did not return usable completed narration")

    output = payload.get("output")
    if not isinstance(output, list):
        raise ProviderResponseError("OpenAI did not return usable completed narration")

    fragments: list[str] = []
    for item in output:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, Mapping) or part.get("type") != "output_text":
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                fragments.append(text)

    narration = "\n".join(fragments).strip()
    if not narration:
        raise ProviderResponseError("OpenAI did not return usable completed narration")
    return narration
