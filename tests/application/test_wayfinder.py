"""Tests for strict structured Wayfinder values and rank authority."""

import json
from dataclasses import FrozenInstanceError

import pytest

from solara_travel.application import (
    WayfinderDestinationNote,
    WayfinderNarrative,
    parse_wayfinder_narrative,
)


def _note(name: str = "Budapest") -> WayfinderDestinationNote:
    return WayfinderDestinationNote(
        name,
        "A concise, grounded destination story.",
        "Around this time of year, the city tends to feel mild and easy to explore.",
        "Buda Castle gives the validated places list a strong starting point.",
        ("Buda Castle",),
    )


def _payload(*names: str) -> str:
    return json.dumps(
        {
            "opening": "A warm, grounded opening.",
            "destination_notes": [
                {
                    "destination": name,
                    "why_it_fits": f"{name} offers a grounded option for these dates.",
                    "seasonal_feel": "Around this time of year, the period tends to feel mild.",
                    "good_to_know": "Validated landmarks offer useful anchors for wandering.",
                    "signature_highlights": [f"{name} landmark"],
                }
                for name in names
            ],
            "comparison_note": "Compare the options carefully." if len(names) > 1 else None,
        }
    )


def test_wayfinder_values_normalize_and_render_compatibility_text() -> None:
    note = _note()
    narrative = WayfinderNarrative("  A grounded opening.  ", (note,), None)

    assert narrative.opening == "A grounded opening."
    assert narrative.as_plain_text().startswith("A grounded opening.\n\nBudapest:")
    with pytest.raises(FrozenInstanceError):
        narrative.opening = "changed"  # type: ignore[misc]


def test_parser_restores_deterministic_order_when_provider_reorders_notes() -> None:
    narrative = parse_wayfinder_narrative(
        _payload("Vienna", "Budapest", "Prague"),
        ("Budapest", "Vienna", "Prague"),
    )

    assert [note.destination for note in narrative.destination_notes] == [
        "Budapest",
        "Vienna",
        "Prague",
    ]


@pytest.mark.parametrize(
    "value",
    [None, 1, [], {}],
)
def test_parser_requires_string(value: object) -> None:
    with pytest.raises(TypeError, match="must be a string"):
        parse_wayfinder_narrative(value, ("Budapest",))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        "{}",
        json.dumps({"opening": "Open", "destination_notes": []}),
        json.dumps({"opening": "Open", "destination_notes": {}, "comparison_note": None}),
        json.dumps({"opening": "Open", "destination_notes": ["bad"], "comparison_note": None}),
        json.dumps(
            {
                "opening": "Open",
                "destination_notes": [
                    {
                        "destination": "Budapest",
                        "why_it_fits": "Fit",
                        "seasonal_feel": "Feel",
                        "good_to_know": "Know",
                    }
                ],
                "comparison_note": None,
            }
        ),
        json.dumps(
            {
                "opening": "Open",
                "destination_notes": [
                    {
                        "destination": "Budapest",
                        "why_it_fits": "Fit",
                        "seasonal_feel": "Feel",
                        "good_to_know": "Know",
                        "signature_highlights": "bad",
                    }
                ],
                "comparison_note": None,
            }
        ),
        json.dumps(
            {
                "opening": "Open",
                "destination_notes": [
                    {
                        "destination": "Vienna",
                        "why_it_fits": "Fit",
                        "seasonal_feel": "Feel",
                        "good_to_know": "Know",
                        "signature_highlights": [],
                    }
                ],
                "comparison_note": None,
            }
        ),
        json.dumps(
            {
                "opening": "Open",
                "destination_notes": [
                    {
                        "destination": "Budapest",
                        "why_it_fits": "Fit",
                        "seasonal_feel": "Feel",
                        "good_to_know": "Know",
                        "signature_highlights": [],
                    }
                ],
                "comparison_note": 1,
            }
        ),
    ],
)
def test_parser_rejects_invalid_structured_output(text: str) -> None:
    with pytest.raises(ValueError):
        parse_wayfinder_narrative(text, ("Budapest",))


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("destination", None, TypeError),
        ("destination", " ", ValueError),
        ("why_it_fits", "**markdown**", ValueError),
        ("seasonal_feel", "The model says so.", ValueError),
        ("good_to_know", "Check visa rules.", ValueError),
    ],
)
def test_destination_note_rejects_non_plain_or_unsupported_language(
    field: str, value: object, error: type[Exception]
) -> None:
    values: dict[str, object] = {
        "destination": "Budapest",
        "why_it_fits": "Grounded fit.",
        "seasonal_feel": "Historically mild.",
        "good_to_know": "Keep plans flexible.",
    }
    values[field] = value
    with pytest.raises(error):
        WayfinderDestinationNote(**values)  # type: ignore[arg-type]


def test_destination_note_validates_highlights() -> None:
    with pytest.raises(TypeError, match="must be a tuple"):
        WayfinderDestinationNote("A", "Fit", "Feel", "Know", [])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="at most four"):
        WayfinderDestinationNote("A", "Fit", "Feel", "Know", ("1", "2", "3", "4", "5"))
    with pytest.raises(ValueError, match="unique"):
        WayfinderDestinationNote("A", "Fit", "Feel", "Know", ("Castle", "castle"))


def test_destination_note_rejects_overlong_text() -> None:
    with pytest.raises(ValueError, match="too long"):
        WayfinderDestinationNote("A", "word " * 111, "Feel", "Know")


@pytest.mark.parametrize(
    "seasonal_feel",
    [
        "Historically, days are mild. Historically, rain is restrained.",
        "Your dates fall into a comfortable window.",
        "The evidence indicates a mild historical window.",
    ],
)
def test_destination_note_rejects_repetitive_or_mechanical_seasonal_language(
    seasonal_feel: str,
) -> None:
    with pytest.raises(ValueError, match="seasonal_feel"):
        WayfinderDestinationNote("A", "Fit", seasonal_feel, "A validated landmark anchors it.")


def test_good_to_know_may_be_omitted_but_not_used_as_a_weather_disclaimer() -> None:
    omitted = WayfinderDestinationNote("A", "Fit", "The season tends to feel mild.", None)
    assert omitted.good_to_know is None
    assert "None" not in WayfinderNarrative("Opening", (omitted,)).as_plain_text()
    with pytest.raises(ValueError, match="destination character"):
        WayfinderDestinationNote(
            "A",
            "Fit",
            "The season tends to feel mild.",
            "This is historical context, not a forecast.",
        )
    with pytest.raises(ValueError, match="must not duplicate"):
        WayfinderDestinationNote(
            "A",
            "Fit",
            "The season tends to feel mild.",
            "The season tends to feel mild.",
        )


def test_narrative_validates_notes_and_comparison() -> None:
    with pytest.raises(TypeError, match="must be a tuple"):
        WayfinderNarrative("Opening", [])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must not be empty"):
        WayfinderNarrative("Opening", ())
    with pytest.raises(TypeError, match="every destination note"):
        WayfinderNarrative("Opening", ("bad",))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be unique"):
        WayfinderNarrative("Opening", (_note(), _note()))
    with pytest.raises(TypeError, match="comparison_note must be a string"):
        WayfinderNarrative("Opening", (_note(),), 1)  # type: ignore[arg-type]


def test_narrative_includes_comparison_in_compatibility_text() -> None:
    narrative = WayfinderNarrative("Opening", (_note(),), "A grounded comparison.")
    assert narrative.as_plain_text().endswith("A grounded comparison.")
