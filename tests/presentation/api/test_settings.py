"""Tests for immutable FastAPI presentation settings."""

from dataclasses import FrozenInstanceError

import pytest

from solara_travel.presentation.api import ApiSettings


def test_api_settings_enable_docs_by_default() -> None:
    settings = ApiSettings()

    assert settings.docs_enabled is True


@pytest.mark.parametrize("docs_enabled", [True, False])
def test_api_settings_accept_explicit_booleans(docs_enabled: bool) -> None:
    settings = ApiSettings(docs_enabled=docs_enabled)

    assert settings.docs_enabled is docs_enabled


@pytest.mark.parametrize("docs_enabled", [1, 0, "true", None])
def test_api_settings_reject_non_booleans(docs_enabled: object) -> None:
    with pytest.raises(TypeError, match="docs_enabled must be a bool"):
        ApiSettings(docs_enabled=docs_enabled)  # type: ignore[arg-type]


def test_api_settings_are_frozen() -> None:
    settings = ApiSettings()

    with pytest.raises(FrozenInstanceError):
        settings.docs_enabled = False  # type: ignore[misc]
