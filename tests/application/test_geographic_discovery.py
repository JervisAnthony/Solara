"""Tests for broad/open geographic discovery orchestration."""

from collections import Counter
from datetime import date

import pytest

from solara_travel.application import (
    DestinationDiscoveryUnavailableError,
    DestinationNotFoundError,
    RecommendationPlan,
    RecommendationService,
    TravelScopeSuggestionService,
)
from solara_travel.domain import (
    Attraction,
    Destination,
    DestinationCandidateProposal,
    DestinationQuery,
    GeoCoordinates,
    GeoViewport,
    RecommendationRequest,
    TemperatureComfortRange,
    TravelPeriod,
    TravelScope,
    TravelScopeKind,
    TravelScopeSuggestion,
    WeatherObservation,
)
from solara_travel.ports import ProviderUnavailableError


def _locality(name: str, country: str = "Portugal", code: str = "PT") -> TravelScope:
    coordinates = {
        "Porto": GeoCoordinates(41.15, -8.61),
        "Lisbon": GeoCoordinates(38.72, -9.14),
        "Havana": GeoCoordinates(23.11, -82.37),
    }.get(name, GeoCoordinates(40, -8))
    return TravelScope(
        f"{name}, {country}",
        TravelScopeKind.LOCALITY,
        country,
        code,
        canonical_name=name,
        center=coordinates,
        containing_regions=("Norte",) if name == "Porto" else (),
    )


def _request(*queries: str, destination: Destination | None = None) -> RecommendationRequest:
    return RecommendationRequest(
        TravelPeriod(date(2027, 5, 1), date(2027, 5, 5)),
        destination=destination,
        destination_queries=tuple(DestinationQuery(query) for query in queries),
    )


class FakePlaces:
    def discover_destinations(self, request: RecommendationRequest) -> tuple[Destination, ...]:
        return ()

    def discover_attractions(self, destination: Destination) -> tuple[Attraction, ...]:
        return ()


class FakeWeather:
    def get_historical_weather(
        self, destination: Destination, period: TravelPeriod
    ) -> tuple[WeatherObservation, ...]:
        return (WeatherObservation(date(2023, 5, 2), 22, 60, 0),)


class FakeResolver:
    def __init__(self, values: dict[str, TravelScope | None | Exception]) -> None:
        self.values = values
        self.queries: list[str] = []

    def resolve_travel_scope(self, query: DestinationQuery) -> TravelScope | None:
        self.queries.append(query.value)
        value = self.values.get(query.value)
        if isinstance(value, Exception):
            raise value
        return value


class FakeProposalProvider:
    def __init__(self, outcome: DestinationCandidateProposal | Exception) -> None:
        self.outcome = outcome
        self.calls: list[tuple[RecommendationRequest, TravelScope | None]] = []

    def propose_candidates(
        self, request: RecommendationRequest, scope: TravelScope | None
    ) -> DestinationCandidateProposal:
        self.calls.append((request, scope))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _proposal(*names: str) -> DestinationCandidateProposal:
    return DestinationCandidateProposal((), (), (), names)


def _service(
    resolver: FakeResolver | None = None,
    proposal: FakeProposalProvider | None = None,
    *,
    maximum: int = 5,
    scoreable_maximum: int = 15,
) -> RecommendationService:
    return RecommendationService(
        FakePlaces(),
        FakeWeather(),
        TravelPeriod(date(2020, 1, 1), date(2024, 12, 31)),
        TemperatureComfortRange(18, 28, 10),
        scope_resolver=resolver,
        candidate_proposal_provider=proposal,
        maximum_candidates=maximum,
        maximum_scoreable_destinations=scoreable_maximum,
    )


def test_open_discovery_proposes_then_google_validates_and_deduplicates() -> None:
    request = _request()
    porto = _locality("Porto")
    lisbon = _locality("Lisbon")
    region = TravelScope("Norte", TravelScopeKind.REGION, "Portugal", "PT")
    resolver = FakeResolver(
        {
            "Porto": porto,
            "Unknown": None,
            "Region": region,
            "Bad": TypeError("bad provider value"),
            "Lisbon": lisbon,
            "Porto City": porto,
        }
    )
    provider = FakeProposalProvider(
        _proposal("Porto", "Unknown", "Region", "Bad", "Lisbon", "Porto City")
    )
    service = _service(resolver, provider)

    plan = service.prepare(request)
    result = service.recommend_plan(plan)

    assert plan.destination_mode == "discovery"
    assert plan.requires_candidate_proposal
    assert provider.calls == [(request, None)]
    assert [item.destination.name for item in result.recommendations] == ["Porto", "Lisbon"]
    assert result.destination_mode == "discovery"


def test_country_and_multinational_region_scope_filter_every_candidate() -> None:
    portugal = TravelScope("Portugal", TravelScopeKind.COUNTRY, "Portugal", "PT")
    caribbean = TravelScope(
        "Caribbean",
        TravelScopeKind.REGION,
        None,
        None,
        viewport=GeoViewport(GeoCoordinates(9, -89), GeoCoordinates(28, -58)),
    )
    porto = _locality("Porto")
    havana = _locality("Havana", "Cuba", "CU")
    proposal = FakeProposalProvider(_proposal("Porto", "Havana"))
    resolver = FakeResolver(
        {
            "Portugal": portugal,
            "Caribbean": caribbean,
            "Porto, Portugal": porto,
            "Havana, Portugal": havana,
            "Porto, Caribbean": porto,
            "Havana, Caribbean": havana,
        }
    )

    portugal_result = _service(resolver, proposal).recommend(_request("Portugal"))
    caribbean_result = _service(resolver, proposal).recommend(_request("Caribbean"))

    assert [item.destination.name for item in portugal_result.recommendations] == ["Porto"]
    assert portugal_result.destination_mode == "scope_discovery"
    assert portugal_result.travel_scope is portugal
    assert portugal_result.recommendations[0].origin is not None
    assert portugal_result.recommendations[0].origin.administrative_context == ("Norte",)
    assert [item.destination.name for item in caribbean_result.recommendations] == ["Havana"]


def test_explicit_localities_are_not_ai_ranked_and_preserve_score_ordering() -> None:
    porto = _locality("Porto")
    lisbon = _locality("Lisbon")
    resolver = FakeResolver({"Porto": porto, "Lisbon": lisbon})
    proposal = FakeProposalProvider(_proposal("Havana"))

    result = _service(resolver, proposal).recommend(_request("Porto", "Lisbon"))

    assert result.destination_mode == "explicit_queries"
    assert {item.destination.name for item in result.recommendations} == {"Porto", "Lisbon"}
    assert proposal.calls == []


@pytest.mark.parametrize("queries", [("Portugal", "Lisbon"), ("Lisbon", "Portugal")])
def test_broad_scope_can_mix_with_an_authoritative_locality(
    queries: tuple[str, str],
) -> None:
    portugal = TravelScope("Portugal", TravelScopeKind.COUNTRY, "Portugal", "PT")
    porto = _locality("Porto")
    lisbon = _locality("Lisbon")
    resolver = FakeResolver(
        {
            "Portugal": portugal,
            "Lisbon": lisbon,
            "Porto, Portugal": porto,
        }
    )
    provider = FakeProposalProvider(_proposal("Porto"))

    result = _service(resolver, provider).recommend(_request(*queries))

    assert result.destination_mode == "mixed_scopes"
    assert {item.destination.name for item in result.recommendations} == {"Lisbon", "Porto"}
    by_name = {item.destination.name: item.origin for item in result.recommendations}
    assert by_name["Lisbon"] is not None
    assert by_name["Lisbon"].was_explicit_locality  # type: ignore[union-attr]
    assert by_name["Porto"] is not None
    assert by_name["Porto"].requested_scope == "Portugal"  # type: ignore[union-attr]
    assert provider.calls == [(_request(*queries), portugal)]


def test_unresolved_explicit_scope_preserves_typed_not_found_error() -> None:
    query = DestinationQuery("Typoo")
    with pytest.raises(DestinationNotFoundError) as raised:
        _service(FakeResolver({}), FakeProposalProvider(_proposal("Porto"))).prepare(
            _request(query.value)
        )
    assert raised.value.query == query


def test_discovery_unavailable_and_zero_validated_candidates_are_safe() -> None:
    request = _request()
    portugal = TravelScope("Portugal", TravelScopeKind.COUNTRY, "Portugal", "PT")
    resolver = FakeResolver({"Portugal": portugal, "Unknown": None})
    with pytest.raises(DestinationDiscoveryUnavailableError):
        _service(resolver).prepare(_request("Portugal"))
    with pytest.raises(DestinationDiscoveryUnavailableError) as raised:
        _service(
            resolver,
            FakeProposalProvider(ProviderUnavailableError("offline")),
        ).recommend(request)
    assert isinstance(raised.value.__cause__, ProviderUnavailableError)
    result = _service(resolver, FakeProposalProvider(_proposal("Unknown"))).recommend(request)
    assert result.recommendations == ()


def test_candidate_cap_is_applied_after_validation() -> None:
    scopes = {name: _locality(name) for name in ("One", "Two", "Three")}
    service = _service(FakeResolver(scopes), FakeProposalProvider(_proposal(*scopes)), maximum=2)
    assert service.recommend(_request()).recommendation_count == 2


def test_fair_round_robin_allocation_never_exceeds_global_scoreable_budget() -> None:
    countries: dict[str, TravelScope] = {}
    resolved: dict[str, TravelScope] = {}
    proposals: dict[str, DestinationCandidateProposal] = {}
    for country_index in range(5):
        country = f"Country {country_index}"
        code = f"C{country_index}"
        countries[country] = TravelScope(
            country,
            TravelScopeKind.COUNTRY,
            country,
            code,
        )
        resolved[country] = countries[country]
        names = tuple(f"Place {country_index}-{index}" for index in range(5))
        proposals[country] = _proposal(*names)
        for place_index, name in enumerate(names):
            resolved[f"{name}, {country}"] = TravelScope(
                f"{name}, {country}",
                TravelScopeKind.LOCALITY,
                country,
                code,
                canonical_name=name,
                center=GeoCoordinates(country_index, place_index),
                containing_regions=(f"Province {country_index}",),
            )

    class ScopedProposalProvider:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def propose_candidates(
            self,
            request: RecommendationRequest,
            scope: TravelScope | None,
        ) -> DestinationCandidateProposal:
            assert scope is not None
            self.calls.append(scope.display_name)
            return proposals[scope.display_name]

    provider = ScopedProposalProvider()
    result = _service(
        FakeResolver(resolved),
        provider,  # type: ignore[arg-type]
    ).recommend(_request(*countries))

    assert result.recommendation_count == 15
    assert set(provider.calls) == set(countries)
    assert Counter(
        item.origin.requested_scope  # type: ignore[union-attr]
        for item in result.recommendations
    ) == Counter({country: 3 for country in countries})


def test_explicit_locality_priority_survives_containment_and_deduplication() -> None:
    france = TravelScope("France", TravelScopeKind.COUNTRY, "France", "FR")
    japan = TravelScope("Japan", TravelScopeKind.COUNTRY, "Japan", "JP")
    tokyo = _locality("Tokyo", "Japan", "JP")
    paris = _locality("Paris", "France", "FR")
    kyoto = _locality("Kyoto", "Japan", "JP")
    resolver = FakeResolver(
        {
            "Tokyo": tokyo,
            "France": france,
            "Japan": japan,
            "Tokyo, France": tokyo,
            "Paris, France": paris,
            "Tokyo, Japan": tokyo,
            "Kyoto, Japan": kyoto,
        }
    )

    class ScopeAwareProposal:
        def propose_candidates(
            self,
            request: RecommendationRequest,
            scope: TravelScope | None,
        ) -> DestinationCandidateProposal:
            assert scope is not None
            return _proposal("Tokyo", "Paris") if scope is france else _proposal("Tokyo", "Kyoto")

    result = _service(
        resolver,
        ScopeAwareProposal(),  # type: ignore[arg-type]
    ).recommend(_request("France", "Tokyo", "Japan"))

    by_name = {item.destination.name: item for item in result.recommendations}
    assert set(by_name) == {"Tokyo", "Paris", "Kyoto"}
    assert by_name["Tokyo"].origin is not None
    assert by_name["Tokyo"].origin.was_explicit_locality
    assert by_name["Paris"].origin is not None
    assert by_name["Paris"].origin.requested_scope == "France"


def test_explicit_locality_can_fill_the_entire_scoreable_budget() -> None:
    japan = TravelScope("Japan", TravelScopeKind.COUNTRY, "Japan", "JP")
    tokyo = _locality("Tokyo", "Japan", "JP")
    provider = FakeProposalProvider(_proposal("Kyoto"))
    service = _service(
        FakeResolver({"Tokyo": tokyo, "Japan": japan}),
        provider,
        scoreable_maximum=1,
    )

    result = service.recommend(_request("Tokyo", "Japan"))

    assert [item.destination.name for item in result.recommendations] == ["Tokyo"]
    assert provider.calls == []


def test_candidate_deduplication_validates_alignment_and_keeps_first_identity() -> None:
    destination = _locality("Porto").to_destination()
    service = _service()
    with pytest.raises(ValueError, match="origins must align"):
        service._deduplicate_candidates((destination,), (None, None))
    candidates, origins = service._deduplicate_candidates(
        (destination, destination),
        (None, None),
    )
    assert candidates == (destination,)
    assert origins == (None,)


@pytest.mark.parametrize("maximum", [0, 6])
def test_service_validates_candidate_cap(maximum: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 5"):
        _service(maximum=maximum)
    with pytest.raises(TypeError, match="maximum_candidates must be an int"):
        _service(maximum=True)  # type: ignore[arg-type]


@pytest.mark.parametrize("maximum", [0, 16])
def test_service_validates_global_scoreable_cap(maximum: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 15"):
        _service(scoreable_maximum=maximum)
    with pytest.raises(TypeError, match="maximum_scoreable_destinations must be an int"):
        _service(scoreable_maximum=True)  # type: ignore[arg-type]


def test_service_validates_optional_ports_and_plan_contract() -> None:
    with pytest.raises(TypeError, match="scope_resolver"):
        _service(resolver="bad")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="candidate_proposal_provider"):
        _service(proposal="bad")  # type: ignore[arg-type]
    request = _request()
    destination = _locality("Porto").to_destination()
    assert _service().prepare(_request(destination=destination)).destination_mode == "pre_resolved"
    with pytest.raises(TypeError, match="request must be RecommendationRequest"):
        RecommendationPlan("bad", ())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="candidates must be a tuple"):
        RecommendationPlan(request, [])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="candidates must contain Destination"):
        RecommendationPlan(request, ("bad",))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="travel_scope"):
        RecommendationPlan(request, (), travel_scope="bad")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="only valid for discovery"):
        RecommendationPlan(request, None, destination_mode="explicit_queries")
    assert RecommendationPlan(request, None).proposal_call_count == 1
    assert RecommendationPlan(request, ()).proposal_call_count == 0
    with pytest.raises(TypeError, match="candidate_origins must be a tuple"):
        RecommendationPlan(request, (), candidate_origins=[])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="candidate_origins must contain"):
        RecommendationPlan(request, (destination,), candidate_origins=("bad",))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="align"):
        RecommendationPlan(request, (destination,), candidate_origins=(None, None))
    with pytest.raises(ValueError, match="require prepared candidates"):
        RecommendationPlan(request, None, candidate_origins=(None,))
    with pytest.raises(TypeError, match="broad_scopes must be a tuple"):
        RecommendationPlan(request, (), broad_scopes=[])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="broad_scopes must contain"):
        RecommendationPlan(request, (), broad_scopes=("bad",))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must not contain localities"):
        RecommendationPlan(request, (), broad_scopes=(_locality("Porto"),))
    with pytest.raises(TypeError, match="plan must be RecommendationPlan"):
        _service().recommend_plan("bad")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="request must be a RecommendationRequest"):
        _service().recommend("bad")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="request must be a RecommendationRequest"):
        _service().prepare("bad")  # type: ignore[arg-type]


def test_service_requires_resolution_for_proposal_and_valid_scope_values() -> None:
    proposal = FakeProposalProvider(_proposal("Porto"))
    service_without_resolver = _service(proposal=proposal)
    with pytest.raises(TypeError, match="candidate discovery requires"):
        service_without_resolver.prepare(_request())
    with pytest.raises(TypeError, match="candidate discovery requires"):
        service_without_resolver.recommend_plan(RecommendationPlan(_request(), None))

    invalid_resolver = FakeResolver({"Portugal": "bad"})  # type: ignore[dict-item]
    with pytest.raises(TypeError, match="travel scope resolver"):
        _service(invalid_resolver, proposal).prepare(_request("Portugal"))


def test_places_provider_can_own_scope_resolution_and_qualified_names_are_not_repeated() -> None:
    portugal = TravelScope("Portugal", TravelScopeKind.COUNTRY, "Portugal", "PT")
    porto = _locality("Porto")

    class ScopePlaces(FakePlaces):
        def __init__(self) -> None:
            self.queries: list[str] = []

        def resolve_travel_scope(self, query: DestinationQuery) -> TravelScope | None:
            self.queries.append(query.value)
            return {"Portugal": portugal, "Porto, Portugal": porto}.get(query.value)

    places = ScopePlaces()
    provider = FakeProposalProvider(_proposal("Porto, Portugal"))
    service = RecommendationService(
        places,
        FakeWeather(),
        TravelPeriod(date(2020, 1, 1), date(2024, 12, 31)),
        TemperatureComfortRange(18, 28, 10),
        candidate_proposal_provider=provider,
    )

    assert service.recommend(_request("Portugal")).recommendation_count == 1
    assert places.queries == ["Portugal", "Porto, Portugal"]


def test_destination_not_found_validates_correction_suggestions() -> None:
    query = DestinationQuery("Lisbom")
    error = DestinationNotFoundError(query, ("Lisbon, Portugal",))
    assert error.suggestions == ("Lisbon, Portugal",)
    with pytest.raises(TypeError, match="query must be"):
        DestinationNotFoundError("Lisbom")  # type: ignore[arg-type]
    for invalid in (["Lisbon"], ("",)):
        with pytest.raises(TypeError, match="suggestions"):
            DestinationNotFoundError(query, invalid)  # type: ignore[arg-type]


class FakeSuggestionProvider:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome

    def suggest_travel_scopes(self, query: DestinationQuery) -> object:
        return self.outcome


def test_suggestion_service_bounds_and_deduplicates_provider_output() -> None:
    values = tuple(
        TravelScopeSuggestion(name, TravelScopeKind.LOCALITY)
        for name in ("Porto", "porto", "Lisbon", "Coimbra", "Évora", "Faro", "Braga")
    )
    service = TravelScopeSuggestionService(FakeSuggestionProvider(values))
    assert [item.display_name for item in service.suggest(DestinationQuery("por"))] == [
        "Porto",
        "Lisbon",
        "Coimbra",
        "Évora",
        "Faro",
    ]
    with pytest.raises(TypeError, match="query must be"):
        service.suggest("por")  # type: ignore[arg-type]


def test_suggestion_service_validates_provider_contract() -> None:
    with pytest.raises(TypeError, match="provider must satisfy"):
        TravelScopeSuggestionService(object())  # type: ignore[arg-type]
    for outcome in ([], ("Porto",)):
        service = TravelScopeSuggestionService(FakeSuggestionProvider(outcome))
        with pytest.raises(TypeError, match="suggestion provider"):
            service.suggest(DestinationQuery("por"))
