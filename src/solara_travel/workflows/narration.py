"""Composition for OpenAI-backed grounded recommendation narration."""

from solara_travel.application.narration import RecommendationNarrationService
from solara_travel.infrastructure.http import JsonHttpTransport, UrllibJsonHttpTransport
from solara_travel.infrastructure.narration.openai import OpenAIResponsesNarrationProvider


def build_openai_recommendation_narration_service(
    *,
    api_key: str,
    model: str,
    timeout_seconds: float = 30.0,
    max_output_tokens: int = 1200,
    transport: JsonHttpTransport | None = None,
) -> RecommendationNarrationService:
    """Compose grounded narration with explicit OpenAI configuration."""

    if transport is None:
        transport = UrllibJsonHttpTransport()

    return RecommendationNarrationService(
        provider=OpenAIResponsesNarrationProvider(
            api_key=api_key,
            model=model,
            transport=transport,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )
    )
