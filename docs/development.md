# Solara Development Guide

## Purpose

This document defines the development workflow and engineering standards for
Solara.

Solara is being rebuilt incrementally from an earlier prototype. The goal is to
develop each capability through small, focused, testable changes rather than
recreate the prototype through a large rewrite.

Useful ideas from the original implementation may be reintroduced, but existing
code should not be copied merely because it already exists.

Each new component should earn its place through a clear product or
architectural requirement.

## Development philosophy

Solara development should prioritize:

- correctness over speed;
- clarity over cleverness;
- tested behaviour over implicit assumptions;
- small commits over broad rewrites;
- explicit architecture over framework-driven design;
- deterministic logic where deterministic answers are possible;
- provider independence;
- explainability;
- maintainability;
- incremental delivery.

A new feature should leave the repository easier to understand than it was
before the change.

## Supported Python versions

Solara supports:

- Python 3.11
- Python 3.12
- Python 3.13

Local development currently uses Python 3.13.

CI should continue validating every supported Python version unless a documented
compatibility decision changes the support policy.

## Local environment setup

From the repository root on Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,web]"
```

The local `.venv` directory must never be committed.

If PowerShell prevents virtual-environment activation for the current session,
use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Do not change machine-wide execution policy merely to activate Solara's local
environment.

## Dependency management

`pyproject.toml` is the authoritative source for package metadata and
dependencies.

Do not maintain a second independent dependency list.

Runtime dependencies belong in:

```toml
[project]
dependencies = []
```

Development-only dependencies belong in:

```toml
[project.optional-dependencies]
dev = []
```

Optional HTTP presentation dependencies belong in the separate `web` extra so
core Solara installations remain dependency-light.

A dependency should be introduced only when there is a current requirement for
it.

Before adding a library, consider:

- whether the Python standard library is sufficient;
- whether the dependency belongs in core logic or only infrastructure;
- whether it supports all supported Python versions;
- whether it introduces significant transitive complexity;
- whether it is actively maintained;
- whether the functionality is genuinely required now;
- whether the dependency would unnecessarily couple Solara to a framework.

Do not add a library merely because the original prototype used it.

## Source layout

Solara uses a `src` package layout.

The Python import package is:

```text
solara_travel
```

Application code belongs under:

```text
src/solara_travel/
```

Tests belong under:

```text
tests/
```

Do not manipulate `sys.path` inside tests to make imports work.

The installed package should resolve correctly through normal packaging.

## Branch workflow

Development follows a feature-branch and pull-request workflow.

Before beginning any new change:

```powershell
git switch main
git fetch origin
git pull --ff-only origin main
git status --short --branch
```

Confirm that:

- `main` is current with `origin/main`;
- the working tree is clean;
- no unrelated local changes are present.

Create one fresh branch for one coherent change:

```powershell
git switch -c feature/<descriptive-name>
```

Examples:

```text
feature/core-domain-models
feature/traveller-preferences
feature/provider-contracts
feature/weather-intelligence
feature/recommendation-service
```

Do not reuse old feature branches for unrelated work.

Do not begin a new feature directly on `main`.

## Commit scope

Each commit should represent one understandable development step.

A good commit should be:

- coherent;
- independently reviewable;
- focused on one responsibility;
- accompanied by relevant tests;
- free of unrelated cleanup;
- small enough that its architectural intent is clear.

Avoid mixing unrelated:

- documentation changes;
- dependency upgrades;
- refactors;
- formatting-only changes;
- feature implementation;
- infrastructure changes.

Related work may remain in the same commit when it is genuinely required to
deliver one coherent change.

A small number of related files is preferable to a large cross-project rewrite
when the work can reasonably be separated.

## Test-first development

Behaviour should generally be introduced using a test-first workflow.

The preferred sequence is:

1. define the expected behaviour;
2. identify important valid and invalid cases;
3. add focused tests;
4. run the tests and confirm the new behaviour is not already implemented;
5. implement the smallest clear solution;
6. rerun the focused tests;
7. run the complete test suite;
8. run static analysis;
9. review the diff;
10. commit only after the change is understood and validated.

Tests should describe behaviour rather than merely mirror implementation
details.

## Testing principles

Tests should be:

- deterministic;
- isolated;
- readable;
- fast;
- explicit about intent;
- independent of external credentials by default.

The normal unit test suite must not require:

- Google API credentials;
- OpenAI credentials;
- weather-provider credentials;
- internet access;
- external databases;
- third-party services.

External dependencies should be represented through fakes, fixtures, or
deterministic test adapters where appropriate.

## Test organization

As the project grows, tests should generally reflect architectural boundaries.

Potential structure:

```text
tests/
├── domain/
├── analytics/
├── application/
├── infrastructure/
└── presentation/
```

Directories should be introduced only when there are tests that belong in them.

Do not create empty test hierarchies merely for visual symmetry.

## Domain tests

Domain tests should verify:

- valid construction;
- invalid construction;
- invariants;
- value semantics;
- boundary conditions;
- domain-specific validation;
- behaviour that belongs to travel concepts themselves.

Domain tests must not depend on infrastructure.

## Analytics tests

Analytics tests should verify deterministic behaviour such as:

- normalization;
- score boundaries;
- weighting;
- ranking;
- ordering;
- edge cases;
- preference matching;
- climate suitability;
- explainable score components.

Analytics tests must remain independent of network access.

## Application tests

Application tests should verify orchestration.

Use fake implementations of ports to test:

- provider collaboration;
- recommendation workflows;
- result assembly;
- partial failures;
- optional integrations;
- no-result behaviour;
- application policy.

Application tests should not require real external providers.

## Infrastructure tests

Infrastructure tests should verify adapter-specific behaviour such as:

- provider response mapping;
- normalization;
- error translation;
- malformed responses;
- unit conversions;
- provider-specific pagination;
- authentication configuration boundaries.

Live integration tests may eventually exist, but they should remain separate
from the normal unit suite.

## Presentation tests

Presentation tests should verify:

- request translation;
- response translation;
- validation behaviour;
- HTTP or CLI boundaries;
- presentation-specific error behaviour.

They should not duplicate the entire domain or analytics test suite.

## Running tests

Run the complete test suite with:

```powershell
python -m pytest
```

Run tests with coverage:

```powershell
python -m pytest --cov=solara_travel --cov-branch --cov-report=term-missing
```

Statement and branch coverage must remain at 100%. This is a regression gate,
not proof that the tests are meaningful by itself.

A high percentage does not replace meaningful behavioural tests.

The normal test suite is offline and credential-free. Provider integrations
must use deterministic test doubles rather than live services.

When coverage is reported, focus particularly on:

- domain rules;
- analytics calculations;
- application orchestration;
- failure paths;
- meaningful edge cases.

## Static analysis

Solara uses Ruff for static analysis.

Run:

```powershell
python -m ruff check .
```

The current rule categories include:

- pycodestyle errors;
- Pyflakes;
- import sorting;
- common bugbear rules.

Do not disable lint rules globally merely to make a local issue disappear.

If a rule genuinely conflicts with a documented design decision, prefer the
smallest possible scoped exception and explain why it exists.

## Formatting

Code should remain readable and consistent.

Ruff's formatting check is:

```powershell
python -m ruff format --check .
```

The repository-wide formatting baseline must be normalized in a dedicated,
reviewable commit before this command becomes an enforced CI gate. Until then,
use it to identify drift in files you modify and avoid broad incidental changes.

Avoid cosmetic rewrites of unrelated files while implementing a feature.

Formatting changes should be limited to the files being meaningfully modified
unless a dedicated formatting change has been intentionally planned.

## Type annotations

Public APIs and important internal boundaries should use clear type annotations.

Types should communicate domain intent.

Prefer:

```python
def score_destination(
    destination: Destination,
    preferences: TravellerPreferences,
) -> RecommendationScore:
    ...
```

over vague structures such as:

```python
def score_destination(data: dict, prefs: dict) -> dict:
    ...
```

Avoid:

- `Any` where a meaningful type can be expressed;
- provider dictionaries propagating into core logic;
- generic mappings used as substitutes for domain models;
- SDK response objects becoming application contracts.

Provider-specific data should be normalized at infrastructure boundaries.

## Domain modelling

Domain models should represent meaningful travel concepts.

A model should exist because Solara needs the concept, not because an API
returns a similarly shaped object.

Domain models should:

- enforce meaningful invariants;
- use clear names;
- avoid provider coupling;
- expose intentional behaviour;
- remain testable without infrastructure.

Do not create large universal models containing every field that every provider
might someday return.

## Error handling

Errors should be explicit and meaningful.

Avoid broad patterns such as:

```python
try:
    ...
except Exception:
    return None
```

unless there is an exceptional and well-documented boundary reason.

When translating failures:

- preserve useful causes;
- distinguish user-input failures from provider failures;
- avoid hiding programming errors;
- avoid leaking arbitrary provider exceptions through application boundaries.

Where appropriate, use exception chaining:

```python
raise ProviderUnavailableError(...) from exc
```

## Deterministic logic

Deterministic behaviour should remain normal program logic.

Examples include:

- validation;
- date calculations;
- normalization;
- scoring;
- weighting;
- filtering;
- sorting;
- climate comparison;
- preference matching;
- ranking.

Do not use an LLM for deterministic calculations merely because an LLM is
available.

Deterministic logic should be directly testable.

## AI-assisted behaviour

AI models should be treated as optional infrastructure.

Possible uses include:

- recommendation explanation;
- summary generation;
- traveller-friendly narratives;
- itinerary prose;
- conversational experiences.

AI models should consume grounded application results.

They should not silently become the source of truth for:

- recommendation scores;
- destination eligibility;
- deterministic ranking;
- numeric calculations;
- known provider facts.

Useful recommendation results should remain available when the AI integration
is unavailable.

## External providers

External capabilities should be accessed through Solara-owned ports.

Application code should depend on interfaces such as:

```text
PlacesProvider
WeatherProvider
NarrationProvider
```

rather than importing vendor clients directly.

Infrastructure adapters should translate provider-specific data into
Solara-owned representations before returning it to application services.

## Offline recommendation workflow

Solara includes an explicit offline composition for deterministic development,
documentation, and end-to-end testing without credentials or network access. It
uses bundled normalized fixture values while retaining `RecommendationService`
as the application orchestrator, so provider ports, domain values, seasonality
analytics, scoring, evidence, ranking, and result assembly follow the same path
used by live-provider composition.

The bundled destinations, attractions, and historical weather are synthetic
Fixtureland data. They must never be presented as live, current, or authoritative
travel evidence. Offline providers are selected explicitly; they are not a
fallback when a live provider fails.

The default fixtures cover April 10 through April 12 across 2020 through 2024.
Calendar coverage is intentionally limited. Requests for unsupported calendar
windows may fail because the workflow does not fabricate missing evidence.

```python
from datetime import date

from solara_travel.domain import (
    RecommendationRequest,
    TemperatureComfortRange,
    TravelPeriod,
)
from solara_travel.workflows import build_offline_recommendation_service

service = build_offline_recommendation_service(
    comfort_range=TemperatureComfortRange(
        minimum_celsius=18.0,
        maximum_celsius=28.0,
        tolerance_celsius=10.0,
    )
)

result = service.recommend(
    RecommendationRequest(
        travel_period=TravelPeriod(
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 12),
        )
    )
)
```

## Grounded AI narration

Narration runs after `RecommendationService` has produced its authoritative
deterministic result. The model receives only structured Solara-owned grounding
and cannot select destinations, change ranks or scores, or add evidence. All
traveller and provider strings in that grounding are untrusted data; trusted
instructions require the model to ignore instructions found there and prohibit
presenting historical seasonal evidence as current weather or a forecast.

The OpenAI adapter uses the Responses API with an explicitly selected model,
`store=false`, a bounded output size, and no tools or conversation state. The
following is manual caller code; `gpt-5.6` is an example compatible model, not an
architectural constant:

```python
import os

from solara_travel.workflows import build_openai_recommendation_narration_service

narration_service = build_openai_recommendation_narration_service(
    api_key=os.environ["OPENAI_API_KEY"],
    model="gpt-5.6",
)
narrated_result = narration_service.narrate(result)
```

Expected provider authentication, rate-limit, response, and availability
failures produce no narration while preserving the exact recommendation result.
Empty results skip the model call. Normal tests and CI use fake providers and
transports, require no API key, and never make a live AI request.

## FastAPI browser shell and recommendation API

Install local development and HTTP presentation dependencies with:

```powershell
python -m pip install -e ".[dev,web]"
```

Run the ASGI application locally with reload enabled for development only:

```powershell
python -m uvicorn solara_travel.presentation.api.app:app --reload
```

Open `http://127.0.0.1:8000/` to view the Solara browser shell. Its HTML,
stylesheet, scripts, and approved brand images are package-local and need no
browser-side credentials.
The form collects required start and end dates plus optional comma-separated
interests, preferred pace, and preferred climate. It sends same-origin JSON to
the recommendation API.

The current browser and API surface is deliberately limited to:

```text
GET /
GET /static/styles.css
GET /static/app.js
GET /static/results.js
GET /static/feedback.js
GET /static/branding/solara-logo-horizontal.png
GET /static/branding/solara-logo-stacked.png
GET /static/branding/solara-mark-gold.png
GET /static/branding/solara-logo-monochrome.png
GET /health
POST /api/v1/recommendations
POST /api/v1/feedback
GET /openapi.json
GET /docs
GET /redoc
```

Interactive Swagger and ReDoc pages are enabled by default. Creating the app
with `ApiSettings(docs_enabled=False)` disables `/docs` and `/redoc` while
retaining `/`, all packaged static resources, `/openapi.json`, and `/health`.
The browser root and static mount are not included in OpenAPI.

Health indicates only that the ASGI process is serving requests; it does not
check provider availability. The default module-level app has no recommendation
service configured, so a valid `POST /api/v1/recommendations` returns `503`
until application composition supplies `ApiDependencies`. This does not prevent
the browser shell and its assets from rendering, but the form receives the safe
`recommendation_service_unconfigured` response until a service is supplied.

A recommendation request uses this shape:

```json
{
  "travel_period": {
    "start_date": "2026-04-10",
    "end_date": "2026-04-12"
  },
  "preferences": {
    "interests": ["nature"],
    "preferred_pace": "relaxed",
    "preferred_climate": "warm"
  },
  "destination": null
}
```

The browser constructs this `application/json` shape with `destination: null`
to use destination-discovery mode. It does not expose raw coordinate entry;
preselected destinations remain available to programmatic API callers. Blank
optional fields serialize as `null`.

The form keeps native `required` semantics while using explicit accessible
browser feedback. Submission validates that both dates exist, the end date is
the same as or after the start date, comma-separated interests contain no blank
items, and interests do not repeat after trimming and ordinary case-insensitive
comparison. Valid interests preserve order and capitalization. Invalid input is
not repaired and does not reach `fetch`; field messages and a focusable summary
identify the problem while the server/domain remains authoritative.

Tests and local demonstrations compose the endpoint explicitly with offline or
fake services and need no credentials:

```python
from solara_travel.domain import TemperatureComfortRange
from solara_travel.presentation.api import ApiDependencies, create_app
from solara_travel.workflows import build_offline_recommendation_service

service = build_offline_recommendation_service(
    comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0)
)
app = create_app(
    dependencies=ApiDependencies(recommendation_service=service)
)
```

Without a narration service, successful responses contain `narration: null`.
When narration is configured, an AI-provider failure still returns the complete
deterministic result with no narration. Seasonal weather fields are aggregated
historical evidence, not current conditions or forecasts.

Current deterministic scoring is season-led. The optional interest, pace, and
climate values are preserved in the request but are not yet independent score
components. Browser request states are idle, validation error, loading, success,
successful empty, and request error. A valid submission disables the submit
button, marks the form busy, and announces loading. It dispatches
`solara:recommendation-request-start` before the request; `results.js` clears
old results only on that event, so local validation failures preserve the last
successful outcome.

The browser parses non-success JSON defensively and maps stable status/code
values to fixed local product copy. Structural and domain `422` responses may
be mapped to known fields; `502`, `503`, unexpected HTTP failures, malformed
successful JSON, and network rejection use a dedicated request-error region.
Raw server messages, provider details, and response bodies are not rendered.
Retry is offered only for transient states and calls `form.requestSubmit()`, so
it uses current values and the normal validation path. There is no automatic
retry or backoff. The default unconfigured app therefore presents its safe
`503` as a tester-friendly preview state rather than composing fixture
providers.

After a successful submission, `app.js` dispatches
`solara:recommendation-ready`; `results.js` renders the
`RecommendationResponse` without another request. Recommendation order, ranks,
scores, component values, and weighted contributions come directly from the
response and are not recomputed in the browser. A configured empty offline
service remains a successful `200` and produces a neutral empty-result state,
not an error or fabricated recommendation.

Each ranked card exposes selected attractions, historical seasonal aggregates,
and server-configured temperature-comfort evidence through native disclosure
controls. Optional narration appears separately only when supplied and is
rendered as plain text; it does not determine ranking. These browser paths use
no live credentials, client persistence, or browser-side provider calls.

### Premium presentation and brand assets

Commit 43 organizes the browser shell as a premium editorial landing experience with
a branded header, season-smart hero, supporting insight, integrated planner, curated
results, tester feedback, product principles, and footer. The redesign preserves the
existing semantic region IDs and JavaScript handoffs, so UI presentation changes do
not alter recommendation requests, ranking, result order, request tracing, or feedback
submission.

Approved assets are stored under:

```text
src/solara_travel/presentation/web/static/branding/
```

The stable asset names are `solara-logo-horizontal.png`,
`solara-logo-stacked.png`, `solara-mark-gold.png`, and
`solara-logo-monochrome.png`. Keep the original approved image bytes unchanged.
`pyproject.toml` must continue to include `static/branding/*.png` as package data;
package builds and clean-install checks must verify the nested files in both the
wheel and source distribution. Brand resources are served through the existing
same-origin `/static` mount. Do not replace them with external URLs, CDN fonts,
tracking pixels, or browser-side asset services.

Presentation CSS uses system font stacks, visible keyboard focus, touch-friendly
controls, narrow-screen layouts, and a reduced-motion mode. Decorative images use
empty alternative text; meaningful logo placements retain concise `Solara` text.
Static HTML contains no fixture destinations or pretend recommendations, and result
text continues to be created with safe DOM text APIs.

### Request tracing, structured events, and tester feedback

Every ordinary handled HTTP response includes a fresh server-generated UUID4 in
`X-Request-ID`. An inbound header with the same name is ignored rather than used
or echoed. Recommendation responses expose this opaque identifier in the browser
as a request reference; the value is held only in current DOM state so a later
feedback submission can refer to the relevant comparison. Local validation and
network failures do not create identifiers.

Inspect a response header locally with a credential-free request such as:

```powershell
curl.exe -i http://127.0.0.1:8000/health
```

The `solara_travel.api` logger writes versioned one-line JSON events to the
process logging stream. Its stable vocabulary is:

- `http.request.completed` and `http.request.exception` for safe HTTP outcome
  and duration metadata;
- `recommendation.completed` for aggregate count, narration availability, and
  deterministic/narration timings;
- `recommendation.failed` for translated provider failure categories;
- `recommendation.rejected` for invalid or unconfigured requests;
- `feedback.accepted` for explicit tester feedback and opaque linkage IDs.

Static assets and `/health` receive request IDs but are intentionally excluded
from request-event logs to limit hosted noise. Request events never contain
query strings, bodies, IP addresses, User-Agent strings, cookies, headers, or
response bodies. Recommendation events never contain travel dates, interests,
pace, climate, destinations, coordinates, scores, weather, provider payloads,
exception text, or narration. The one intentional free-text operational field
is the comment that a tester explicitly enters in the feedback form.

Feedback does not require recommendation-service configuration. Submit a benign
local example with:

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/api/v1/feedback `
  -H "Accept: application/json" `
  -H "Content-Type: application/json" `
  -d '{"rating":"helpful","comment":"The evidence view was clear."}'
```

The request schema accepts an optional UUID `recommendation_request_id`, a
required `helpful`, `mixed`, or `not_helpful` rating, and an optional comment of
at most 1,000 characters. Blank comments normalize to null and unknown fields
are rejected. A successful response is `202 Accepted` with only
`status: "accepted"` and a new feedback UUID; submitted values are not echoed.

The browser feedback form attaches its current recommendation request reference
when one exists, resets only after a successful response, and preserves entered
text after HTTP or network failure. It uses fixed local status copy and no
browser persistence, identity fields, analytics, client metadata, external
requests, or automatic retry.

For this alpha milestone, structured process logs are the feedback recording
mechanism. There is no database, file sink, forwarding service, retention job,
rate limiting, quota, cost control, abuse safeguard, or deployment configuration
yet. Commit 44 adds public-alpha safeguards before hosted release; Commit 45
deployment configuration work owns log transport and retention.

## Configuration

Configuration should be introduced when external services require it.

Configuration must:

- keep secrets out of source code;
- provide explicit environment-driven settings;
- avoid import-time provider initialization;
- avoid preventing domain modules from being imported when credentials are
  missing;
- distinguish required settings from optional integrations.

A missing optional AI credential should not prevent deterministic analytics from
being used.

## Secrets

Real credentials must never be committed.

The repository may eventually contain:

```text
.env.example
```

with empty placeholders for required configuration names.

It must never contain usable secrets.

If a secret is accidentally exposed:

1. revoke or rotate it;
2. remove it from active code;
3. investigate whether Git history or logs contain it;
4. do not assume deleting the latest file is sufficient remediation.

Private signing keys and their passphrases must also never be committed or
shared.

## Generated files

Normal local build and tooling artifacts should not be committed.

Examples include:

```text
.venv/
build/
dist/
.pytest_cache/
.ruff_cache/
*.egg-info/
.coverage
htmlcov/
```

Generated artifacts should only become tracked files when there is a deliberate
and documented reason.

## Package builds

For packaging-related changes, verify that the package builds successfully:

```powershell
python -m build
```

This should produce:

- a source distribution;
- a wheel.

Build artifacts belong under `dist/` and should remain untracked.

CI also installs the built wheel into a clean temporary environment, runs
`pip check`, and smoke-tests representative public imports. This prevents an
editable source checkout from hiding wheel packaging or dependency problems.

## Local validation

Before a pull request is opened, run:

```powershell
python -m ruff check .
python -m pytest
python -m pytest --cov=solara_travel --cov-branch --cov-report=term-missing
python -m build
git diff --check
```

Also inspect formatting drift while the repository formatting baseline is being
prepared:

```powershell
python -m ruff format --check .
```

Do not state that a command passed unless it was actually executed
successfully.

## Continuous integration

GitHub Actions separates failures into focused repository CI and security gates:

- Ruff lint and dependency consistency;
- tests on Python 3.11, 3.12, and 3.13 on Ubuntu;
- a separate 100% statement and branch coverage regression gate;
- the complete test suite on Windows with Python 3.13;
- source-distribution and wheel builds followed by a clean-install smoke test;
- pull-request dependency review that rejects newly introduced high or critical
  vulnerabilities;
- CodeQL `security-extended` analysis of Python source and GitHub Actions
  workflows;
- GitGuardian as an additional, independently operated repository security
  check.

The Ruff format gate will join these checks after the existing formatting drift
is normalized in its own commit. Branch and ruleset enforcement is configured
separately in GitHub settings; these checks are not automatically required merely
because their workflows exist.

A locally passing change does not justify ignoring a failing CI run.

CI failures should be investigated rather than bypassed.

## Reviewing changes before staging

Before staging files, inspect:

```powershell
git status --short
git diff --check
git diff
```

Review:

- unexpected files;
- accidental deletions;
- generated artifacts;
- unrelated changes;
- secrets;
- stale debug code;
- unintended formatting.

Deletions deserve the same level of review as additions.

## Staging

Stage only intended files.

Then inspect:

```powershell
git status --short
git diff --staged --stat
git diff --staged
```

Do not assume that because a file was intentionally edited, every line in its
diff is intentional.

## Commit messages

Use concise conventional-style commit messages.

Examples:

```text
chore: rebuild project foundation
docs: define product architecture
docs: add development workflow
feat: add destination domain model
feat: add traveller preferences
feat: define weather provider contract
test: cover destination validation
fix: reject invalid travel periods
```

The commit subject should describe what the change accomplishes.

Avoid vague messages such as:

```text
updates
changes
fix stuff
work
```

## Signed commits

Solara's protected `main` branch requires verified commits.

Local Git is configured to use SSH commit signing.

Automatic commit signing should remain enabled through:

```text
commit.gpgsign=true
```

Before pushing rewritten commit history, a signature may be checked with:

```powershell
git cat-file -p HEAD | Select-String "gpgsig"
```

Never expose:

- the private signing key;
- the signing-key passphrase.

Only the public signing key should be registered with GitHub.

## Pull requests

Every meaningful feature should be delivered through a pull request.

A pull request description should include:

- what changed;
- why the change was needed;
- important architectural decisions;
- tests performed;
- known limitations;
- intentionally deferred work.

The actual diff must be reviewed even when all automated checks pass.

Automation supplements review; it does not replace review.

## Pull request approval

Protected branches require review before merge.

When a commit is rewritten or force-pushed, stale approvals may be dismissed.

The latest review should always apply to the exact commit being merged.

Do not weaken branch rules merely to avoid repeating review when the underlying
commit changed.

## Merge strategy

Feature pull requests should normally use:

```text
Squash and merge
```

This keeps `main` linear while allowing iterative work on a feature branch.

Do not bypass repository protections merely because a merge is blocked.

When GitHub blocks a merge:

1. identify the exact unmet rule;
2. determine whether the rule represents an intentional policy;
3. correct the commit, review, check, or repository configuration as
   appropriate;
4. merge normally once the requirements are satisfied.

Bypass should remain exceptional.

## Force pushes

Force pushes to protected branches should remain blocked.

A feature branch may occasionally require rewritten history, such as when
amending a commit signature.

In that situation use:

```powershell
git push --force-with-lease
```

rather than:

```powershell
git push --force
```

`--force-with-lease` provides protection against accidentally overwriting remote
changes that are not represented in the local remote-tracking state.

## Documentation

Documentation should describe current truth.

When discussing future architecture or features, clearly label them as:

- planned;
- intended;
- proposed;
- future;
- potential.

Do not describe unimplemented functionality as though it already exists.

Documentation should be updated when a change materially affects:

- product behaviour;
- architecture;
- development workflow;
- configuration;
- external integrations;
- user-facing setup.

## Comments

Comments should explain:

- decisions;
- invariants;
- constraints;
- trade-offs;
- non-obvious reasoning.

Avoid comments that simply translate code into English.

For example, avoid:

```python
# Increment count by one.
count += 1
```

Prefer comments that explain why behaviour exists when that reason is not
obvious from the implementation itself.

## Architectural changes

Significant architectural changes should answer:

- What concrete problem does this solve?
- Why is the existing architecture insufficient?
- Which boundary changes?
- Which dependency direction changes?
- How will the new behaviour be tested?
- What complexity is being introduced?
- Is there a simpler solution?

Do not introduce technologies such as:

- vector databases;
- RAG;
- multi-agent systems;
- message queues;
- microservices;
- Kubernetes;
- distributed event systems;
- complex databases;

without a demonstrated product requirement.

## Provider selection

Provider selection should remain an infrastructure concern.

Choosing a different:

- weather provider;
- places provider;
- mapping provider;
- AI provider;

should not require rewriting core domain or analytics logic.

If replacing a provider would require a large core rewrite, the architectural
boundary should be reconsidered.

## Performance

Do not optimize prematurely.

First establish:

- correct behaviour;
- meaningful tests;
- understandable architecture.

Performance optimization should follow measured evidence.

Potential future metrics may include:

- recommendation latency;
- provider latency;
- scoring time;
- cache hit rate;
- API throughput;
- AI generation latency.

## Security

Treat all external input as untrusted.

This includes:

- user input;
- API responses;
- imported files;
- generated content;
- provider metadata.

Validation and normalization should occur at appropriate boundaries.

Security-sensitive functionality should be added deliberately rather than
assumed to be handled automatically by frameworks.

## Definition of done

A development change is ready for review when:

1. the intended behaviour is clearly implemented;
2. relevant focused tests pass;
3. the complete test suite passes;
4. Ruff passes;
5. `git diff --check` passes;
6. packaging validation passes when relevant;
7. the diff contains only intended changes;
8. no secrets or local artifacts are included;
9. documentation is updated where behaviour or architecture changed;
10. the change is committed on a dedicated feature branch;
11. the feature branch is pushed;
12. the pull request clearly explains the change;
13. the pull request is reviewed before merge.

## Guiding principle

Solara should become sophisticated only when the product requires
sophistication.

Every new abstraction, dependency, framework, service, and layer should make a
real problem easier to solve, easier to test, or easier to maintain.
