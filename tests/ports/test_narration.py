"""Tests for provider-independent narration contracts."""

from dataclasses import FrozenInstanceError

import pytest

from solara_travel.ports import NarrationPrompt, NarrationProvider


class FakeNarrationProvider:
    """Minimal structural implementation of the narration protocol."""

    def generate(self, prompt: NarrationPrompt) -> str:
        return prompt.input_text


def test_narration_prompt_preserves_valid_text_exactly() -> None:
    prompt = NarrationPrompt("  trusted instructions  ", "  grounding data  ")

    assert prompt.instructions == "  trusted instructions  "
    assert prompt.input_text == "  grounding data  "


@pytest.mark.parametrize("field", ["instructions", "input_text"])
def test_narration_prompt_requires_string_fields(field: str) -> None:
    values: dict[str, object] = {
        "instructions": "Explain the result",
        "input_text": "{}",
    }
    values[field] = None

    with pytest.raises(TypeError, match=f"{field} must be a string"):
        NarrationPrompt(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["instructions", "input_text"])
@pytest.mark.parametrize("value", ["", " ", "\t\n"])
def test_narration_prompt_rejects_blank_fields(field: str, value: str) -> None:
    values = {
        "instructions": "Explain the result",
        "input_text": "{}",
    }
    values[field] = value

    with pytest.raises(ValueError, match=f"{field} must not be blank"):
        NarrationPrompt(**values)


def test_narration_prompt_is_frozen() -> None:
    prompt = NarrationPrompt("Explain", "{}")

    with pytest.raises(FrozenInstanceError):
        prompt.input_text = "changed"  # type: ignore[misc]


def test_narration_provider_is_runtime_checkable() -> None:
    assert isinstance(FakeNarrationProvider(), NarrationProvider)
