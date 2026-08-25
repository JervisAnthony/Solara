"""Tests for provider-neutral geographic scope and AI proposal values."""

import pytest

from solara_travel.domain import (
    DestinationCandidateProposal,
    GeoCoordinates,
    GeoViewport,
    TravelScope,
    TravelScopeKind,
    TravelScopeSuggestion,
)


def _locality(
    name: str = "Funchal",
    *,
    country: str = "Portugal",
    code: str = "PT",
    coordinates: GeoCoordinates | None = None,
    regions: tuple[str, ...] = ("Madeira",),
) -> TravelScope:
    return TravelScope(
        display_name=f" {name}, {country} ",
        canonical_name=f" {name} ",
        kind=TravelScopeKind.LOCALITY,
        country_name=f" {country} ",
        country_code=f" {code.lower()} ",
        center=coordinates or GeoCoordinates(32.65, -16.91),
        containing_regions=regions,
    )


def test_scope_normalizes_locality_and_converts_only_validated_locality() -> None:
    scope = _locality()

    assert scope.display_name == "Funchal, Portugal"
    assert scope.canonical_name == "Funchal"
    assert scope.country_name == "Portugal"
    assert scope.country_code == "PT"
    destination = scope.to_destination()
    assert (destination.name, destination.country) == ("Funchal", "Portugal")


def test_country_region_and_antimeridian_viewport_containment() -> None:
    candidate = _locality()
    country = TravelScope(
        "Portugal",
        TravelScopeKind.COUNTRY,
        "Portugal",
        "pt",
    )
    region = TravelScope(
        "Madeira",
        TravelScopeKind.REGION,
        "Portugal",
        "PT",
        viewport=GeoViewport(GeoCoordinates(30, -18), GeoCoordinates(34, -15)),
    )
    dateline = GeoViewport(GeoCoordinates(-20, 170), GeoCoordinates(20, -170))

    assert country.contains(candidate)
    assert region.contains(candidate)
    assert not region.contains(_locality(country="Spain", code="ES"))
    assert dateline.contains(GeoCoordinates(0, 179))
    assert dateline.contains(GeoCoordinates(0, -179))
    assert not dateline.contains(GeoCoordinates(30, 179))
    assert not dateline.contains(GeoCoordinates(0, 0))


def test_multinational_region_uses_viewport_and_rejects_nonlocality() -> None:
    caribbean = TravelScope(
        "Caribbean",
        TravelScopeKind.REGION,
        None,
        None,
        viewport=GeoViewport(GeoCoordinates(9, -89), GeoCoordinates(28, -58)),
    )
    havana = _locality(
        "Havana", country="Cuba", code="CU", coordinates=GeoCoordinates(23.1, -82.4), regions=()
    )
    europe = _locality("Lisbon", coordinates=GeoCoordinates(38.7, -9.1), regions=())
    other_region = TravelScope("Azores", TravelScopeKind.REGION, "Portugal", "PT")

    assert caribbean.contains(havana)
    assert not caribbean.contains(europe)
    assert not caribbean.contains(other_region)
    assert not havana.contains(havana)
    with pytest.raises(TypeError, match="candidate must be TravelScope"):
        caribbean.contains("Havana")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kwargs", "error", "message"),
    [
        ({"display_name": 1}, TypeError, "display_name must be a string"),
        ({"display_name": " "}, ValueError, "display_name must not be blank"),
        ({"kind": "region"}, TypeError, "kind must be TravelScopeKind"),
        ({"country_name": 1}, TypeError, "country_name must be a string or None"),
        ({"country_name": " "}, ValueError, "country_name must not be blank"),
        ({"country_name": None}, ValueError, "must both be set"),
        (
            {
                "kind": TravelScopeKind.COUNTRY,
                "country_name": None,
                "country_code": None,
            },
            ValueError,
            "must include country",
        ),
        ({"canonical_name": 1}, TypeError, "canonical_name must be a string or None"),
        ({"canonical_name": " "}, ValueError, "canonical_name must not be blank"),
        ({"center": "point"}, TypeError, "center must be GeoCoordinates"),
        ({"viewport": "bounds"}, TypeError, "viewport must be GeoViewport"),
        ({"containing_regions": []}, TypeError, "containing_regions must be a tuple"),
        ({"containing_regions": ("",)}, ValueError, "non-blank strings"),
        ({"containing_regions": ("Madeira", "madeira")}, ValueError, "duplicates"),
    ],
)
def test_scope_rejects_invalid_values(
    kwargs: dict[str, object], error: type[Exception], message: str
) -> None:
    values: dict[str, object] = {
        "display_name": "Madeira",
        "kind": TravelScopeKind.REGION,
        "country_name": "Portugal",
        "country_code": "PT",
    }
    values.update(kwargs)
    with pytest.raises(error, match=message):
        TravelScope(**values)  # type: ignore[arg-type]


def test_scope_rejects_invalid_viewport_and_nonlocality_conversion() -> None:
    with pytest.raises(TypeError, match="southwest"):
        GeoViewport("south", GeoCoordinates(1, 1))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="northeast"):
        GeoViewport(GeoCoordinates(0, 0), "north")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="latitude bounds"):
        GeoViewport(GeoCoordinates(2, 0), GeoCoordinates(1, 1))
    with pytest.raises(TypeError, match="coordinates"):
        GeoViewport(GeoCoordinates(0, 0), GeoCoordinates(1, 1)).contains("x")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="only locality"):
        TravelScope("Portugal", TravelScopeKind.COUNTRY, "Portugal", "PT").to_destination()
    with pytest.raises(ValueError, match="center coordinates"):
        TravelScope(
            "Funchal, Portugal",
            TravelScopeKind.LOCALITY,
            "Portugal",
            "PT",
        ).to_destination()


def test_suggestion_and_candidate_proposal_normalize_and_validate() -> None:
    suggestion = TravelScopeSuggestion("  Portugal ", TravelScopeKind.COUNTRY)
    proposal = DestinationCandidateProposal(
        themes=(" Culture ",),
        desired_experiences=("Local food",),
        avoidances=(),
        candidate_localities=("Funchal", "Porto"),
    )

    assert suggestion.display_name == "Portugal"
    assert proposal.themes == ("Culture",)
    for value in (None, " "):
        with pytest.raises((TypeError, ValueError)):
            TravelScopeSuggestion(value, TravelScopeKind.COUNTRY)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="kind"):
        TravelScopeSuggestion("Portugal", "country")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must not be empty"):
        DestinationCandidateProposal((), (), (), ())
    with pytest.raises(ValueError, match="at most 8"):
        DestinationCandidateProposal((), (), (), tuple(f"City {index}" for index in range(9)))


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("themes", [], TypeError),
        ("desired_experiences", ("",), ValueError),
        ("avoidances", (1,), ValueError),
        ("candidate_localities", ("Porto", "porto"), ValueError),
    ],
)
def test_candidate_proposal_rejects_invalid_arrays(
    field: str, value: object, error: type[Exception]
) -> None:
    values: dict[str, object] = {
        "themes": (),
        "desired_experiences": (),
        "avoidances": (),
        "candidate_localities": ("Porto",),
    }
    values[field] = value
    with pytest.raises(error):
        DestinationCandidateProposal(**values)  # type: ignore[arg-type]
