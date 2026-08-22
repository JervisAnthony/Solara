# Solara Roadmap

## Purpose

This roadmap describes the planned sequence for rebuilding Solara from its clean
engineering foundation into a usable, explainable travel-intelligence platform.

The roadmap is directional rather than a fixed promise of release dates.

Each milestone should remain:

- independently understandable;
- testable;
- reviewable;
- small enough to evolve when implementation reveals better design choices.

The roadmap should guide development without becoming a constraint that forces
Solara to preserve outdated assumptions.

## Current state

Solara has completed its engineering re-foundation.

The active codebase currently provides:

- a modern Python package;
- a `src` package layout;
- Python 3.11 through Python 3.13 support;
- pytest-based testing;
- coverage tooling;
- Ruff static analysis;
- package build support;
- GitHub Actions CI;
- a protected pull-request workflow;
- foundational product and architecture documentation.

The original prototype implementation has intentionally not been carried into
the active architecture.

Useful concepts from the prototype may return only after they are redesigned
within the new domain, application, provider, analytics, and testing boundaries.

## Development strategy

The rebuild should progress from the most stable and provider-independent
concepts toward external integrations and user-facing experiences.

The preferred dependency order is:

```text
Domain
  |
  v
Traveller and trip context
  |
  v
Provider contracts
  |
  v
Deterministic analytics
  |
  v
Provider implementations
  |
  v
Application services
  |
  v
Offline workflow
  |
  v
Optional orchestration
  |
  v
AI-assisted narration
  |
  v
Presentation layers
```

This ordering ensures that external services and AI models are added around a
working recommendation core rather than becoming the core itself.

## Phase 1 - Core travel domain

### Goal

Introduce the first provider-independent travel concepts.

### Expected capabilities

The domain may include:

- geographic coordinates;
- destinations;
- attractions;
- travel periods;
- normalized weather observations;
- basic categories and identifiers.

### Engineering focus

This phase should establish:

- immutable or well-defined value semantics where appropriate;
- meaningful validation;
- clear invariants;
- provider-independent terminology;
- focused domain tests.

External providers must not be introduced merely to populate the models.

### Completion criteria

This phase is complete when Solara can represent its first meaningful travel
entities without:

- API keys;
- provider SDKs;
- network access;
- AI dependencies.

## Phase 2 - Traveller preferences and trip context

### Goal

Represent the traveller and the circumstances of a recommendation request.

### Potential concepts

Initial concepts may include:

- traveller interests;
- trip style;
- preferred pace;
- climate preference;
- crowd tolerance;
- indoor versus outdoor preference;
- trip duration;
- budget context;
- travel month or date range;
- group type.

Only concepts required by real recommendation behaviour should be implemented.

### Recommendation request

This phase should establish a structured recommendation request that can
eventually express questions such as:

```text
Where should I travel in November for seven days if I prefer mild weather,
history, local food, moderate crowds, and a medium budget?
```

The request should remain a domain or application concept rather than an
unstructured prompt sent directly to an LLM.

### Completion criteria

Solara should be able to validate and represent a traveller's request
deterministically.

## Phase 3 - Provider contracts

### Goal

Define Solara-owned interfaces for external capabilities before implementing
specific providers.

### Initial candidate ports

Potential contracts include:

```text
PlacesProvider
WeatherProvider
GeocodingProvider
```

Later contracts may include:

```text
NarrationProvider
TripRepository
Cache
```

only when required.

### Engineering focus

Provider contracts should:

- express Solara's needs;
- return Solara-owned representations;
- avoid vendor-specific data structures;
- support fake implementations;
- remain small and focused.

### Completion criteria

Application code should be able to depend on provider abstractions without
knowing which external service will eventually implement them.

## Phase 4 - Deterministic popularity and suitability analytics

### Goal

Build the first explainable recommendation calculations.

### Initial analytics

Potential capabilities include:

- popularity normalization;
- interest matching;
- category suitability;
- preference weighting;
- score composition;
- ranking.

The original prototype's popularity normalization concept may be revisited, but
its previous implementation should not be copied automatically.

### Explainability requirement

A recommendation score should expose components such as:

```text
overall suitability
├── popularity
├── interest match
├── climate comfort
└── seasonal suitability
```

rather than produce only a final opaque number.

### Completion criteria

A deterministic set of candidate destinations or attractions should be rankable
using local test data.

## Phase 5 - Weather intelligence and climate comfort

### Goal

Introduce travel-oriented weather reasoning without yet depending on live
weather services.

### Potential capabilities

This phase may include:

- temperature comfort;
- precipitation preference;
- seasonal climate observations;
- weather suitability;
- traveller climate tolerance;
- normalized climate metrics.

Historical climate and real-time weather should remain conceptually distinct.

### Engineering focus

The first implementation should use deterministic models and fixtures.

Provider integration should follow only after the desired domain behaviour is
clear.

### Completion criteria

Solara should be able to explain how climate conditions affect suitability for a
traveller.

## Phase 6 - Places integration

### Goal

Introduce the first real external places provider.

### Responsibilities

The infrastructure adapter should handle:

- provider authentication;
- place discovery;
- response parsing;
- category normalization;
- identifier mapping;
- error translation.

Provider-specific response objects must stop at the infrastructure boundary.

### Provider independence

The application should request concepts such as:

```text
find attractions near this destination
```

rather than expose provider-specific request syntax.

### Completion criteria

The real provider should be replaceable by a fake implementation without
changing recommendation logic.

## Phase 7 - Weather provider integration

### Goal

Connect deterministic climate and weather reasoning to normalized external data.

### Responsibilities

The provider adapter may handle:

- weather or climate lookup;
- date normalization;
- units;
- missing observations;
- provider failures;
- response normalization.

The analytics layer should continue to reason over Solara-owned weather models.

### Completion criteria

Switching the weather provider should not require changing core climate
suitability algorithms.

## Phase 8 - Seasonality intelligence

### Goal

Develop explicit season-aware travel reasoning.

### Potential factors

Seasonality may eventually consider:

- climate comfort;
- rainfall;
- temperature;
- daylight;
- crowds;
- destination season;
- activity availability;
- traveller tolerance.

Not every factor must be introduced at once.

### Engineering focus

Seasonality should be calculated from explicit evidence.

Avoid fixed placeholder values such as a universal seasonal score.

### Completion criteria

Solara should be able to explain why a destination becomes more or less suitable
during a particular travel period.

## Phase 9 - Recommendation application service

### Goal

Coordinate the completed domain, providers, and analytics into a meaningful
recommendation use case.

### Conceptual flow

```text
RecommendationRequest
        |
        v
Validate request
        |
        v
Discover candidates
        |
        v
Gather provider evidence
        |
        v
Calculate suitability
        |
        v
Rank candidates
        |
        v
Assemble recommendation results
```

### Responsibilities

The application service should coordinate:

- request validation;
- candidate discovery;
- provider calls;
- deterministic analytics;
- ranking;
- evidence collection;
- result construction.

It should not implement vendor-specific logic.

### Completion criteria

The service must be fully testable using fake providers with no network access.

## Phase 10 - Offline recommendation workflow

### Goal

Provide an end-to-end deterministic demonstration of Solara without requiring
external services.

### Offline data

Local fixtures may represent:

- destinations;
- attractions;
- climate observations;
- traveller preferences.

### Why this milestone matters

An offline workflow provides:

- deterministic regression testing;
- reproducible demonstrations;
- portfolio-ready behaviour;
- resilience against API availability;
- a stable foundation for later orchestration.

### Completion criteria

A user or developer should be able to run a meaningful recommendation flow
without:

- an API key;
- internet access;
- an LLM.

## Phase 11 - Workflow orchestration

### Goal

Evaluate whether graph-based orchestration improves the recommendation workflow.

LangGraph may be introduced here if it provides clear value.

### Potential workflow

```text
validate_request
      |
discover_candidates
      |
collect_evidence
      |
score_candidates
      |
rank_results
      |
optional_narration
      |
return_result
```

### Constraints

LangGraph must not own:

- domain models;
- scoring logic;
- provider contracts;
- provider normalization;
- recommendation policy.

The application service should exist before LangGraph is introduced.

### Completion criteria

Orchestration should simplify workflow composition without increasing coupling
to framework-specific state.

## Phase 12 - AI-assisted recommendation explanations

### Goal

Add optional generative explanations on top of grounded deterministic results.

### Potential capabilities

AI may generate:

- recommendation summaries;
- traveller-friendly explanations;
- strengths and trade-offs;
- itinerary prose;
- conversational responses.

### Grounding requirement

The AI layer should consume structured evidence such as:

```text
Destination: Kyoto
Suitability: 0.86
Climate comfort: 0.82
Interest match: 0.95
Seasonal suitability: 0.84
Trade-off: high visitor density
```

and transform it into useful natural language.

It should not invent the underlying ranking.

### Completion criteria

Disabling the AI provider should still leave a complete deterministic
recommendation result.

## Phase 13 - Command-line demonstration

### Goal

Provide a simple developer and portfolio-facing interface for exercising the
recommendation system.

### Potential capabilities

A CLI may accept:

- destination region;
- travel period;
- interests;
- climate preference;
- duration.

It may return:

- ranked recommendations;
- component scores;
- explanation evidence;
- optional generated narrative.

### Completion criteria

Solara should be demonstrable end-to-end from the terminal.

## Phase 14 - FastAPI foundation

### Goal

Introduce an HTTP presentation layer after recommendation behaviour has
stabilized.

### Initial API capabilities

Potential endpoints include:

```text
GET /health
```

Additional endpoints should be introduced only when real use cases require them.

### Architectural constraint

FastAPI should translate HTTP requests into application inputs.

It should not become the recommendation engine.

### Completion criteria

Application behaviour should remain identical whether invoked through tests,
the CLI, or the API.

## Phase 15 - Recommendation API

### Goal

Expose the structured recommendation workflow through a stable API contract.

The implemented public route is `POST /api/v1/recommendations`. It uses typed
presentation request and response models, explicit HTTP/domain mapping, and
application-service injection. Responses preserve deterministic ranking,
scores, components, and selected aggregate evidence while optional grounded
narration remains non-authoritative. Known provider failures are translated at
the HTTP boundary without exposing provider details.

### Potential response

A response may eventually include:

```text
recommendations
├── destination
├── suitability score
├── scoring components
├── supporting observations
├── trade-offs
├── assumptions
├── missing-data notices
└── optional narrative
```

### Completion criteria

External clients should be able to obtain explainable recommendations without
depending on internal implementation details.

## Phase 16 - Product experience

### Goal

Develop user-facing interfaces around proven application workflows.

Potential directions include:

- web application;
- desktop application;
- interactive trip discovery;
- map-based exploration;
- saved recommendations;
- traveller profiles.

The user-interface technology should be selected based on concrete product
requirements rather than chosen prematurely.

## Phase 17 - Itinerary intelligence

### Goal

Extend recommendations into practical trip planning.

Potential capabilities include:

- multi-day itinerary organization;
- attraction grouping;
- pace-aware planning;
- opening-hour constraints;
- travel-time awareness;
- indoor and outdoor balance;
- alternative activities;
- rest periods;
- traveller priorities.

The itinerary engine should build on existing domain and recommendation
contracts rather than bypass them.

## Phase 18 - Budget intelligence

### Goal

Make cost an explicit recommendation factor.

Potential inputs may include:

- traveller budget;
- trip duration;
- accommodation level;
- activity preferences;
- transport assumptions.

Potential outputs may include:

- approximate budget suitability;
- relative destination affordability;
- cost trade-offs;
- budget warnings.

Price information must be treated as time-sensitive evidence where appropriate.

Solara should not present estimates as guaranteed prices.

## Phase 19 - Advanced traveller profiles

### Goal

Support persistent traveller preferences when durable state becomes useful.

Potential profile information may include:

- interests;
- climate preferences;
- travel pace;
- crowd tolerance;
- budget style;
- preferred activities;
- accessibility requirements;
- previous destination feedback.

Persistence should be introduced behind application-facing repository
interfaces.

## Phase 20 - Rich travel intelligence

Potential later capabilities include:

- multi-city recommendation;
- alternative destination comparison;
- travel-time-aware routing;
- accommodation comparisons;
- transport recommendations;
- destination similarity;
- collaborative planning;
- sustainable-travel preferences;
- accessibility-focused recommendations;
- multilingual assistance.

These capabilities are future possibilities rather than commitments to the
initial product.

## Operational maturity

Production infrastructure should be introduced as actual usage requires it.

Potential capabilities include:

- structured logging;
- observability;
- provider latency monitoring;
- retries;
- caching;
- rate-limit handling;
- persistent storage;
- secure secret management;
- deployment environments;
- performance testing;
- application health monitoring.

Infrastructure should follow demonstrated operational needs.

## Caching roadmap

Caching may eventually be useful for:

- geocoding results;
- attraction discovery;
- climate data;
- provider metadata;
- expensive AI narration.

Caching should not be introduced before provider behaviour demonstrates a
meaningful performance, reliability, or cost benefit.

## Persistence roadmap

Persistent storage may eventually support:

- saved traveller profiles;
- saved trips;
- recommendation history;
- favourites;
- itinerary drafts;
- collaborative trips.

The choice of database should be made after the required access patterns are
understood.

## AI roadmap

AI capabilities should be introduced progressively.

Potential future uses include:

```text
grounded recommendation narration
             |
             v
conversational recommendation interface
             |
             v
itinerary explanation
             |
             v
context-aware travel assistance
```

More complex AI architecture should only be introduced if simple grounded model
calls become insufficient.

Grounded narration is required for the intended hosted MVP1 experience, while
deterministic recommendations must remain complete and usable when narration
fails. LangGraph is not a prerequisite for grounded narration and should be
introduced only if demonstrated orchestration complexity later justifies it.

## Agentic architecture

Solara does not initially require a multi-agent architecture.

Agentic workflows may be considered later if the product develops genuinely
independent decision-making capabilities that benefit from separate tools,
state, and responsibilities.

The existence of LangGraph or other agent frameworks is not itself a reason to
create agents.

## Retrieval-augmented generation

A vector database or RAG pipeline is not required for the initial
recommendation system.

RAG may become useful in the future for grounded access to information such as:

- destination guides;
- travel documentation;
- curated local knowledge;
- traveller notes;
- structured trip resources.

It should be introduced only when retrieval over a meaningful corpus solves a
demonstrated problem.

## Deliberately deferred technologies

Solara should not introduce the following by default:

- vector databases;
- multi-agent systems;
- microservices;
- message queues;
- Kubernetes;
- distributed event systems;
- complex persistence infrastructure;
- service meshes;
- event streaming platforms.

These remain architectural options rather than predefined requirements.

## Near-term commit sequence

The current intended sequence after the documentation milestone is:

```text
Commit 23 - core travel domain models
Commit 24 - traveller preferences and recommendation requests
Commit 25 - provider contracts
Commit 26 - deterministic popularity and suitability analytics
Commit 27 - weather intelligence and climate comfort
Commit 28 - places provider and normalization
Commit 29 - historical weather provider and normalization
Commit 30 - seasonality intelligence
Commit 31 - recommendation result and evidence models
Commit 32 - recommendation application service
Commit 33 - CI hardening and repository quality gates
Commit 34 - offline providers and end-to-end recommendation workflow
Commit 35 - grounded AI narration
Commit 36 - FastAPI application foundation
Commit 37 - recommendation HTTP API
Commit 38 - web application shell
Commit 39 - traveller recommendation form
Commit 40 - recommendation results and explainability UI
Commit 41 - validation, error, loading, and empty states
Commit 42 - logging, request tracing, and tester feedback
Commit 43 - premium UI/GUI redesign
Commit 44 - public-alpha safeguards and rate and cost controls
Commit 45 - deployment configuration
Commit 46 - hosted MVP1 deployment
Commit 47 - public-alpha integration, smoke, and browser testing
Commit 48 - MVP1 release documentation
```

This sequence is intentionally more granular than the original prototype.

Each commit should establish one architectural capability cleanly before the
next layer depends on it.

The sequence may change if implementation reveals a better dependency order.

Roadmap changes are acceptable when they improve architecture, product value, or
development clarity.

## Commit 23 - Core travel domain models

The next implementation milestone should introduce Solara's first real domain
objects.

Expected scope may include:

- geographic coordinates;
- destination;
- attraction;
- travel period;
- normalized domain validation.

The exact scope should be finalized when Commit 23 begins.

This commit should remain:

- provider-independent;
- framework-independent;
- network-independent;
- test-first.

## Commit 24 - Traveller preferences and recommendation requests

Expected scope may include:

- traveller interests;
- travel style;
- trip duration;
- climate preferences;
- recommendation request;
- validation and invariants.

## Commit 25 - Provider contracts

Expected scope may include:

- places-provider interface;
- weather-provider interface;
- normalized provider-facing inputs and outputs;
- fake implementations for tests where useful.

No real external provider is required merely to establish the contracts.

## Commit 26 - Deterministic popularity and suitability analytics

Expected scope may include:

- bounded normalization;
- deterministic component scores;
- scoring configuration;
- explainable score composition;
- edge-case tests.

## Commit 27 - Weather intelligence and climate comfort

Expected scope may include:

- climate comfort calculation;
- traveller weather preferences;
- temperature and precipitation suitability;
- deterministic fixture-based tests.

## Commit 28 - Places provider and normalization

Expected scope may include:

- concrete places infrastructure;
- external response mapping;
- provider error translation;
- attraction normalization.

## Commit 29 - Seasonality intelligence

Expected scope may include:

- seasonal suitability;
- travel-period comparison;
- climate contribution;
- explicit component explanation.

## Commit 30 - Recommendation application service

Expected scope may include:

- candidate orchestration;
- provider collaboration;
- analytics invocation;
- ranking;
- recommendation result assembly.

## Commit 31 - Recommendation result and evidence models

Expected scope may include:

- immutable recommendation values;
- deterministic result ordering;
- retained score and provider evidence;
- result invariant tests.

## Commit 32 - Recommendation application service

Expected scope may include:

- candidate orchestration;
- provider collaboration;
- analytics invocation;
- deterministic ranking and result assembly.

## Commit 33 - CI hardening and repository quality gates

Expected scope may include:

- multi-version Python validation;
- 100% statement and branch coverage gates;
- package installation validation;
- security and dependency review workflows.

## Commit 34 - Offline providers and end-to-end recommendation workflow

Expected scope may include:

- explicit credential-free provider composition;
- bundled synthetic fixture evidence;
- end-to-end deterministic recommendation execution;
- no silent fallback from live providers.

## Commit 35 - Grounded AI narration

Expected scope may include:

- narration port;
- deterministic grounded prompt construction;
- OpenAI Responses API infrastructure;
- result-preserving provider failure fallback.

Narration is part of the intended MVP1 experience but remains enrichment: AI
does not own recommendation logic, and deterministic results remain usable when
narration is unavailable. LangGraph is not required for this milestone.

## Commit 36 - FastAPI application foundation

Expected scope may include:

- optional FastAPI web dependencies;
- application factory and ASGI entrypoint;
- typed process-health endpoint and standard API documentation;
- presentation-layer tests without provider composition.

Recommendation request and response HTTP behavior remains Commit 37 scope.

## Commit 37 - Recommendation HTTP API

Implemented scope includes:

- versioned `POST /api/v1/recommendations` route;
- typed request and response schemas with explicit domain mapping;
- per-application `RecommendationService` and optional narration injection;
- deterministic evidence serialization without raw provider payloads;
- safe provider-boundary error translation and optional narration degradation.

## Commit 38 - Web application shell

Implemented scope includes:

- browser-facing `GET /` route outside the OpenAPI contract;
- semantic, accessible application shell with stable future-workspace anchors;
- responsive sunlight-inspired visual foundation;
- packaged local HTML and CSS with no external frontend dependency;
- credential-free rendering independent of recommendation composition;
- focused browser-shell, static-asset, and API-regression tests.

Commit 39 extends this shell with recommendation inputs and submission; Commit
40 adds authoritative result rendering.

## Commit 39 - Traveller recommendation form

Implemented scope includes:

- one accessible traveller input form;
- required start-date and end-date inputs;
- optional free-text interests, pace, and climate inputs;
- exact JSON recommendation-request construction in destination-discovery mode;
- same-origin submission to `POST /api/v1/recommendations`;
- packaged, dependency-free browser JavaScript;
- minimal success and failure acknowledgement;
- no recommendation-result rendering.

## Commit 40 - Recommendation results and explainability UI

Implemented scope includes:

- authoritative ranked destination cards and suitability scores;
- deterministic score components without browser recomputation;
- selected attraction evidence;
- historical seasonal and temperature-comfort evidence;
- optional grounded AI explanation kept separate from deterministic ranking;
- safe plain-text rendering of response content;
- repeated-response replacement with no reranking or rescoring;
- no loading, detailed error, or empty-result UX.

## Commit 41 - Validation, error, loading, and empty states

Implemented scope includes:

- accessible validation summary and field-level feedback;
- required-date, date-order, malformed-interest, and duplicate-interest checks;
- request busy state with a disabled action and duplicate-submit guard;
- stable HTTP error interpretation with safe `422`, `502`, `503`, unexpected,
  and network-failure presentation;
- manual retry for transient failures through the normal form submission path;
- successful empty-result presentation without fabricated recommendations;
- accessible focus transitions for validation, results, empty, and error states;
- result clearing only after a locally valid request actually begins;
- no request tracing or tester feedback before Commit 42.

## Commit 42 - Logging, request tracing, and tester feedback

Implemented scope includes:

- fresh server-generated UUID4 identifiers for every handled HTTP request;
- `X-Request-ID` response tracing with untrusted inbound IDs ignored;
- versioned one-line structured JSON request events and monotonic durations;
- safe aggregate recommendation completion, rejection, failure, deterministic
  timing, and optional narration timing events;
- tester-visible opaque request references held only in transient DOM state;
- typed `POST /api/v1/feedback` with `202 Accepted` receipts;
- required helpful, mixed, or not-helpful ratings and optional bounded comments;
- optional linkage to the recommendation request being discussed;
- distinct feedback receipt, feedback HTTP request, and recommendation request
  UUIDs in the structured feedback event;
- log-backed public-alpha feedback recording with no database or file sink;
- packaged accessible browser feedback UI and same-origin `feedback.js`;
- privacy boundaries that exclude travel bodies, response bodies, client
  metadata, raw provider failures, and narration content from operational logs;
- no rate limiting, quotas, abuse safeguards, cost controls, or deployment
  configuration yet.

## Commit 43 - Premium UI/GUI redesign

Implemented scope includes:

- approved horizontal, stacked, icon-only, and monochrome Solara brand assets
  stored and served as nested package-managed static resources;
- premium ivory, forest, sand, amber, and muted-gold visual system using local
  system typography and no external frontend dependency;
- redesigned branded header, season-smart hero, supporting insight card,
  integrated traveller planner, curated results presentation, tester-feedback
  panel, product-principle section, and footer;
- responsive layouts, visible keyboard focus, touch-friendly controls, semantic
  headings, accessible status regions, and reduced-motion behavior;
- preserved validation, loading, success, empty, error, retry, result rendering,
  narration, request-reference, and feedback-submission behavior;
- unchanged recommendation and feedback API contracts, provider orchestration,
  deterministic ranking, scoring, observability, and privacy boundaries;
- no fabricated recommendations, external assets, persistence, authentication,
  rate limiting, cost controls, deployment configuration, or hosting work.

## Commit 44 - Public-alpha safeguards and rate and cost controls

Implemented scope includes:

- immutable positive-integer policy for recommendation rate, longer usage,
  concurrency, narration-attempt, and feedback-rate guardrails;
- fresh identity-free process-local state for every application instance;
- atomic recommendation admission with exception-safe concurrency release;
- safe Solara-owned `429` codes, integer `Retry-After`, request tracing, and
  privacy-conscious rejection events;
- narration-budget degradation to the unchanged deterministic `200` result;
- accessible browser recommendation and feedback cooldowns with fixed local
  copy, preserved input, no persistence, and no automatic retry;
- deterministic fake-clock and synchronization-based tests with no sleeps;
- no IP-based limiting, accounts, distributed limiter, new dependency,
  deployment configuration, or guaranteed financial ceiling.

## Commit 45 - Deployment configuration

Implemented scope includes:

- immutable framework-independent settings and explicit environment parsing;
- required Google Places and OpenAI configuration with safe aggregate startup
  errors and secret-free reprs;
- one fresh live-provider dependency graph per hosted application, with no
  provider calls during startup;
- a dedicated environment-driven FastAPI factory that preserves the ordinary
  credential-free application factory;
- a one-worker Uvicorn entrypoint with access logs and proxy-header trust
  disabled;
- a non-root Python 3.13 slim Docker image, health check, secret-protecting
  Docker context, safe environment template, and CI container smoke gate;
- deployment, architecture, and development documentation;
- no hosting account, public URL, production deployment, distributed limiter,
  or change to recommendation ranking.

## Commits 46-48 - MVP1 deployment and release

The remaining MVP1 sequence is exactly:

- Commit 46 - hosted MVP1 deployment;
- Commit 47 - public-alpha integration, smoke, and browser testing;
- Commit 48 - MVP1 release documentation.

## Release milestones

### Foundation milestone

A clean package, engineering workflow, documentation, and CI.

### Domain milestone

Provider-independent travel and traveller concepts with tested invariants.

### Core intelligence milestone

Deterministic, explainable suitability scoring operating entirely offline.

### Integration milestone

Real provider adapters coordinated through stable ports.

### Recommendation milestone

End-to-end application-level recommendation workflows.

### AI-assisted milestone

Grounded natural-language explanation layered over deterministic recommendations.

### Application milestone

A stable API and user-facing experience for end-to-end travel intelligence.

## Quality gates

Each roadmap milestone should preserve the following expectations:

- tests remain deterministic;
- the default suite requires no external credentials;
- Ruff passes;
- provider coupling remains outside the domain;
- recommendation scoring remains explainable;
- AI remains optional to deterministic recommendation behaviour;
- documentation reflects the actual implementation state;
- pull requests remain small enough for meaningful review.

## Architecture review points

The roadmap should include deliberate opportunities to reassess architecture.

A review is appropriate when:

- several new layers have accumulated;
- provider contracts prove awkward;
- scoring logic becomes difficult to explain;
- orchestration complexity grows;
- persistence becomes necessary;
- a user-facing application begins to impose new requirements.

Architecture should evolve through evidence gathered from implementation rather
than speculation made at project inception.

## What success looks like

A meaningful Solara release should eventually allow a traveller to provide
structured preferences and trip context and receive recommendations that are:

- relevant;
- season-aware;
- preference-aware;
- explainable;
- grounded in identifiable evidence;
- explicit about trade-offs;
- resilient to missing optional services.

A user should be able to understand not only **what** Solara recommends, but
also **why** it recommends it.

## Guiding principle

Solara should become sophisticated because traveller needs require
sophistication, not because sophisticated technology is available.

Every new framework, provider, model, service, database, workflow, or
abstraction should solve a concrete problem and fit within the architecture
already established.
