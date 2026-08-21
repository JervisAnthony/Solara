# Solara Architecture

## Purpose

This document defines the architectural direction for Solara as the project is
rebuilt from its original prototype.

Solara is intended to become a season-smart, preference-aware, and explainable
travel-intelligence platform. Its architecture must therefore support both
deterministic travel reasoning and optional AI-assisted experiences without
allowing external providers, frameworks, or language models to become the core
of the product.

The architecture is designed to keep travel-domain reasoning independent from:

- external APIs;
- AI model providers;
- persistence technologies;
- orchestration frameworks;
- presentation frameworks;
- deployment infrastructure.

The design should remain appropriately simple for the current product while
providing clear boundaries for future growth.

## Architectural goals

Solara should:

- keep core travel concepts independent of external APIs;
- make deterministic recommendation behaviour easy to test;
- isolate provider-specific data structures and failures;
- allow weather, places, mapping, and AI providers to be replaced;
- allow useful recommendation behaviour without network access;
- separate recommendation computation from recommendation narration;
- expose the factors and evidence behind rankings;
- distinguish evidence from assumptions and generated prose;
- avoid framework-driven domain design;
- support graceful degradation when optional services are unavailable;
- grow incrementally rather than through speculative abstractions.

## Architectural style

Solara will follow a layered, ports-and-adapters-inspired architecture.

The core system owns its domain language and application behaviour.

External systems are treated as replaceable implementation details.

The intended high-level flow is:

```text
User / External Client
        |
        v
Presentation
        |
        v
Application
   |         |
   v         v
Domain    Analytics
   ^
   |
 Ports
   ^
   |
Infrastructure
```

Workflow orchestration may coordinate application services where useful, but it
must not become the owner of domain behaviour.

## Target package structure

The planned package structure is:

```text
src/
└── solara_travel/
    ├── domain/
    ├── application/
    ├── ports/
    ├── infrastructure/
    ├── analytics/
    ├── workflows/
    ├── presentation/
    └── config/
```

Directories should be introduced only when a commit contains functionality that
belongs in them.

Empty architecture scaffolding should not be created merely to make the
repository resemble this diagram.

## Domain layer

The `domain` package owns the concepts and rules that describe travel and
recommendation behaviour.

Potential domain concepts include:

- geographic coordinates;
- destinations;
- attractions;
- experiences;
- travel periods;
- traveller preferences;
- trip constraints;
- weather observations;
- seasonal observations;
- recommendation requests;
- recommendation candidates;
- score components;
- recommendation results.

The domain layer should express Solara's language rather than the language of
external providers.

For example, the system should reason about:

```text
Destination
Attraction
WeatherObservation
TravellerPreferences
Recommendation
```

rather than:

```text
GooglePlacesResult
MeteostatDataFrame
OpenAIResponse
LangGraphState
```

### Domain constraints

The domain layer must not directly depend on:

- Google Places;
- Meteostat;
- OpenAI;
- LangChain;
- LangGraph;
- HTTP clients;
- web frameworks;
- databases;
- environment variables;
- provider SDKs.

Provider-specific identifiers may be represented as ordinary data where useful,
but provider SDK objects must not become domain models.

## Application layer

The `application` package coordinates Solara's use cases.

Its responsibilities may include:

- accepting validated recommendation requests;
- coordinating destination or attraction discovery;
- requesting information through provider interfaces;
- invoking deterministic analytics;
- ranking candidates;
- assembling recommendation evidence;
- coordinating optional recommendation narration;
- returning application-level recommendation results.

Application services should orchestrate behaviour rather than implement
provider-specific details.

A future recommendation flow might conceptually resemble:

```text
RecommendationRequest
        |
        v
RecommendationService
        |
        +----> PlacesPort
        |
        +----> WeatherPort
        |
        +----> SuitabilityScorer
        |
        +----> RecommendationResult
        |
        +----> Optional NarrationPort
```

The application layer should remain testable using fake or deterministic
implementations of external capabilities.

## Ports

The `ports` package defines interfaces through which the application accesses
capabilities outside the core system.

Potential ports include:

- places discovery;
- weather and climate information;
- geographic lookup;
- recommendation narration;
- persistence;
- caching.

Ports should describe what **Solara needs**, not reproduce the public API of a
particular vendor.

For example, a places port should expose normalized attraction discovery rather
than mirror the complete Google Places SDK.

A provider change should ideally require replacing an infrastructure adapter,
not rewriting the recommendation engine.

## Infrastructure

The `infrastructure` package contains concrete integrations with external
systems.

Potential future structure:

```text
infrastructure/
├── places/
│   └── google.py
├── weather/
│   └── meteostat.py
├── geocoding/
│   └── provider.py
└── ai/
    └── openai.py
```

Infrastructure adapters are responsible for:

- communicating with external systems;
- handling provider-specific authentication;
- interpreting provider responses;
- normalizing provider data;
- translating provider failures;
- returning Solara-owned representations.

External API response objects should not propagate through the application.

Similarly, arbitrary SDK exceptions should not leak throughout the codebase.

## Analytics

The `analytics` package contains deterministic travel-intelligence
calculations.

Potential capabilities include:

- popularity normalization;
- weather comfort scoring;
- climate suitability;
- seasonal suitability;
- interest matching;
- category suitability;
- traveller-preference matching;
- crowd-tolerance scoring;
- weighted recommendation scoring;
- recommendation score decomposition.

Analytics should remain:

- deterministic;
- network-independent;
- provider-independent;
- independently testable;
- explainable.

A recommendation score should expose its component contributions rather than
producing only an opaque final number.

For example:

```text
Overall suitability: 0.82

Components:
- climate comfort:       0.90
- interest match:        0.85
- seasonal suitability:  0.80
- popularity:            0.72
- crowd preference:      0.76
```

The exact scoring model will be introduced and tested incrementally.

## Deterministic logic and AI

Solara should explicitly distinguish deterministic reasoning from generative
behaviour.

### Deterministic work

Normal program logic should own behaviour such as:

- validation;
- score normalization;
- date calculations;
- filtering;
- weighting;
- climate comparisons;
- preference matching;
- candidate ranking;
- eligibility rules;
- recommendation ordering.

If a result can be calculated reliably using explicit rules, an LLM should not
be required to calculate it.

### Generative work

AI models may assist with:

- natural-language recommendation explanations;
- summaries;
- traveller-friendly narratives;
- itinerary prose;
- conversational interaction;
- synthesis of already-grounded evidence.

An AI model should not silently decide the underlying score that determines
which destination or attraction ranks first.

The deterministic recommendation result should exist before optional AI
narration is applied.

Solara should remain useful when the AI provider is unavailable.

### Grounded narration boundary

Grounded narration is application enrichment applied only after deterministic
recommendation work is complete:

```text
RecommendationService
        |
        v
RecommendationResult
        |
        v
RecommendationNarrationService
        |
        v
NarrationProvider
        |
        v
OpenAIResponsesNarrationProvider
```

`RecommendationResult` remains authoritative. The narration service creates a
deterministic, structured grounding payload from that result and asks a provider
for traveller-friendly prose. Provider failures are recoverable: the exact
result remains available with no narration. Generated prose never flows back
into eligibility, evidence, scoring, or ranking.

The application layer depends on the vendor-independent `NarrationProvider`
port, not OpenAI. OpenAI infrastructure depends on that port and the shared JSON
HTTP transport. Domain and analytics code have no dependency on narration
infrastructure.

## Provider normalization

External providers commonly return different:

- schemas;
- identifiers;
- naming conventions;
- units;
- category systems;
- error types;
- availability guarantees.

Provider adapters should normalize these differences into Solara-owned models at
the infrastructure boundary.

For example:

```text
Google Places
      |
      v
GooglePlacesAdapter
      |
      v
Attraction
```

and:

```text
Weather Provider
      |
      v
WeatherAdapter
      |
      v
WeatherObservation
```

The application and analytics layers should not need to understand how the
provider originally represented the data.

## Workflows

The `workflows` package contains orchestration mechanisms for use cases that
genuinely benefit from explicit multi-step state management.

LangGraph may be used in this layer where graph-based orchestration provides
clear value.

Possible workflow steps could eventually include:

```text
validate request
      |
discover candidates
      |
gather evidence
      |
calculate suitability
      |
rank results
      |
generate explanation
      |
return recommendation
```

LangGraph must not own:

- travel-domain entities;
- validation rules;
- scoring formulas;
- provider interfaces;
- provider normalization;
- core application policy.

The application should remain understandable and testable without requiring
domain behaviour to execute inside LangGraph nodes.

## Presentation

The `presentation` package contains the entry points through which users or
other systems interact with Solara.

Potential presentation layers include:

- command-line interfaces;
- FastAPI endpoints;
- web applications;
- desktop applications.

Presentation code should:

1. accept external input;
2. translate it into application inputs;
3. invoke application services;
4. translate application results into external responses.

Presentation code should not implement recommendation algorithms.

### FastAPI application foundation

FastAPI is an optional `web` dependency and belongs exclusively to the
presentation layer. The ASGI boundary follows the existing inward dependency
direction:

```text
HTTP Client
    |
    v
FastAPI Presentation
    |
    v
Application Services
    |
    v
Domain / Ports / Analytics
```

`create_app()` is the composition entrypoint for this HTTP surface and returns a
new application instance without reading environment configuration, composing
providers, or making network calls. Application and domain modules do not
depend on FastAPI.

The unversioned `GET /health` route proves only that the ASGI process can serve
and serialize an HTTP response. It does not check Google Places, Open-Meteo,
OpenAI, or recommendation readiness.

### Recommendation HTTP boundary

The public application contract exposes `POST /api/v1/recommendations` while
operational health remains unversioned. Recommendation logic stays in the
application and domain layers:

```text
HTTP JSON
    |
    v
RecommendationRequestBody
    |
    v
HTTP-to-domain mapper
    |
    v
RecommendationRequest
    |
    v
RecommendationService
    |
    v
RecommendationResult
    |
    +----> optional RecommendationNarrationService
    |
    v
HTTP response mapper
    |
    v
RecommendationResponse
```

`ApiDependencies` injects application services when each FastAPI instance is
created. The default module-level app remains credential-free; it serves health
normally and returns a safe `503` for recommendation calls until a
`RecommendationService` is supplied.

The presentation layer explicitly maps domain values and selected aggregate
evidence. It preserves recommendation order, scores, components, and request
data without rescoring or exposing raw provider payloads or historical
observations. Known provider-boundary failures become safe `502` or `503`
responses. Optional narration is applied only after the deterministic result;
an AI provider failure leaves that result usable with no narration.

### Browser presentation boundary

The presentation layer has separate `api` and `web` surfaces. The browser is a
package-owned presentation flow:

```text
Browser
    |
    v
GET /
    |
    v
Web presentation
    |
    +----> packaged semantic HTML
    |
    +----> packaged CSS at /static/styles.css
    |
    +----> packaged JavaScript at /static/app.js
```

The root route is excluded from OpenAPI, and its local static mount is likewise
separate from the JSON API contract. HTML, CSS, and JavaScript resolve relative to the
installed `presentation.web` package, so the shell works from a wheel without a
repository working-directory assumption or external frontend dependency.

The traveller interaction stays at the presentation boundary:

```text
Traveller
    |
    v
Recommendation form
    |
    v
packaged app.js
    |
    v
JSON RecommendationRequestBody
    |
    v
POST /api/v1/recommendations
    |
    v
RecommendationResponse
    |
    v
Commit 40 result renderer
```

The script is presentation-only and calls the same-origin recommendation API;
provider calls remain server-side. The browser uses destination-discovery mode
with `destination: null` rather than asking travellers for raw coordinates. The
programmatic API continues to support a preselected destination.

Current deterministic scoring is season-led. Interests, preferred pace, and
preferred climate travel through the request but are not yet separate score
components. Commit 39 parses a successful response and exposes it through the
internal `solara:recommendation-ready` browser event without rendering or
persisting its contents. Commit 40 owns result rendering, and Commit 41 owns
comprehensive validation, loading, error, and empty-state presentation.

## Configuration

The `config` package will own typed application configuration when external
integrations are introduced.

Configuration should:

- read environment-driven values at application boundaries;
- distinguish required and optional integrations;
- provide useful errors for missing required configuration;
- avoid import-time validation side effects;
- avoid global provider-client construction;
- never embed secrets in source control.

Domain and analytics modules must remain importable without API keys.

The presence or absence of an OpenAI, places, or weather credential should not
determine whether Solara's core domain package can be imported.

## Dependency direction

The intended dependency direction is:

```text
presentation
      |
      v
application <----- workflows
      |
      +-------> analytics
      |
      +-------> domain
      |
      v
    ports
      ^
      |
infrastructure
```

Additional relationships include:

```text
analytics ------> domain
ports ----------> domain
infrastructure -> ports
infrastructure -> domain
```

The important constraint is that dependencies point inward toward Solara-owned
contracts and concepts.

The domain must not depend outward on infrastructure.

Infrastructure implements ports; ports do not depend on infrastructure.

## Recommendation evidence

Solara's recommendation architecture should make it possible to distinguish
between different kinds of information.

A recommendation may eventually contain:

```text
Recommendation
├── deterministic scores
├── provider observations
├── traveller preferences
├── assumptions
├── missing-data notices
├── trade-offs
└── generated explanation
```

Generated prose should be derived from the recommendation evidence rather than
becoming the evidence itself.

This distinction is essential for explainability and reliable testing.

## Failure handling

Failures should be explicit and meaningful.

The architecture should distinguish situations such as:

- invalid user input;
- unsupported travel requests;
- missing provider credentials;
- provider timeout;
- provider rate limiting;
- malformed provider response;
- provider service failure;
- no matching destinations;
- incomplete recommendation evidence;
- optional narration failure.

Broad exception handling should not hide programming errors.

Provider-specific failures should be translated at infrastructure boundaries
where appropriate.

Optional integrations should fail gracefully when the rest of the system can
still provide a useful result.

## Graceful degradation

Solara should avoid an all-or-nothing dependency on external services.

For example:

```text
Deterministic recommendation succeeds
             |
             +---- AI available ----> recommendation + narrative
             |
             +---- AI unavailable --> recommendation without narrative
```

Similarly, when some evidence is unavailable, Solara should make the limitation
visible rather than silently fabricate missing information.

## Testing strategy

Testing should follow architectural boundaries.

### Domain tests

Verify:

- validation;
- invariants;
- value semantics;
- invalid states;
- boundary conditions.

### Analytics tests

Verify:

- deterministic calculations;
- score boundaries;
- normalization;
- weighting;
- ordering;
- edge cases;
- explainable components.

### Application tests

Use fakes or deterministic test implementations of ports.

Verify:

- orchestration;
- provider collaboration;
- ranking flow;
- partial failures;
- result assembly.

Application tests should not require network access.

### Infrastructure tests

Verify:

- provider response mapping;
- normalization;
- error translation;
- unit conversion;
- malformed-response handling.

Live network integration tests, if introduced, should remain separate from the
default unit suite.

### Presentation tests

Verify:

- input translation;
- request validation behaviour;
- response structures;
- status behaviour.

Presentation tests should not duplicate core domain tests.

## Offline-first testability

A major architectural requirement is that Solara's core recommendation path can
be exercised using local deterministic data.

The default test suite must not require:

- Google API credentials;
- OpenAI credentials;
- weather-provider credentials;
- internet access.

This allows the core product to be tested reliably, quickly, and inexpensively.

## Persistence

Persistent storage should not be introduced merely because Solara may need it in
the future.

Storage should be added when a concrete user journey requires durable state.

Potential future requirements include:

- saved traveller profiles;
- saved trips;
- recommendation history;
- favourite destinations;
- collaborative itineraries.

When persistence is introduced, application and domain logic should depend on
repository interfaces rather than directly on a database client.

The choice of database should remain an infrastructure decision.

## Caching

Caching should be introduced only when provider behaviour or product usage
demonstrates a need.

Likely future caching candidates include:

- place discovery results;
- geocoding results;
- historical climate observations;
- expensive provider responses.

Caching policy must not become embedded in domain logic.

## Observability

Production observability will be introduced when Solara gains deployed
application workflows.

Potential future concerns include:

- structured logging;
- provider latency;
- provider failures;
- recommendation execution time;
- cache effectiveness;
- request volume;
- AI token usage;
- degraded-result frequency.

Observability should help explain system behaviour without capturing sensitive
traveller information unnecessarily.

## Security boundaries

API credentials and other secrets must remain outside source control.

External input should be validated before reaching core application behaviour.

Provider data should also be treated as external input and normalized before it
is trusted by the rest of the system.

Future user-generated content, saved profiles, or authentication features will
require additional security design when those capabilities become real product
requirements.

## Architecture constraints

Unless a later architectural decision explicitly changes them, the following
constraints apply:

1. The domain layer must not import infrastructure.
2. Domain behaviour must not require network access.
3. Analytics must remain deterministic and network-independent.
4. Provider SDK objects must not become domain objects.
5. Provider-specific response formats must be normalized at boundaries.
6. Core tests must not require API keys.
7. LLMs must not be the sole source of recommendation ranking.
8. AI narration must remain optional to the deterministic recommendation path.
9. LangGraph must remain an orchestration mechanism rather than the domain model.
10. Presentation frameworks must not own recommendation behaviour.
11. New abstractions must solve a demonstrated problem.
12. Provider choice must not require rewriting core recommendation logic.
13. Persistence technology must remain outside the domain layer.
14. Planned architecture must not be represented as already implemented.

## Architectural decision discipline

A significant architectural change should answer:

- What concrete problem does it solve?
- Why is the current design insufficient?
- Which architectural boundary changes?
- Which dependency direction changes?
- How will the behaviour be tested?
- What complexity does the change introduce?
- Can the same problem be solved more simply?

Frameworks and infrastructure should be introduced because the product requires
them, not because they are fashionable or technically interesting.

## Evolution

This document describes Solara's intended architectural direction.

Not every package, provider, model, or workflow described here currently exists.

Architecture will be introduced incrementally alongside tested functionality.

Useful concepts from the original prototype may return, but they should return
within these architectural boundaries rather than reintroducing the prototype's
tight coupling.

Significant deviations from this architecture should be deliberate, reviewed,
and documented before they become permanent design constraints.
