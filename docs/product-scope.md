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

A traveller may leave destination input blank and ask where to go, supply one
human-readable city/locality for evaluation, or supply two to five cities for a
bounded comparison. Country-wide recommendation is not part of MVP1. Solara
resolves explicit locality names server-side, then uses
the same evidence, deterministic scoring, and ranking pipeline in every mode.
Blank discovery remains an intended Solara capability. In the current hosted
public alpha, however, the tested real blank-discovery request completed with an
empty result rather than useful destination candidates; correction is deferred
to the next public-alpha experience iteration in Commit 48.

Commit 48's visual travel experience begins with a photography-led homepage,
curated Popular Escapes, and a compact trip planner. Popular Escapes is static
editorial inspiration: choosing a card only adds that city/locality to the
planner and does not influence ranking or spend provider quota. Country scope
and locality discovery within a country remain future Commit 49 capabilities,
not part of this visual phase.

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

## Out of scope for the initial milestones

The initial implementation will not:

- book flights, hotels, activities, or transport;
- process payments;
- guarantee prices or availability;
- replace official visa, immigration, health, or safety advice;
- provide real-time emergency guidance;
- operate as an autonomous travel agent;
- scrape websites in violation of their terms;
- require a vector database before there is a demonstrated product need;
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
