"""Structured traveller-facing Wayfinder narrative values."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

_FORBIDDEN_LANGUAGE = re.compile(
    r"\b(?:llm|model|weighted contribution|configured comfort|raw score|"
    r"temperature threshold|visa|entry rules?|crime|safety guarantee|"
    r"medical advice|opening hours?|flight availability|booking availability|"
    r"weather forecast)\b",
    re.IGNORECASE,
)


def _plain_text(value: object, field_name: str, *, maximum_words: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    if len(normalized.split()) > maximum_words:
        raise ValueError(f"{field_name} is too long")
    if any(marker in normalized for marker in ("<", ">", "```", "**", "__")):
        raise ValueError(f"{field_name} must be plain text")
    if _FORBIDDEN_LANGUAGE.search(normalized):
        raise ValueError(f"{field_name} contains unsupported claims or technical language")
    return normalized


@dataclass(frozen=True, slots=True)
class WayfinderDestinationNote:
    """One bounded, evidence-grounded destination story."""

    destination: str
    why_it_fits: str
    seasonal_feel: str
    good_to_know: str
    signature_highlights: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "destination",
            _plain_text(self.destination, "destination", maximum_words=20),
        )
        object.__setattr__(
            self,
            "why_it_fits",
            _plain_text(self.why_it_fits, "why_it_fits", maximum_words=110),
        )
        object.__setattr__(
            self,
            "seasonal_feel",
            _plain_text(self.seasonal_feel, "seasonal_feel", maximum_words=55),
        )
        object.__setattr__(
            self,
            "good_to_know",
            _plain_text(self.good_to_know, "good_to_know", maximum_words=55),
        )
        if not isinstance(self.signature_highlights, tuple):
            raise TypeError("signature_highlights must be a tuple")
        if len(self.signature_highlights) > 4:
            raise ValueError("signature_highlights must contain at most four values")
        highlights = tuple(
            _plain_text(value, "signature highlight", maximum_words=12)
            for value in self.signature_highlights
        )
        if len({value.casefold() for value in highlights}) != len(highlights):
            raise ValueError("signature_highlights must be unique")
        object.__setattr__(self, "signature_highlights", highlights)


@dataclass(frozen=True, slots=True)
class WayfinderNarrative:
    """One opening and authoritative-rank-aligned destination notes."""

    opening: str
    destination_notes: tuple[WayfinderDestinationNote, ...]
    comparison_note: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "opening", _plain_text(self.opening, "opening", maximum_words=90))
        if not isinstance(self.destination_notes, tuple):
            raise TypeError("destination_notes must be a tuple")
        if not self.destination_notes:
            raise ValueError("destination_notes must not be empty")
        if not all(isinstance(note, WayfinderDestinationNote) for note in self.destination_notes):
            raise TypeError("every destination note must be a WayfinderDestinationNote")
        names = [note.destination.casefold() for note in self.destination_notes]
        if len(set(names)) != len(names):
            raise ValueError("destination notes must be unique")
        if self.comparison_note is not None:
            object.__setattr__(
                self,
                "comparison_note",
                _plain_text(self.comparison_note, "comparison_note", maximum_words=120),
            )

    def as_plain_text(self) -> str:
        """Return a compatibility narration without changing note order."""

        paragraphs = [self.opening]
        paragraphs.extend(
            f"{note.destination}: {note.why_it_fits} {note.seasonal_feel} {note.good_to_know}"
            for note in self.destination_notes
        )
        if self.comparison_note is not None:
            paragraphs.append(self.comparison_note)
        return "\n\n".join(paragraphs)


def parse_wayfinder_narrative(
    text: str,
    authoritative_destinations: tuple[str, ...],
) -> WayfinderNarrative:
    """Parse strict provider JSON and restore authoritative destination order."""

    if not isinstance(text, str):
        raise TypeError("Wayfinder output must be a string")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Wayfinder output must be valid JSON") from exc
    if not isinstance(payload, Mapping) or set(payload) != {
        "opening",
        "destination_notes",
        "comparison_note",
    }:
        raise ValueError("Wayfinder output does not match its schema")
    raw_notes = payload["destination_notes"]
    if not isinstance(raw_notes, list):
        raise ValueError("Wayfinder destination notes must be a list")
    notes: list[WayfinderDestinationNote] = []
    for raw_note in raw_notes:
        if not isinstance(raw_note, Mapping) or set(raw_note) != {
            "destination",
            "why_it_fits",
            "seasonal_feel",
            "good_to_know",
            "signature_highlights",
        }:
            raise ValueError("Wayfinder destination note does not match its schema")
        highlights = raw_note["signature_highlights"]
        if not isinstance(highlights, list):
            raise ValueError("signature_highlights must be a list")
        notes.append(
            WayfinderDestinationNote(
                destination=raw_note["destination"],  # type: ignore[arg-type]
                why_it_fits=raw_note["why_it_fits"],  # type: ignore[arg-type]
                seasonal_feel=raw_note["seasonal_feel"],  # type: ignore[arg-type]
                good_to_know=raw_note["good_to_know"],  # type: ignore[arg-type]
                signature_highlights=tuple(highlights),
            )
        )
    by_name = {note.destination.casefold(): note for note in notes}
    authoritative_keys = tuple(name.casefold() for name in authoritative_destinations)
    if len(by_name) != len(notes) or set(by_name) != set(authoritative_keys):
        raise ValueError("Wayfinder destinations must match deterministic recommendations")
    comparison_note = payload["comparison_note"]
    if comparison_note is not None and not isinstance(comparison_note, str):
        raise ValueError("comparison_note must be a string or null")
    return WayfinderNarrative(
        opening=payload["opening"],  # type: ignore[arg-type]
        destination_notes=tuple(by_name[key] for key in authoritative_keys),
        comparison_note=comparison_note,
    )
