# Solara Product Scope

## Purpose

Solara is a travel-intelligence platform that helps travellers identify
destinations, attractions, and trip plans suited to their timing, preferences,
constraints, and comfort expectations.

The platform should go beyond generic popularity lists by considering seasonal
conditions, traveller intent, trip context, and explainable suitability.

## Target users

Solara is intended for travellers who:

- are deciding where to travel;
- have a specific month, season, or date range in mind;
- want recommendations aligned with their interests;
- care about weather and seasonal comfort;
- need recommendations that respect time or budget constraints;
- want to understand why a place was recommended;
- prefer a structured starting point rather than an unfiltered list of options.

## Core user journeys

### Destination discovery

A traveller may select up to 15 cities, countries, regions, provinces, island
groups, or similar supported geographies in one request, or leave destination
blank for worldwide discovery. Broad and exact scopes may be mixed freely. A
country or region is never treated as one scoreable destination. For broad and
blank requests, an AI adapter proposes bounded locality pools from the dates and
traveller intent; Google then validates each locality, coordinates, country,
administrative context, and requested-scope containment before it can enter the
existing evidence pipeline. Explicit localities are reserved first. Remaining
capacity is allocated fairly across broad scopes, deduplicated, and capped at 15
concrete scoreable destinations globally.

Explicit-city evaluation and comparison bypass candidate-proposal AI. Interests,
pace, climate, and the optional natural-language trip description may influence
which localities are proposed for broad/open discovery, but do not become new
numeric score components. Historical seasonal evidence and deterministic
scoring still own final ranking. Geographic suggestions are same-origin,
provider-neutral, user-confirmed, and protected by identity-free process-local
limits. Each result may explain whether it came from an exact traveller selection
or a broad-scope expansion; that context never changes scoring.

### Attraction discovery

A traveller selects a destination. Solara identifies relevant attractions and
experiences, normalizes provider data, and ranks them against the trip context.

### Seasonal suitability

Solara evaluates how destination conditions align with the traveller's selected
period and weather preferences.

### Recommendation explanation

Solara explains the main factors that influenced a ranking, including strengths,
trade-offs, assumptions, and unavailable evidence.

### Itinerary assistance

Solara organizes selected experiences into a practical trip outline based on
duration, pace, interests, and known constraints.

## Initial product scope

The first usable version should support:

- structured destination-recommendation requests;
- discovery, single-city evaluation, and small city comparisons;
- one-country or one-region locality discovery;
- guided interests, stable pace/climate choices, and optional trip context;
- traveller interests and trip-style preferences;
- destination and attraction representations;
- normalized weather and seasonal observations;
- deterministic suitability scoring;
- explainable ranking components;
- replaceable place and weather providers;
- an application service that coordinates recommendations;
- an offline demonstration path;
- a simple API for recommendation requests.

## Recommendation inputs

The model should eventually support inputs such as:

- origin or home region;
- candidate destination or destination region;
- travel month or date range;
- trip duration;
- traveller interests;
- preferred pace;
- preferred climate;
- budget level or budget range;
- accessibility or mobility considerations;
- indoor versus outdoor preference;
- solo, couple, family, friends, or group travel;
- tolerance for crowds, rain, heat, cold, and travel complexity.

Not every input must be implemented in the first milestone.

## Recommendation outputs

A recommendation should eventually include:

- ranked destinations or attractions;
- an overall suitability score;
- named scoring components;
- supporting observations;
- important trade-offs;
- explicit assumptions;
- uncertainty or missing-data notices;
- a concise recommendation explanation;
- optional itinerary suggestions.

For the current public alpha, the traveller-facing numeric result is seasonal
fit derived from seasonal temperature comfort. Technical component weights stay
available to engineering/API consumers. Interests and pace are accepted as
context but are not yet independent deterministic ranking factors.

## Product principles

### Explainability

Every ranking should expose its major contributing factors. Solara should avoid
presenting an unexplained score as an authoritative answer.

### Evidence awareness

Provider data, deterministic calculations, assumptions, and AI-generated text
must remain distinguishable.

### Conservative guidance

Solara should avoid presenting uncertain or incomplete travel information as
guaranteed fact.

### Traveller control

Preferences and constraints supplied by the traveller should materially
influence recommendations.

### Provider independence

Core recommendation logic should not depend directly on one commercial weather,
places, mapping, search, or AI provider.

### Graceful degradation

Useful deterministic results should remain available when optional AI generation
or an external provider is unavailable.

### Phase 2B traveller experience boundary

Postcards are optional visual enrichment from current provider-backed photo
metadata. The Wayfinder is optional structured explanation and storytelling.
Neither is evidence, neither selects or orders destinations, and neither can
change Seasonal Fit. Photo, handle, media, narration, or schema failure leaves the
same deterministic recommendation usable.

The ordinary traveller UI is intentionally non-technical: it prioritizes imagery,
destination identity and provider-backed administrative context, Seasonal Fit,
concise stories, Places to see, editorial Seasonal feel, grounded destination-
character Good to know, and shortlist comparison. Good to know is omitted when
trusted non-seasonal grounding is insufficient; the historical-not-forecast note
appears once for the overall result rather than inside every card. Components,
weights, weighted
contributions, configured comfort values, raw aggregates, and audit keys remain
available internally and through the additive typed API for engineering and
compatible consumers; hiding them in the browser does not delete them.

The homepage catalogue contains exactly twelve locally bundled, credited Popular
Escapes and uses three-second motion with pause/resume, hidden-tab pausing, and no
automatic movement under reduced-motion preferences. Premium pace/climate menus
and the vacation-description composer preserve stable API values and traveller
text without claiming those preferences are independent numeric score factors.

### Commit 49 itinerary boundary

Commit 49's Itinerary Studio / Build This Trip is implemented downstream of
validated recommendations and selected canonical localities. It organizes
Morning, Afternoon, and Evening; supports trusted activity add, remove, replace,
move, and reorder operations; sequences destinations with positive allocations;
and represents planning-only transport legs without implying live schedules.
Traveller party, pace, children/senior context, and declared practical mobility
or rest needs modify a deterministic day-time budget. Duration ranges declare
provider, bounded category-heuristic, or traveller-selected provenance; unknown
duration and accessibility remain explicitly unknown.

Hard eligibility constraints are separate from soft style preferences. The
mandatory cold-or-snowy choice uses trusted historical evidence for the requested
dates before ranking. If the evidence cannot establish cold conditions, the
candidate is excluded; a successful zero-match result offers climate,
destination, and search recovery actions. Seasonal Fit remains deterministic and
historical, not a forecast. The Wayfinder itinerary overview explains only the
already structured plan and cannot create facts or override feasibility.

The studio is an active, privacy-preserving browser session without accounts or
persistence. It contains no accommodation inventory, booking inventory, live
price, cart, payment, or partner API.

### MVP2 destination knowledge and RAG boundary

Destination Knowledge + RAG Grounding is deferred entirely to MVP2. A future
curated or verifiable corpus may use ingestion, normalization/chunking,
embeddings, vector or hybrid retrieval, metadata and geographic filtering,
freshness metadata, and destination/admin-area linking to ground destination
facts, Good to Know, destination character, cultural or practical context,
Wayfinder stories, and itinerary enrichment.

The knowledge corpus must use authoritative or verifiable sources and retain
source URL, publisher/source, destination, country, relevant administrative area,
retrieval date, publication/update date when available, content type, and
relevant licence/use boundaries. Retrieval may support grounded Good to Know,
destination character, practical/cultural/activity context, and itinerary
storytelling with future source links. It must not replace geographic validation,
historical weather evidence, deterministic seasonal scoring, or rank authority.
No vector provider is selected; vector and hybrid retrieval technology will be
evaluated during MVP2.

## Out of scope for the current public alpha

The current public-alpha implementation does not:

- book flights, hotels, activities, or transport;
- process payments;
- persist itineraries or provide multi-country journey management;
- persist trips or provide traveller accounts;
- provide partner booking inventory or booking-provider integrations;
- operate the MVP2 destination corpus, RAG, or vector-retrieval layer;
- guarantee prices or availability;
- replace official visa, immigration, health, or safety advice;
- provide real-time emergency guidance;
- operate as an autonomous travel agent;
- scrape websites in violation of their terms;
- introduce a vector database or RAG pipeline during MVP1;
- introduce multi-agent orchestration merely for architectural novelty.

## Future possibilities

Later versions may explore:

- collaborative trip planning;
- saved traveller profiles;
- multi-city itinerary optimization;
- live disruption awareness;
- accommodation and transport comparisons;
- sustainable-travel preferences;
- accessibility-focused recommendations;
- multilingual travel assistance;
- map-based planning;
- mobile and desktop applications;
- integration with the Tuesday personal assistant.

These possibilities are not commitments for the initial release.

## Success criteria

The first meaningful Solara milestone should demonstrate that:

1. a structured travel request can be validated;
2. provider data can be normalized behind stable interfaces;
3. recommendations can be scored deterministically;
4. each ranking can be explained;
5. the core workflow can be tested without network access;
6. optional AI narration can be added without owning the recommendation logic;
7. the system can be extended without rewriting the domain layer.
