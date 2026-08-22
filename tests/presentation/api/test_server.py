"""Tests for the privacy-conscious Uvicorn deployment runner."""

import runpy
import sys

import pytest

from solara_travel.config import DeploymentConfigurationError
from solara_travel.presentation.api import server


def test_port_defaults_and_accepts_trimmed_valid_value() -> None:
    assert server.load_port({}) == 8000
    assert server.load_port({"PORT": " 4321 "}) == 4321


@pytest.mark.parametrize("value", [None, "", "abc", "0", "65536"])
def test_port_rejects_invalid_values(value: object) -> None:
    with pytest.raises(DeploymentConfigurationError, match="PORT"):
        server.load_port({"PORT": value})  # type: ignore[dict-item]


def test_omitted_port_mapping_reads_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "9876")

    assert server.load_port() == 9876


def test_main_runs_exactly_one_privacy_safe_factory_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, dict[str, object]]] = []
    monkeypatch.setenv("PORT", "8123")
    monkeypatch.setattr(
        server.uvicorn,
        "run",
        lambda target, **kwargs: calls.append((target, kwargs)),
    )

    server.main()

    assert calls == [
        (
            "solara_travel.presentation.api.deployment:create_deployment_app",
            {
                "host": "0.0.0.0",
                "port": 8123,
                "workers": 1,
                "factory": True,
                "proxy_headers": False,
                "access_log": False,
                "server_header": False,
            },
        )
    ]


def test_module_execution_invokes_main_without_starting_a_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(server.uvicorn, "run", lambda *args, **kwargs: calls.append(args))
    monkeypatch.delitem(sys.modules, "solara_travel.presentation.api.server")

    runpy.run_module("solara_travel.presentation.api.server", run_name="__main__")

    assert calls == [("solara_travel.presentation.api.deployment:create_deployment_app",)]
