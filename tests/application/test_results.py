"""Tests for structured recommendation result and evidence values."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from solara_travel.analytics.scoring import ScoreComponent, SuitabilityScore
from solara_travel.analytics.seasonality import (
    SeasonalTemperatureComfortAssessment,
    SeasonalWeatherProfile,
    assess_seasonal_temperature_comfort,
)
from solara_travel.application.results import (
    DestinationRecommendation,
    RecommendationEvidence,
    RecommendationResult,
)
from solara_travel.domain.attraction import Attraction
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.destination import Destination
from solara_travel.domain.geography import GeoCoordinates
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.weather import WeatherObservation


def _period(
    start: date = date(2027, 4, 10),
    end: date = date(2027, 4, 12),
) -> TravelPeriod:
    return TravelPeriod(start_date=start, end_date=end)


def _destination(
    name: str = "Kyoto",
    country: str = "Japan",
    latitude: float = 35.0116,
    longitude: float = 135.7681,
) -> Destination:
    return Destination(
        name=name,
        country=country,
        coordinates=GeoCoordinates(latitude=latitude, longitude=longitude),
    )


def _attraction(
    name: str = "Kiyomizu-dera",
    category: str = "temple",
    latitude: float = 34.9949,
    longitude: float = 135.7850,
) -> Attraction:
    return Attraction(
        name=name,
        category=category,
        coordinates=GeoCoordinates(latitude=latitude, longitude=longitude),
    )


def _profile(
    target_period: TravelPeriod | None = None,
    temperature: float = 22.0,
) -> SeasonalWeatherProfile:
    period = target_period or _period()
    observation = WeatherObservation(
        observed_on=date(
            2020,
            period.start_date.month,
            period.start_date.day,
        ),
        temperature_celsius=temperature,
        relative_humidity_percent=60.0,
        precipitation_mm=1.0,
    )
    return SeasonalWeatherProfile(
        target_period=period,
        observations=(observation,),
    )


def _comfort(
    profile: SeasonalWeatherProfile,
) -> SeasonalTemperatureComfortAssessment:
    return assess_seasonal_temperature_comfort(
        profile,
        TemperatureComfortRange(18.0, 28.0, 10.0),
    )


def _evidence(
    target_period: TravelPeriod | None = None,
    attractions: tuple[Attraction, ...] = (),
    temperature: float = 22.0,
) -> RecommendationEvidence:
    profile = _profile(target_period, temperature)
    return RecommendationEvidence(
        attractions=attractions,
        seasonal_weather=profile,
        seasonal_temperature_comfort=_comfort(profile),
    )


def _suitability(
    evidence: RecommendationEvidence,
    *,
    include_seasonal: bool = True,
    seasonal_name: str = "seasonal_temperature_comfort",
    seasonal_score: float | None = None,
    generic_score: float | None = None,
) -> SuitabilityScore:
    components: list[ScoreComponent] = []
    if include_seasonal:
        components.append(
            ScoreComponent(
                name=seasonal_name,
                score=(
                    evidence.seasonal_temperature_comfort.score
                    if seasonal_score is None
                    else seasonal_score
                ),
                weight=0.6,
            )
        )
    if generic_score is not None:
        components.append(
            ScoreComponent(
                name="interest_match",
                score=generic_score,
                weight=0.4,
            )
        )
    if not components:
        components.append(ScoreComponent("interest_match", 0.7, 1.0))
    return SuitabilityScore(tuple(components))


def _recommendation(
    destination: Destination | None = None,
    target_period: TravelPeriod | None = None,
    *,
    temperature: float = 22.0,
    generic_score: float | None = None,
) -> DestinationRecommendation:
    evidence = _evidence(target_period, temperature=temperature)
    return DestinationRecommendation(
        destination=destination or _destination(),
        suitability=_suitability(evidence, generic_score=generic_score),
        evidence=evidence,
    )


@pytest.mark.parametrize(
    "attractions",
    [
        (),
        (_attraction(),),
        (
            _attraction(),
            _attraction("Nishiki Market", "market", 35.0050, 135.7649),
        ),
    ],
)
def test_recommendation_evidence_preserves_attraction_tuple(
    attractions: tuple[Attraction, ...],
) -> None:
    """Empty and populated attraction evidence should retain supplied order."""

    evidence = _evidence(attractions=attractions)

    assert evidence.attractions is attractions
    assert evidence.attractions == attractions
    assert isinstance(evidence.seasonal_weather, SeasonalWeatherProfile)
    assert (
        evidence.seasonal_temperature_comfort.profile
        == evidence.seasonal_weather
    )


def test_recommendation_evidence_is_immutable_hashable_value() -> None:
    """Equivalent evidence should compare and hash as immutable values."""

    first = _evidence(attractions=(_attraction(),))
    second = _evidence(attractions=(_attraction(),))

    assert first == second
    assert {first, second} == {first}

    with pytest.raises(FrozenInstanceError):
        first.attractions = ()


@pytest.mark.parametrize("attractions", [None, [_attraction()]])
def test_recommendation_evidence_rejects_non_tuple_attractions(
    attractions: object,
) -> None:
    """Attraction evidence must use the explicit immutable tuple contract."""

    profile = _profile()
    with pytest.raises(TypeError, match="attractions must be a tuple"):
        RecommendationEvidence(
            attractions=attractions,  # type: ignore[arg-type]
            seasonal_weather=profile,
            seasonal_temperature_comfort=_comfort(profile),
        )


def test_recommendation_evidence_rejects_invalid_attraction_item() -> None:
    """Provider payloads and unrelated values are not application evidence."""

    profile = _profile()
    with pytest.raises(TypeError, match="every attraction"):
        RecommendationEvidence(
            attractions=(_attraction(), "market"),  # type: ignore[arg-type]
            seasonal_weather=profile,
            seasonal_temperature_comfort=_comfort(profile),
        )


def test_recommendation_evidence_rejects_duplicate_attractions() -> None:
    """Full duplicate Attraction values should be rejected."""

    attraction = _attraction()
    profile = _profile()
    with pytest.raises(ValueError, match="must not contain duplicates"):
        RecommendationEvidence(
            attractions=(attraction, attraction),
            seasonal_weather=profile,
            seasonal_temperature_comfort=_comfort(profile),
        )


def test_recommendation_evidence_allows_same_name_for_distinct_attractions() -> None:
    """Attraction identity must use full value equality rather than names."""

    first = _attraction(name="Central Market", category="market")
    second = _attraction(
        name="Central Market",
        category="museum",
        latitude=35.1,
    )

    evidence = _evidence(attractions=(first, second))

    assert evidence.attractions == (first, second)


def test_recommendation_evidence_rejects_invalid_seasonal_weather() -> None:
    """Seasonal weather must use the existing analytics value."""

    profile = _profile()
    with pytest.raises(TypeError, match="seasonal_weather must be"):
        RecommendationEvidence(
            attractions=(),
            seasonal_weather="spring",  # type: ignore[arg-type]
            seasonal_temperature_comfort=_comfort(profile),
        )


def test_recommendation_evidence_rejects_invalid_seasonal_comfort() -> None:
    """Seasonal comfort must use the existing analytics assessment."""

    with pytest.raises(TypeError, match="seasonal_temperature_comfort must be"):
        RecommendationEvidence(
            attractions=(),
            seasonal_weather=_profile(),
            seasonal_temperature_comfort=0.9,  # type: ignore[arg-type]
        )


def test_recommendation_evidence_rejects_mismatched_profile_and_comfort() -> None:
    """Weather and comfort evidence must describe exactly the same profile."""

    weather = _profile(temperature=22.0)
    other_weather = _profile(temperature=24.0)

    with pytest.raises(ValueError, match="must describe seasonal weather"):
        RecommendationEvidence(
            attractions=(),
            seasonal_weather=weather,
            seasonal_temperature_comfort=_comfort(other_weather),
        )


def test_destination_recommendation_exposes_existing_score_state() -> None:
    """Destination results should preserve values and derive score accessors."""

    destination = _destination()
    evidence = _evidence(attractions=(_attraction(),))
    suitability = _suitability(evidence, generic_score=0.5)
    recommendation = DestinationRecommendation(destination, suitability, evidence)

    assert recommendation.destination is destination
    assert recommendation.suitability is suitability
    assert recommendation.evidence is evidence
    assert recommendation.score == suitability.score
    assert recommendation.components is suitability.components


def test_destination_recommendation_is_immutable_hashable_value() -> None:
    """Equivalent destination recommendations should be frozen values."""

    first = _recommendation()
    second = _recommendation()

    assert first == second
    assert {first, second} == {first}

    with pytest.raises(FrozenInstanceError):
        first.destination = _destination("Osaka")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("destination", "Kyoto", "destination must be a Destination"),
        ("suitability", 0.8, "suitability must be a SuitabilityScore"),
        ("evidence", {}, "evidence must be RecommendationEvidence"),
    ],
)
def test_destination_recommendation_rejects_invalid_field_type(
    field: str,
    value: object,
    message: str,
) -> None:
    """Destination results require existing Solara-owned value types."""

    evidence = _evidence()
    values: dict[str, object] = {
        "destination": _destination(),
        "suitability": _suitability(evidence),
        "evidence": evidence,
    }
    values[field] = value

    with pytest.raises(TypeError, match=message):
        DestinationRecommendation(**values)  # type: ignore[arg-type]


def test_destination_recommendation_allows_absent_seasonal_component() -> None:
    """Result models must not prescribe the future component-selection policy."""

    evidence = _evidence()
    recommendation = DestinationRecommendation(
        _destination(),
        _suitability(evidence, include_seasonal=False),
        evidence,
    )

    assert recommendation.components[0].name == "interest_match"


@pytest.mark.parametrize(
    "name",
    [
        "seasonal_temperature_comfort",
        "  Seasonal_Temperature_Comfort  ",
    ],
)
def test_destination_recommendation_accepts_matching_seasonal_component(
    name: str,
) -> None:
    """Owned component comparison should normalize names but preserve them."""

    evidence = _evidence()
    recommendation = DestinationRecommendation(
        _destination(),
        _suitability(evidence, seasonal_name=name),
        evidence,
    )

    assert recommendation.components[0].name == name


def test_destination_recommendation_rejects_conflicting_seasonal_score() -> None:
    """A named seasonal score must equal the retained analytical evidence."""

    evidence = _evidence(temperature=22.0)
    with pytest.raises(ValueError, match="component score must match evidence"):
        DestinationRecommendation(
            _destination(),
            _suitability(evidence, seasonal_score=0.5),
            evidence,
        )


def test_destination_recommendation_supports_generic_component_interop() -> None:
    """Owned seasonal evidence should coexist with generic scoring components."""

    evidence = _evidence(temperature=22.0)
    suitability = _suitability(evidence, generic_score=0.4)
    recommendation = DestinationRecommendation(
        _destination(), suitability, evidence
    )

    assert tuple(component.name for component in recommendation.components) == (
        "seasonal_temperature_comfort",
        "interest_match",
    )
    assert recommendation.score == suitability.score


def test_recommendation_result_allows_empty_discovery_result() -> None:
    """Destination discovery may legitimately produce no recommendations."""

    request = RecommendationRequest(_period())
    result = RecommendationResult(request, ())

    assert result.request is request
    assert result.recommendations == ()
    assert result.recommendation_count == 0
    assert result.has_recommendations is False


def test_recommendation_result_preserves_non_ranked_input_order() -> None:
    """Result values must preserve order without introducing ranking policy."""

    period = _period()
    lower = _recommendation(
        _destination("Kyoto"),
        period,
        temperature=33.0,
    )
    higher = _recommendation(
        _destination("Osaka", latitude=34.6937, longitude=135.5023),
        period,
        temperature=22.0,
    )
    assert lower.score < higher.score

    supplied = (lower, higher)
    result = RecommendationResult(RecommendationRequest(period), supplied)

    assert result.recommendations is supplied
    assert result.recommendations == (lower, higher)
    assert result.recommendation_count == 2
    assert result.has_recommendations is True


def test_recommendation_result_is_immutable_hashable_value() -> None:
    """Equivalent result structures should be frozen and hashable."""

    request = RecommendationRequest(_period())
    first = RecommendationResult(request, (_recommendation(),))
    second = RecommendationResult(request, (_recommendation(),))

    assert first == second
    assert {first, second} == {first}

    with pytest.raises(FrozenInstanceError):
        first.recommendations = ()


def test_recommendation_result_allows_matching_preselected_destination() -> None:
    """Known-destination requests may be empty or contain that destination."""

    destination = _destination()
    request = RecommendationRequest(_period(), destination=destination)

    empty = RecommendationResult(request, ())
    matching = RecommendationResult(
        request,
        (_recommendation(destination, request.travel_period),),
    )

    assert empty.has_recommendations is False
    assert matching.recommendations[0].destination == destination


def test_recommendation_result_rejects_other_preselected_destination() -> None:
    """Known-destination requests must not return an alternative destination."""

    requested = _destination()
    other = _destination("Osaka", latitude=34.6937, longitude=135.5023)
    request = RecommendationRequest(_period(), destination=requested)

    with pytest.raises(ValueError, match="must match requested destination"):
        RecommendationResult(
            request,
            (_recommendation(other, request.travel_period),),
        )


def test_recommendation_result_rejects_invalid_request() -> None:
    """A result must remain grounded to a RecommendationRequest."""

    with pytest.raises(TypeError, match="request must be a RecommendationRequest"):
        RecommendationResult("April trip", ())  # type: ignore[arg-type]


@pytest.mark.parametrize("recommendations", [None, []])
def test_recommendation_result_rejects_non_tuple_recommendations(
    recommendations: object,
) -> None:
    """Recommendation collections require an immutable tuple."""

    with pytest.raises(TypeError, match="recommendations must be a tuple"):
        RecommendationResult(
            RecommendationRequest(_period()),
            recommendations,  # type: ignore[arg-type]
        )


def test_recommendation_result_rejects_invalid_recommendation_item() -> None:
    """Every result item must be a DestinationRecommendation."""

    with pytest.raises(TypeError, match="every recommendation"):
        RecommendationResult(
            RecommendationRequest(_period()),
            (_recommendation(), "Osaka"),  # type: ignore[arg-type]
        )


def test_recommendation_result_rejects_duplicate_destination_values() -> None:
    """A result cannot repeat the same full Destination value."""

    destination = _destination()
    period = _period()
    first = _recommendation(destination, period, temperature=22.0)
    second = _recommendation(destination, period, temperature=24.0)

    with pytest.raises(ValueError, match="destinations must be unique"):
        RecommendationResult(
            RecommendationRequest(period),
            (first, second),
        )


def test_recommendation_result_allows_same_name_for_distinct_destinations() -> None:
    """Destination uniqueness uses full equality rather than names alone."""

    period = _period()
    united_states = _destination(
        "Springfield", "United States", 39.7817, -89.6501
    )
    canada = _destination("Springfield", "Canada", 45.0, -75.0)

    result = RecommendationResult(
        RecommendationRequest(period),
        (
            _recommendation(united_states, period),
            _recommendation(canada, period),
        ),
    )

    assert result.recommendation_count == 2


@pytest.mark.parametrize(
    "evidence_period",
    [
        _period(date(2028, 4, 10), date(2028, 4, 12)),
        _period(date(2027, 5, 1), date(2027, 5, 3)),
    ],
)
def test_recommendation_result_rejects_evidence_for_other_exact_period(
    evidence_period: TravelPeriod,
) -> None:
    """Result grounding uses exact periods, not merely seasonal resemblance."""

    request_period = _period()
    with pytest.raises(ValueError, match="target period must match request"):
        RecommendationResult(
            RecommendationRequest(request_period),
            (_recommendation(target_period=evidence_period),),
        )


def test_recommendation_result_public_imports() -> None:
    """Application values should be available through both intended imports."""

    import solara_travel.application as application

    assert application.DestinationRecommendation is DestinationRecommendation
    assert application.RecommendationEvidence is RecommendationEvidence
    assert application.RecommendationResult is RecommendationResult
