"""Application service coordinating deterministic Solara recommendations."""

from dataclasses import dataclass

from solara_travel.analytics.scoring import ScoreComponent, SuitabilityScore
from solara_travel.analytics.seasonality import (
    assess_seasonal_temperature_comfort,
    build_seasonal_weather_profile,
    seasonal_temperature_comfort_score_component,
)
from solara_travel.application.errors import (
    BroadScopeCombinationError,
    DestinationDiscoveryUnavailableError,
    DestinationNotFoundError,
)
from solara_travel.application.results import (
    DestinationRecommendation,
    RecommendationEvidence,
    RecommendationResult,
)
from solara_travel.domain.climate import TemperatureComfortRange
from solara_travel.domain.destination import (
    DESTINATION_QUERY_MAX_LENGTH,
    Destination,
    DestinationQuery,
)
from solara_travel.domain.recommendation import RecommendationRequest
from solara_travel.domain.travel import TravelPeriod
from solara_travel.domain.travel_scope import TravelScope, TravelScopeKind
from solara_travel.ports.discovery import DestinationCandidateProposalPort
from solara_travel.ports.errors import ProviderError
from solara_travel.ports.places import (
    DestinationResolutionPort,
    PlacesProvider,
    TravelScopeResolutionPort,
)
from solara_travel.ports.weather import HistoricalWeatherProvider


@dataclass(frozen=True, slots=True)
class RecommendationPlan:
    """Prepared geographic candidates before evidence and scoring."""

    request: RecommendationRequest
    candidates: tuple[Destination, ...] | None
    travel_scope: TravelScope | None = None
    destination_mode: str = "discovery"

    def __post_init__(self) -> None:
        if not isinstance(self.request, RecommendationRequest):
            raise TypeError("request must be RecommendationRequest")
        if self.candidates is not None:
            if not isinstance(self.candidates, tuple):
                raise TypeError("candidates must be a tuple or None")
            if not all(isinstance(candidate, Destination) for candidate in self.candidates):
                raise TypeError("candidates must contain Destination values")
        if self.travel_scope is not None and not isinstance(self.travel_scope, TravelScope):
            raise TypeError("travel_scope must be TravelScope or None")
        if self.candidates is None and self.destination_mode not in {
            "discovery",
            "scope_discovery",
        }:
            raise ValueError("candidate proposal is only valid for discovery modes")

    @property
    def requires_candidate_proposal(self) -> bool:
        """Return whether this plan needs one bounded AI proposal call."""

        return self.candidates is None


@dataclass(frozen=True, slots=True)
class RecommendationService:
    """Coordinate providers and deterministic analytics into ranked results."""

    places_provider: PlacesProvider
    weather_provider: HistoricalWeatherProvider
    historical_period: TravelPeriod
    comfort_range: TemperatureComfortRange
    seasonal_weight: float = 1.0
    scope_resolver: TravelScopeResolutionPort | None = None
    candidate_proposal_provider: DestinationCandidateProposalPort | None = None
    maximum_candidates: int = 5

    def __post_init__(self) -> None:
        """Validate application-service dependencies and explicit policy values."""

        if not isinstance(self.places_provider, PlacesProvider):
            raise TypeError("places_provider must satisfy PlacesProvider")

        if not isinstance(self.weather_provider, HistoricalWeatherProvider):
            raise TypeError("weather_provider must satisfy HistoricalWeatherProvider")

        if not isinstance(self.historical_period, TravelPeriod):
            raise TypeError("historical_period must be a TravelPeriod")

        if not isinstance(self.comfort_range, TemperatureComfortRange):
            raise TypeError("comfort_range must be a TemperatureComfortRange")

        # Reuse generic scoring validation rather than duplicating numeric rules.
        SuitabilityScore(
            (
                ScoreComponent(
                    name="seasonal_temperature_comfort",
                    score=1.0,
                    weight=self.seasonal_weight,
                ),
            )
        )
        if self.scope_resolver is not None and not isinstance(
            self.scope_resolver, TravelScopeResolutionPort
        ):
            raise TypeError("scope_resolver must satisfy TravelScopeResolutionPort or be None")
        if self.candidate_proposal_provider is not None and not isinstance(
            self.candidate_proposal_provider, DestinationCandidateProposalPort
        ):
            raise TypeError(
                "candidate_proposal_provider must satisfy "
                "DestinationCandidateProposalPort or be None"
            )
        if type(self.maximum_candidates) is not int:
            raise TypeError("maximum_candidates must be an int")
        if not 1 <= self.maximum_candidates <= 5:
            raise ValueError("maximum_candidates must be between 1 and 5")

    def recommend(self, request: RecommendationRequest) -> RecommendationResult:
        """Return deterministic recommendations for one validated request."""

        if not isinstance(request, RecommendationRequest):
            raise TypeError("request must be a RecommendationRequest")

        return self.recommend_plan(self.prepare(request))

    def prepare(self, request: RecommendationRequest) -> RecommendationPlan:
        """Resolve traveller geography without invoking candidate-proposal AI."""

        if not isinstance(request, RecommendationRequest):
            raise TypeError("request must be a RecommendationRequest")

        if request.destination is not None:
            return RecommendationPlan(
                request, (request.destination,), destination_mode="pre_resolved"
            )

        if request.destination_queries:
            resolver = self._scope_resolution_port()
            if resolver is not None:
                resolved_scopes: list[TravelScope] = []
                for query in request.destination_queries:
                    scope = self._resolve_scope(resolver, query)
                    if (
                        scope.kind is not TravelScopeKind.LOCALITY
                        and len(request.destination_queries) != 1
                    ):
                        raise BroadScopeCombinationError(
                            "choose one country or region, or compare individual localities"
                        )
                    resolved_scopes.append(scope)
                scopes = tuple(resolved_scopes)
                broad_scopes = tuple(
                    scope for scope in scopes if scope.kind is not TravelScopeKind.LOCALITY
                )
                if broad_scopes:
                    self._require_candidate_proposal_provider()
                    return RecommendationPlan(
                        request,
                        None,
                        travel_scope=broad_scopes[0],
                        destination_mode="scope_discovery",
                    )
                return RecommendationPlan(
                    request,
                    self._deduplicate_destinations(
                        tuple(scope.to_destination() for scope in scopes)
                    ),
                    destination_mode="explicit_queries",
                )
            return RecommendationPlan(
                request,
                self._resolve_legacy_destinations(request),
                destination_mode="explicit_queries",
            )

        if self.candidate_proposal_provider is not None:
            if self._scope_resolution_port() is None:
                raise TypeError("candidate discovery requires TravelScopeResolutionPort")
            return RecommendationPlan(request, None, destination_mode="discovery")

        candidates = self.places_provider.discover_destinations(request)
        if not isinstance(candidates, tuple):
            raise TypeError("destination provider must return a tuple")
        if not all(isinstance(candidate, Destination) for candidate in candidates):
            raise TypeError("destination provider must return Destination values")
        return RecommendationPlan(request, candidates, destination_mode="discovery")

    def recommend_plan(self, plan: RecommendationPlan) -> RecommendationResult:
        """Gather evidence and deterministically rank one prepared plan."""

        if not isinstance(plan, RecommendationPlan):
            raise TypeError("plan must be RecommendationPlan")
        request = plan.request
        candidates = (
            self._propose_and_validate_candidates(request, plan.travel_scope)
            if plan.requires_candidate_proposal
            else plan.candidates
        )
        assert candidates is not None
        recommendations = tuple(
            self._recommend_destination(destination, request) for destination in candidates
        )
        ranked = tuple(
            sorted(
                recommendations,
                key=lambda recommendation: recommendation.score,
                reverse=True,
            )
        )
        return RecommendationResult(
            request=request,
            recommendations=ranked,
            destination_mode=plan.destination_mode,
            travel_scope=plan.travel_scope,
        )

    def _scope_resolution_port(self) -> TravelScopeResolutionPort | None:
        if self.scope_resolver is not None:
            return self.scope_resolver
        if isinstance(self.places_provider, TravelScopeResolutionPort):
            return self.places_provider
        return None

    @staticmethod
    def _resolve_scope(
        resolver: TravelScopeResolutionPort,
        query: DestinationQuery,
    ) -> TravelScope:
        scope = resolver.resolve_travel_scope(query)
        if scope is None:
            raise DestinationNotFoundError(query)
        if not isinstance(scope, TravelScope):
            raise TypeError("travel scope resolver must return TravelScope or None")
        return scope

    def _resolve_legacy_destinations(
        self,
        request: RecommendationRequest,
    ) -> tuple[Destination, ...]:
        if not isinstance(self.places_provider, DestinationResolutionPort):
            raise TypeError(
                "places_provider must satisfy DestinationResolutionPort for explicit queries"
            )
        resolved: list[Destination] = []
        for query in request.destination_queries:
            destination = self.places_provider.resolve_destination(query)
            if destination is None:
                raise DestinationNotFoundError(query)
            if not isinstance(destination, Destination):
                raise TypeError("destination resolver must return Destination or None")
            resolved.append(destination)
        return self._deduplicate_destinations(tuple(resolved))

    def _propose_and_validate_candidates(
        self,
        request: RecommendationRequest,
        broad_scope: TravelScope | None,
    ) -> tuple[Destination, ...]:
        provider = self._require_candidate_proposal_provider()
        resolver = self._scope_resolution_port()
        if resolver is None:
            raise TypeError("candidate discovery requires TravelScopeResolutionPort")
        try:
            proposal = provider.propose_candidates(request, broad_scope)
        except ProviderError as exc:
            raise DestinationDiscoveryUnavailableError(
                "candidate proposal provider failed"
            ) from exc
        candidates: list[Destination] = []
        seen: set[tuple[str, str]] = set()
        for proposed_name in proposal.candidate_localities:
            query_text = self._qualified_candidate_query(proposed_name, broad_scope)
            try:
                candidate_scope = resolver.resolve_travel_scope(DestinationQuery(query_text))
            except (TypeError, ValueError, ProviderError):
                continue
            if candidate_scope is None or candidate_scope.kind is not TravelScopeKind.LOCALITY:
                continue
            if broad_scope is not None and not broad_scope.contains(candidate_scope):
                continue
            destination = candidate_scope.to_destination()
            identity = (destination.name.casefold(), destination.country.casefold())
            if identity in seen:
                continue
            candidates.append(destination)
            seen.add(identity)
            if len(candidates) == self.maximum_candidates:
                break
        return tuple(candidates)

    def _require_candidate_proposal_provider(self) -> DestinationCandidateProposalPort:
        provider = self.candidate_proposal_provider
        if provider is None:
            raise DestinationDiscoveryUnavailableError(
                "candidate proposal provider is not configured"
            )
        return provider

    @staticmethod
    def _qualified_candidate_query(name: str, scope: TravelScope | None) -> str:
        query = name.strip()
        if scope is not None:
            qualifier = scope.display_name
            if qualifier.casefold() not in query.casefold():
                query = f"{query}, {qualifier}"
        return query[:DESTINATION_QUERY_MAX_LENGTH].rstrip(" ,")

    @staticmethod
    def _deduplicate_destinations(
        destinations: tuple[Destination, ...],
    ) -> tuple[Destination, ...]:
        unique: list[Destination] = []
        seen: set[tuple[str, str]] = set()
        for destination in destinations:
            identity = (destination.name.casefold(), destination.country.casefold())
            if identity not in seen:
                unique.append(destination)
                seen.add(identity)
        return tuple(unique)

    def _recommend_destination(
        self,
        destination: Destination,
        request: RecommendationRequest,
    ) -> DestinationRecommendation:
        """Collect evidence and build one deterministic destination result."""

        attractions = self.places_provider.discover_attractions(destination)
        observations = self.weather_provider.get_historical_weather(
            destination,
            self.historical_period,
        )
        profile = build_seasonal_weather_profile(
            observations,
            request.travel_period,
        )
        comfort = assess_seasonal_temperature_comfort(
            profile,
            self.comfort_range,
        )
        seasonal_component = seasonal_temperature_comfort_score_component(
            comfort,
            self.seasonal_weight,
        )
        evidence = RecommendationEvidence(
            attractions=attractions,
            seasonal_weather=profile,
            seasonal_temperature_comfort=comfort,
        )
        return DestinationRecommendation(
            destination=destination,
            suitability=SuitabilityScore((seasonal_component,)),
            evidence=evidence,
        )
