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

### The Wayfinder structured narration boundary

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
for one strict `WayfinderNarrative`: an opening, rank-aligned destination notes,
and an optional comparison note. Each note owns `why_it_fits`, an editorial
`seasonal_feel`, optional `good_to_know`, and provider-backed highlights.
Seasonal Feel qualifies historical evidence naturally once rather than repeating
technical templates. Good to Know may synthesize only trusted destination
identity, attractions/categories, traveller context, and provider-backed
administrative context; it is omitted instead of filled when that grounding is
insufficient. A generic historical-not-forecast statement is rendered once at
the overall result boundary, not once per destination. Provider failures or
invalid structured output are recoverable: the exact result remains available
with no Wayfinder. The application restores authoritative result order even if a
provider returns notes out of order. Generated prose never flows back
into eligibility, evidence, scoring, or ranking.

The application layer depends on the vendor-independent `NarrationProvider`
port, not OpenAI. OpenAI infrastructure depends on that port and the shared JSON
HTTP transport. Domain and analytics code have no dependency on narration
infrastructure.

### MVP2 destination-knowledge and retrieval boundary

Destination Knowledge + RAG Grounding is deferred entirely to MVP2 and is not
part of the remaining MVP1 implementation sequence:

```text
curated/verifiable sources
        |
        v
ingestion -> normalization/chunking -> embedding/indexing
        |
        v
metadata-filtered vector or hybrid retrieval
        |
        v
grounded destination context -> Wayfinder / itinerary generation
        |
        v
source provenance
```

Every indexed unit must retain source URL, publisher, destination/country/admin
links, retrieval date, publication/update date where available, content type,
and relevant licence/use boundaries. A future retrieval port must allow provider
selection based on cost, latency, geographic and hybrid filtering, operations,
scale, lock-in, and developer ergonomics. Pinecone or another vector store may
be evaluated during MVP2; no implementation is selected or depended on now.

Throughout MVP1, provider-backed geography and places plus deterministic seasonal
evidence remain authoritative. Wayfinder may use only currently trusted request
and result context; Good to Know is omitted when trustworthy non-seasonal
grounding is insufficient, and unsupported destination facts must not be
generated merely to improve prose.

In MVP2, retrieved knowledge may ground destination facts, Good to Know,
destination character, practical, cultural, or activity context, Wayfinder
stories, and itinerary enrichment. It may not silently replace provider-backed
geography, historical weather evidence, deterministic seasonal scoring, or rank
authority. The presentation contract reserves future source-aware experiences
such as Sources, Learn more, and Why Solara says this without exposing technical
retrieval diagnostics.

### Postcards photo-enrichment boundary

Postcards are transient visual enrichment, never recommendation evidence. After
ranking, `PostcardEnrichmentService` asks a provider-independent metadata port
for at most four current photos per destination. The hosted Google adapter makes
one bounded Places Text Search per result destination, deduplicates photo/place
identity, and returns current photo dimensions, Google Maps source links, and any
author attributions. Failure yields an empty gallery and a premium Solara fallback;
it cannot fail, reorder, or rescore the recommendation.

Google photo names are not persisted. A startup-random HMAC secret signs each
fresh resource name into a tamper-resistant five-minute browser handle. The
browser receives only `/api/v1/postcards/{handle}`. The same-origin delivery
route verifies expiry, calls Place Photos (New) with bounded dimensions and
`skipHttpRedirect=true`, then retrieves the credential-free Google media URI.
It returns supported image bytes with `private, no-store, max-age=0`; neither the
resource name nor image content is written to a database, filesystem, Redis, or
browser cache. The Google API key stays in server headers and never enters HTML,
JavaScript, or an image URL.

The gallery associates author names/profile links with each image, links directly
to the source photo on Google Maps, and displays Google Maps attribution. This
design follows the current official [Place Photos (New)](https://developers.google.com/maps/documentation/places/web-service/place-photos)
and [Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies)
reviewed for Phase 2B. The browser sends no cookies, analytics identifiers, user
IP forwarding, User-Agent forwarding, or direct third-party image request.

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

Autocomplete has independent short-window, long-window, and concurrency
admission before Google is called. Broad/open recommendation plans consume a
separate discovery-AI budget immediately before candidate proposal; explicit
locality and multi-city plans do not consume it. These limits share no identity
key and remain distinct from upstream Google/OpenAI `429` translation.

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

### Public-alpha safeguard boundary

`PublicAlphaSafeguardSettings` supplies immutable positive-integer policy to a
fresh `ApiSafeguards` instance stored on each application. The runtime uses a
monotonic clock, bounded rolling timestamp queues, one lock for atomic
recommendation admission, and a concurrency lease that is released on every
success or exception path. Admission happens only after HTTP and domain
validation and service-configuration checks:

```text
valid recommendation request
    |
    v
process-local admission: concurrency -> short rate -> longer budget
    |-- rejected --> safe 429 + Retry-After
    v
RecommendationService -> deterministic result
    |
    v
narration budget
    |-- available --> optional narration attempt
    `-- exhausted --> deterministic result only
    |
    v
RecommendationResponse
```

Accepted recommendation attempts consume the short-window and longer-budget
slots atomically; concurrency or rate rejection consumes no unrelated quota.
The separate candidate-proposal budget consumes one atomic unit per broad/open
proposal call, so a mixed request cannot hide multiple provider calls behind one
admission. Each request is still bounded to 15 units. The separate narration
budget never blocks or changes deterministic ranking.
When it is exhausted, Solara skips the provider call, emits `narration.skipped`,
and returns the deterministic `200` response without narration. Valid feedback
has an independent rolling rate and invalid bodies consume no capacity.

Safeguard rejections expose only a stable Solara-owned code, fixed safe message,
integer delta-seconds `Retry-After`, and the ordinary server-owned request ID.
Safe `recommendation.rejected` and `feedback.rejected` events include only the
request ID, code, safeguard stage, and retry duration. They contain no submitted
body or client metadata.

These guardrails are deliberately global and identity-free: IP addresses,
forwarding headers, cookies, request IDs, fingerprints, geolocation, and account
identifiers are never limiter keys. State exists only in one application
process, resets at restart, and is not coordinated across workers or instances.
It is best-effort public-alpha protection, not a guaranteed financial ceiling or
distributed abuse-prevention platform.

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
    |
    +----> packaged result renderer at /static/results.js
    |
    +----> packaged geographic typeahead at /static/travel-scopes.js
    |
    +----> packaged tester feedback at /static/feedback.js
    |
    +----> approved brand assets at /static/branding/*.png
```

The root route is excluded from OpenAPI, and its local static mount is likewise
separate from the JSON API contract. HTML, CSS, and JavaScript resolve relative to the
installed `presentation.web` package, so the shell works from a wheel without a
repository working-directory assumption or external frontend dependency. The four
approved Solara logo variants live in the nested `static/branding` directory and are
explicit package data in both wheel and source distributions. The browser does not
load external fonts, images, scripts, trackers, or asset CDNs.

Commit 43 presents this boundary as a premium editorial travel experience: a branded
header, season-smart hero, evidence-oriented insight card, integrated planner, curated
results region, tester-feedback panel, product-principle section, and quiet branded
footer. Warm ivory surfaces, forest text, muted gold accents, serif-forward display
type, responsive layout changes, visible focus treatment, and reduced-motion behavior
are all owned by packaged HTML and CSS. This visual organization does not add a new
application layer or browser data source.

The traveller interaction stays at the presentation boundary:

```text
Traveller
    |
    v
Recommendation form
    |
    v
app.js validation
    |
    +----> validation summary / field errors
    |
    v
solara:recommendation-request-start
    |
    v
loading state + stale-result clearing
    |
    v
POST /api/v1/recommendations
    |
    +----> 422 validation state
    +----> 502/503 provider or service state
    +----> network / unexpected HTTP state
    |
    +----> RecommendationResponse
              |
              v
        solara:recommendation-ready
              |
              v
        results.js
              |
              +----> authoritative ranked cards
              +----> deterministic score factors
              +----> attraction evidence
              +----> historical seasonal evidence
              +----> temperature comfort evidence
              +----> optional grounded narration
              +----> successful empty state
```

The browser is presentation-only and calls same-origin Solara APIs; provider
calls remain server-side. `travel-scopes.js` debounces destination text, aborts
stale requests, and uses an accessible listbox backed by
`POST /api/v1/travel-scope-suggestions`. The response contains only canonical
display text and Solara's `locality`, `region`, or `country` hint. It contains no
Google identifier or raw payload. Prediction display includes the exact
space-constrained text attribution `Google Maps`, marked `translate="no"` and
visually separated below the predictions, following the current
[Places API policy](https://developers.google.com/maps/documentation/places/web-service/policies).
No invented or hotlinked Google logo is used. The canonical text is resolved
again on intentional recommendation submit.

`TravelScope` and `TravelScopeKind` are provider-independent domain values.
Google Text Search normalizes locality, country, administrative-region, and
archipelago responses behind `TravelScopeResolutionPort`; unfamiliar or business
types are rejected rather than guessed. A locality carries the normalized name,
coordinates, and country needed to become a scoreable `Destination`. A broad
scope carries country/region containment evidence but never becomes a
`Destination` and is never scored.

```text
pre-resolved Destination ----------------------------------+
                                                            |
up to 15 selected scopes -> Google scope normalization -----+
          |                                                 |
          +-> exact LOCALITY (reserved first) ---------------+-> deduplicate
          |                                                 |       |
          +-> COUNTRY/REGION -> bounded proposal -> Google --+       v
blank/global -------------> bounded proposal -> Google ------+  max 15 concrete
                                                                     localities
                                                                         |
                                                                         v
                                                           evidence -> deterministic rank
```

`DestinationCandidateProposalPort` is the only AI-assisted candidate boundary.
The hosted OpenAI Responses adapter uses strict structured output for five to
eight proposed locality names per broad scope, treats traveller text as untrusted
data, grants no tools, and stores no response. Up to 15 broad and exact scopes may
be mixed. Every proposed name is then resolved by Google; non-localities, out-of-
scope results, ambiguous results, and duplicates are discarded. Exact localities
are authoritative and reserve scoreable capacity first. A deterministic round-
robin gives every valid broad scope representation where capacity permits, then
distributes remaining places fairly. Scope work uses at most three concurrent
workers and the final set never exceeds 15 concrete destinations. Each result
retains provider-independent origin and optional provider-backed administrative
context for presentation only. Those values never enter eligibility, evidence,
scoring, or ranking. Requests containing only exact cities short-circuit proposal
AI entirely.

Interests, pace, climate, and `trip_description` may influence candidate proposal
for broad/open discovery and remain narration context. They are not independent
numeric score components. `destination_not_found` may carry bounded Google-backed
correction suggestions, but the traveller must select a correction and submit
again; no silent rewrite occurs. Submitted geography, preferences, description,
proposals, and raw model output are excluded from operational logs.

Current deterministic scoring is season-led. Interests, preferred pace, and
soft preferred climate travel through the request but are not separate score
components. An explicit `ClimateConstraint` has independent hard/soft severity.
The mandatory cold-or-snowy UI choice creates a hard constraint: trusted
historical seasonal evidence is gathered for the requested date window, an
absolute cold threshold is applied, and incompatible candidates are removed
before deterministic sorting. Temperature evidence can establish cold; Solara
does not infer or claim snowfall without a snowfall source. A zero-candidate
result is a successful truthful outcome. Browser validation supplements the
authoritative domain validation:
it reports known date and interest problems but never silently repairs malformed
input. After validation, `app.js` owns busy state, fetching, safe status/code
classification, and fixed local error copy. Raw backend error text never reaches
the DOM except for the application-owned `destination_not_found` explanation.
That explanation echoes only the normalized query submitted by the same caller,
is inserted through `textContent`, and is never added to operational logs.

`app.js` dispatches `solara:recommendation-request-start` only when a real
network request begins. `results.js` uses that event to clear stale results, so
an invalid edit does not destroy the previous useful outcome. Retry calls the
normal `form.requestSubmit()` path and therefore revalidates current values;
there is no automatic retry or backoff. On success, the existing
`solara:recommendation-ready` event remains the sole handoff. `results.js`
consumes the parsed response without fetching independently, preserves response
array order and rank, never rescores, and owns both ranked and successful-empty
rendering.

### Commit 49 itinerary architecture

The itinerary domain is provider-independent. `TravellerParty`,
`TravellerProfile`, `DestinationStay`, `Itinerary`, `ItineraryDay`, `DayPeriod`,
`ActivityOption`, `ItineraryActivity`, `DurationEstimate`, `TravelLeg`, and
`FeasibilityAssessment` contain no Google payload or partner-commerce fields.
Duration carries a range, provenance, and confidence; accessibility supports
confirmed, unavailable, and unknown rather than optimistic inference. A
`TravelLeg` may remain structurally present with no mode, duration, distance,
buffer, or provenance claim. A mode or other route claim is valid only when the
leg is marked verified and carries evidence provenance. The repository has no
configured routing adapter: Google Places does not provide this capability.

Application services remain separated by responsibility. Activity discovery
maps at most twelve normalized Places attractions into stable options and only
applies documented category duration heuristics. Planning builds coherent route
days, the immutable editor owns add/remove/replace/move/reorder behavior, and the
feasibility service owns deterministic time budgets. Activity duration,
transition buffers, meal/rest time, inbound travel, pace, children/seniors, and
declared practical requirements contribute visibly. Unknown travel or visit
duration produces guidance rather than fabricated precision. Inbound travel
with unknown duration makes the complete arrival-day assessment explicitly
unresolved; it is never converted to zero or a generic 90-minute journey. For a
verified duration range, feasibility conservatively consumes the upper bound and
adds a separately evidenced planning buffer. Known travel that consumes the
usable planning window, or known travel plus activities and required buffers
that exceed it, is a hard conflict; ordinary fullness remains calm guidance and
traveller choice.

`POST /api/v1/itinerary-activities` resolves submitted geography again as a
canonical locality, shares the existing process-local discovery safeguard, and
returns a bounded provider-neutral palette. It is the browser's primary activity
discovery boundary: server identities, duration provenance/confidence, and
accessibility states remain authoritative. Per-destination loading, success,
empty, and unavailable states are cached only in an in-memory map; request
abortion and identity checks prevent stale responses from crossing destinations.
Provider failure leaves the route and day allocation usable. The browser studio
itself is an active-session configurator; it uses DOM `textContent`/node
construction and no cookies, storage, tracking, account, or hidden persistence.
Its deterministic Wayfinder fallback summarizes only the authoritative
structured itinerary.

Traveller-facing destination stories preserve deterministic order while showing
Postcards, destination identity and administrative context, a de-emphasized
Seasonal Fit percentage, The Wayfinder when present, Places to see, editorial
Seasonal feel, grounded-or-omitted Good to know, one global historical note, and
a compact multi-destination overview with origin context. Technical components, weights,
configured comfort values, observation counts, and audit keys remain typed in the
API and internal model but are intentionally absent from the ordinary UI. Optional
structured Wayfinder narration is separate enrichment and never controls ranking. All
response text is inserted through safe DOM text APIs rather than interpreted as
HTML or Markdown. Application-level normalization conservatively removes common
structured strings are validated as bounded plain text before serialization,
while the browser continues to insert the result only as text. `app.js` also
reads the server-owned `X-Request-ID` response header before consuming a
recommendation response. A handled HTTP outcome shows
that opaque UUID as a request reference and stores it only in the recommendation
form's transient dataset for `feedback.js`; local validation and network failure
never fabricate a reference, and no browser persistence is used.

After recommendation results, the tester-feedback form collects one required
`helpful`, `mixed`, or `not_helpful` rating and an optional 1,000-character
comment. `feedback.js` sends exactly those explicit fields plus the current
opaque recommendation request reference, when available, to the same-origin
feedback endpoint. It owns its in-flight, success, and fixed-copy failure states
without reading recommendation content or client metadata.

The premium redesign preserves the existing element IDs, semantic regions, browser
events, and same-origin request contracts. `app.js`, `results.js`, and `feedback.js`
retain their Commit 42 responsibilities; styling and document composition do not
rescore results, reorder recommendations, fabricate destinations, or broaden logged
or submitted data.

## Configuration

The framework-independent `solara_travel.config` package owns immutable typed
deployment settings and explicit environment parsing. The implemented hosted
composition path is:

```text
environment
    |
    v
solara_travel.config
    |
    v
workflows.hosted
    |
    v
ApiSettings + ApiDependencies
    |
    v
create_app
```

`load_deployment_settings()` reads `os.environ` only when invoked without an
explicit mapping. Importing the config or deployment module performs no
environment read, provider construction, network call, or validation. Domain,
analytics, application, and provider contracts remain environment-independent
and importable without FastAPI or credentials.

The hosted factory requires Google Places access plus OpenAI narration; Open-
Meteo needs no key. API keys are excluded from settings and provider reprs, and
configuration errors name variables without echoing values. Provider endpoints
remain trusted adapter constants rather than environment-controlled URLs.

Every `create_deployment_app()` invocation composes its own shared HTTP
transport, provider graph, application services, and process-local safeguards.
Construction makes no provider requests. It then delegates all route and
middleware registration to the existing credential-free `create_app()`.

The deployment Uvicorn runner uses one worker because public-alpha safeguards
are process-local. It disables access logging and proxy-header trust, leaving
Solara's privacy-conscious structured request events authoritative. MVP1 uses
one container/instance; additional processes or replicas would multiply the
effective limits until a distributed safeguard design exists.

The deployed MVP1 topology is operationally narrow:

```text
GitHub main -> CI checks -> Render Docker web service
    -> single Uvicorn process -> create_deployment_app()
    -> RecommendationService
        -> Google Places resolution, suggestions, attractions
        -> Open-Meteo
        -> bounded OpenAI candidate proposal for broad/open discovery
        -> optional OpenAI narration
```

The live service uses Render's Singapore region and Free plan. It keeps the
browser and API same-origin in one service and adds no database, cache, worker,
custom domain, or trusted proxy-header boundary. Root, health, and disabled-docs
behavior are verified; provider-backed recommendation, feedback, and live
responsive-browser validation completed for Commit 47's explicit-destination
public-alpha flow. Commit 48 added candidate proposal and validation for blank and
broad discovery, mixed-scope planning, Postcards, Wayfinder, and the final visual
travel experience. The exact hosted build at
`c9d698ad5e926beb4e6cad1c291f6d4a786c479c` was manually reviewed and accepted
after deployment. That acceptance does not change deterministic scoring and
ranking authority. Automated Chromium and adapter coverage continues to use only
fake providers.

The service was manually configured before `render.yaml` existed remotely. The
repository Blueprint now represents the desired topology but does not yet manage
the live service; adoption must match the existing service rather than create a
second one.

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

Operational observability is isolated in the HTTP presentation layer:

```text
HTTP request
    |
    v
RequestTracingMiddleware
    |
    +----> fresh server-generated UUID4
    +----> request.state.request_id
    +----> X-Request-ID response header
    +----> monotonic request timing
    |
    v
route

POST /api/v1/recommendations
    |
    +----> deterministic recommendation timing
    +----> optional narration timing
    +----> safe aggregate completed, failed, or rejected event

Browser feedback + optional recommendation request ID
    |
    v
POST /api/v1/feedback
    |
    +----> feedback UUID receipt
    +----> structured feedback.accepted event
    |
    v
202 Accepted
```

`solara_travel.api` emits one standard-library JSON log record per product
event. Every record has schema version 1, a UTC timestamp, and a stable dotted
event name. Request timing uses a monotonic clock. The middleware never trusts
or echoes inbound `X-Request-ID`; every handled request gets a new server-owned
identifier. Static assets and `/health` still receive the response header but
are excluded from structured request-event logging to avoid routine asset and
probe noise.

General request events contain only request ID, method, path without query
string, status, and duration. Recommendation events contain only safe failure
codes or aggregate count, narration availability, and stage timings. They never
record travel request bodies, destination or attraction data, scores, weather,
recommendation responses, IP addresses, User-Agent strings, cookies, provider
payloads, exception text, or narration content.

Tester feedback is deliberately different: `feedback.accepted` intentionally
records the explicitly submitted rating and comment, JSON escaped on one log
line, plus opaque feedback, HTTP-request, and optional recommendation-request
IDs. The UI asks testers not to provide sensitive personal information. There
is no feedback database or file persistence; the hosting process log stream is
the MVP1 alpha review mechanism. Commit 44 adds the process-local safeguards
described above, and Commit 45 adds portable deployment configuration. Host log
transport and retention remain operational concerns.

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
