"""Architectural contracts for the Render MVP1 Blueprint."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT = ROOT / "render.yaml"

SERVICE_VALUES = {
    "type": "web",
    "name": "solara-travel-mvp1",
    "runtime": "docker",
    "plan": "free",
    "region": "singapore",
    "branch": "main",
    "numInstances": "1",
    "dockerfilePath": "./Dockerfile",
    "healthCheckPath": "/health",
    "autoDeployTrigger": "checksPass",
    "renderSubdomainPolicy": "enabled",
}

SECRET_VARIABLES = {
    "SOLARA_GOOGLE_PLACES_API_KEY",
    "SOLARA_OPENAI_API_KEY",
}

POLICY_VALUES = {
    "SOLARA_OPENAI_MODEL": "gpt-5.6-luna",
    "SOLARA_DOCS_ENABLED": "false",
    "SOLARA_GOOGLE_PLACES_TIMEOUT_SECONDS": "10",
    "SOLARA_GOOGLE_PLACES_DESTINATION_PAGE_SIZE": "10",
    "SOLARA_GOOGLE_PLACES_ATTRACTION_MAX_RESULTS": "20",
    "SOLARA_GOOGLE_PLACES_ATTRACTION_RADIUS_METERS": "30000",
    "SOLARA_OPEN_METEO_TIMEOUT_SECONDS": "10",
    "SOLARA_OPENAI_TIMEOUT_SECONDS": "30",
    "SOLARA_OPENAI_MAX_OUTPUT_TOKENS": "1200",
    "SOLARA_HISTORICAL_START_DATE": "2020-01-01",
    "SOLARA_HISTORICAL_END_DATE": "2024-12-31",
    "SOLARA_COMFORT_MIN_CELSIUS": "18",
    "SOLARA_COMFORT_MAX_CELSIUS": "28",
    "SOLARA_COMFORT_TOLERANCE_CELSIUS": "10",
    "SOLARA_SEASONAL_WEIGHT": "1.0",
    "SOLARA_RECOMMENDATION_RATE_LIMIT": "12",
    "SOLARA_RECOMMENDATION_RATE_WINDOW_SECONDS": "60",
    "SOLARA_RECOMMENDATION_BUDGET_LIMIT": "60",
    "SOLARA_RECOMMENDATION_BUDGET_WINDOW_SECONDS": "3600",
    "SOLARA_RECOMMENDATION_CONCURRENCY_LIMIT": "2",
    "SOLARA_FEEDBACK_RATE_LIMIT": "30",
    "SOLARA_FEEDBACK_RATE_WINDOW_SECONDS": "60",
    "SOLARA_NARRATION_BUDGET_LIMIT": "30",
    "SOLARA_NARRATION_BUDGET_WINDOW_SECONDS": "3600",
}


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _service_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        if raw_line.strip() == "envVars:":
            break
        match = re.fullmatch(
            r"\s+(?:-\s+)?([A-Za-z][A-Za-z0-9]*):\s*(\S.*?)\s*",
            raw_line,
        )
        if match is not None:
            fields[match.group(1)] = _scalar(match.group(2))
    return fields


def _environment_variables(text: str) -> dict[str, dict[str, str]]:
    variables: dict[str, dict[str, str]] = {}
    current: str | None = None
    inside_environment = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped == "envVars:":
            inside_environment = True
            continue
        if not inside_environment:
            continue

        key_match = re.fullmatch(r"-\s+key:\s*(\S+)", stripped)
        if key_match is not None:
            current = _scalar(key_match.group(1))
            assert current not in variables
            variables[current] = {}
            continue

        property_match = re.fullmatch(r"(value|sync):\s*(\S.*?)\s*", stripped)
        if property_match is not None and current is not None:
            variables[current][property_match.group(1)] = _scalar(property_match.group(2))

    return variables


def test_render_blueprint_defines_one_docker_web_service() -> None:
    assert BLUEPRINT.is_file()
    text = BLUEPRINT.read_text(encoding="utf-8")

    service_types = re.findall(
        r"^\s*-\s+type:\s*([A-Za-z][A-Za-z0-9]*)\s*$",
        text,
        flags=re.MULTILINE,
    )
    assert service_types == ["web"]
    assert _service_fields(text) == SERVICE_VALUES


def test_render_blueprint_uses_placeholders_and_pins_hosted_policy() -> None:
    variables = _environment_variables(BLUEPRINT.read_text(encoding="utf-8"))

    assert set(variables) == SECRET_VARIABLES | set(POLICY_VALUES)
    for name in SECRET_VARIABLES:
        assert variables[name] == {"sync": "false"}
    for name, value in POLICY_VALUES.items():
        assert variables[name] == {"value": value}


def test_render_blueprint_keeps_the_single_service_security_boundary() -> None:
    text = BLUEPRINT.read_text(encoding="utf-8")
    lowered = text.lower()
    forbidden_fields = {
        "autoscaling",
        "databases",
        "dockercommand",
        "domains",
        "envvargroups",
        "keyvalue",
        "maxinstances",
        "mininstances",
        "previews",
        "render_api",
        "scaling",
        "workers",
    }

    declared_fields = {
        match.group(1).lower()
        for match in re.finditer(r"^\s*(?:-\s+)?([A-Za-z][A-Za-z0-9_]*):", text, re.MULTILINE)
    }
    assert declared_fields.isdisjoint(forbidden_fields)
    extra_service = re.search(
        r"^\s*-\s+type:\s*(?:worker|cron|pserv|redis|keyvalue)\s*$",
        text,
        re.MULTILINE,
    )
    assert extra_service is None
    assert "onrender.com" not in lowered
    assert "render_api" not in lowered
    assert "bearer " not in lowered
    assert "private key" not in lowered
