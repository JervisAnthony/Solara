"""Static contracts for portable, secret-free deployment configuration."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VARIABLES = {
    "SOLARA_GOOGLE_PLACES_API_KEY",
    "SOLARA_OPENAI_API_KEY",
    "SOLARA_OPENAI_MODEL",
    "SOLARA_DOCS_ENABLED",
    "SOLARA_GOOGLE_PLACES_TIMEOUT_SECONDS",
    "SOLARA_GOOGLE_PLACES_DESTINATION_PAGE_SIZE",
    "SOLARA_GOOGLE_PLACES_ATTRACTION_MAX_RESULTS",
    "SOLARA_GOOGLE_PLACES_ATTRACTION_RADIUS_METERS",
    "SOLARA_OPEN_METEO_TIMEOUT_SECONDS",
    "SOLARA_OPENAI_TIMEOUT_SECONDS",
    "SOLARA_OPENAI_MAX_OUTPUT_TOKENS",
    "SOLARA_HISTORICAL_START_DATE",
    "SOLARA_HISTORICAL_END_DATE",
    "SOLARA_COMFORT_MIN_CELSIUS",
    "SOLARA_COMFORT_MAX_CELSIUS",
    "SOLARA_COMFORT_TOLERANCE_CELSIUS",
    "SOLARA_SEASONAL_WEIGHT",
    "SOLARA_RECOMMENDATION_RATE_LIMIT",
    "SOLARA_RECOMMENDATION_RATE_WINDOW_SECONDS",
    "SOLARA_RECOMMENDATION_BUDGET_LIMIT",
    "SOLARA_RECOMMENDATION_BUDGET_WINDOW_SECONDS",
    "SOLARA_RECOMMENDATION_CONCURRENCY_LIMIT",
    "SOLARA_FEEDBACK_RATE_LIMIT",
    "SOLARA_FEEDBACK_RATE_WINDOW_SECONDS",
    "SOLARA_NARRATION_BUDGET_LIMIT",
    "SOLARA_NARRATION_BUDGET_WINDOW_SECONDS",
    "PORT",
}


def test_environment_template_lists_every_supported_variable_with_blank_secrets() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    names = {
        line.split("=", 1)[0] for line in text.splitlines() if line and not line.startswith("#")
    }

    assert names == VARIABLES
    assert "SOLARA_GOOGLE_PLACES_API_KEY=\n" in text
    assert "SOLARA_OPENAI_API_KEY=\n" in text
    assert "SOLARA_OPENAI_MODEL=\n" in text


def test_container_runs_non_root_single_worker_server_and_healthcheck() -> None:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.13-slim" in text
    assert "USER solara" in text
    assert "EXPOSE 8000" in text
    assert "HEALTHCHECK" in text
    assert "/health" in text
    assert "solara_travel.presentation.api.server" in text
    assert "SOLARA_GOOGLE_PLACES_API_KEY" not in text
    assert "SOLARA_OPENAI_API_KEY" not in text


def test_dockerignore_protects_local_state_without_excluding_branding() -> None:
    text = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    for excluded in (".git", ".venv", ".pytest_cache", ".coverage", ".env", "dist"):
        assert excluded in text
    assert "branding" not in text
