"""Provider-independent contracts for grounded recommendation narration."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class NarrationPrompt:
    """Trusted narration instructions paired with untrusted grounding data."""

    instructions: str
    input_text: str

    def __post_init__(self) -> None:
        """Validate prompt fields without rewriting caller text."""

        if not isinstance(self.instructions, str):
            raise TypeError("instructions must be a string")

        if not self.instructions.strip():
            raise ValueError("instructions must not be blank")

        if not isinstance(self.input_text, str):
            raise TypeError("input_text must be a string")

        if not self.input_text.strip():
            raise ValueError("input_text must not be blank")


@runtime_checkable
class NarrationProvider(Protocol):
    """Contract for generating prose from a grounded narration prompt."""

    def generate(self, prompt: NarrationPrompt) -> str:
        """Generate traveller-friendly prose from trusted instructions and grounding."""

        ...
