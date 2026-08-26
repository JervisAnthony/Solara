# 🌞 Solara

### *Season-smart, preference-aware, and explainable travel intelligence*

Solara is an evolving AI-assisted travel platform designed to help travellers
discover destinations and experiences that suit their timing, preferences,
budget, and trip context.

Rather than recommending places solely because they are popular, Solara aims to
explain why a destination or attraction may be suitable for a particular
traveller at a particular time.

## Project status

Solara is currently in **pre-alpha development** and is undergoing a clean,
test-first architectural rebuild.

The original prototype explored:

- attraction discovery;
- historical weather analysis;
- popularity scoring;
- seasonal travel recommendations;
- AI-generated recommendation summaries.

That prototype has been retired from the active codebase and remains available
through Git history. Useful ideas from it will be reintroduced only after their
responsibilities, boundaries, and expected behaviour are clearly defined and
tested.

The current implementation provides the Python package and engineering
foundation. Travel recommendation functionality has not yet been reintroduced.

## Product vision

Solara is intended to help travellers answer questions such as:

- Where should I travel during a particular month or season?
- Which destinations best match my interests and travel style?
- How suitable is a destination for my preferred weather?
- Which attractions are genuinely relevant to my trip?
- Why was one destination ranked above another?
- How can a trip be planned around time, budget, comfort, and priorities?

Recommendations should remain understandable, evidence-aware, and explicit
about uncertainty.

## Planned capabilities

Solara is planned to support:

- destination and attraction discovery;
- seasonal and climate-suitability analysis;
- traveller preferences and trip styles;
- deterministic and explainable recommendation scoring;
- budget-aware and duration-aware recommendations;
- personalized itinerary generation;
- AI-assisted recommendation narratives;
- practical travel guidance and preparation;
- API, web, and desktop-facing experiences.

Planned capabilities are not presented as implemented functionality.

## Engineering principles

Solara is being developed with the following principles:

- domain logic remains independent of external APIs and AI providers;
- deterministic computation is preferred where deterministic answers are possible;
- AI-generated content explains recommendations rather than replacing core rules;
- external providers are accessed through replaceable interfaces;
- important behaviour is introduced with focused automated tests;
- recommendations distinguish evidence, assumptions, and generated guidance;
- development proceeds through small, reviewed feature branches and pull requests.

## Requirements

- Python 3.11 or newer
- Git

Python 3.13 is used for local development.

## Development setup

Create and activate a virtual environment on Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Upgrade pip and install Solara with its development dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev,web]"
```

## Quality checks

Run static analysis:

```powershell
python -m ruff check .
```

Run the test suite:

```powershell
python -m pytest
```

Run tests with coverage:

```powershell
python -m pytest --cov=solara_travel --cov-report=term-missing
```

Run the deterministic local Chromium smoke suite (no provider credentials or
live provider calls):

```powershell
python -m pip install -e ".[browser,dev,web]"
python -m playwright install chromium
python -m pytest tests/browser
```

Build the source distribution and wheel:

```powershell
python -m build
```

## Hosted MVP1 deployment

Commit 45 adds a portable, environment-driven hosted application factory and
Docker image configuration. The hosted factory requires
`SOLARA_GOOGLE_PLACES_API_KEY`, `SOLARA_OPENAI_API_KEY`, and
`SOLARA_OPENAI_MODEL`; [.env.example](.env.example) lists every supported
variable and safe default. Solara does not load that file automatically, and
real credentials must come from the hosting platform's secret store.

The hosted MVP1 deployment is live at
[https://solara-travel-mvp1.onrender.com](https://solara-travel-mvp1.onrender.com).
It runs on Render Free in Singapore as one Docker web service, one instance, and
one Uvicorn worker. `GET /health` is the health check; hosted API documentation
is disabled. Idle spin-down can cause cold starts. The public-alpha planner
accepts up to 15 selected cities, countries, regions, provinces, island groups,
or similar geographic scopes in any supported combination, as well as blank
worldwide discovery. Guided interests, stable pace and climate choices,
and an optional natural-language trip description help express the trip without
requiring technical vocabulary. Public result cards present the current
seasonal-temperature score as a readable seasonal-fit percentage; interests and
travel-style preferences are request context, not yet independent numeric
ranking factors. Commit 47's
explicit-destination public-alpha acceptance passed against the hosted service.
Commit 48 is complete. Its exact hosted build at
`c9d698ad5e926beb4e6cad1c291f6d4a786c479c` was manually reviewed and accepted.
Phase 1 introduced an editorial travel homepage, locally bundled destination
photography, curated Popular Escapes inspiration, and a compact planner. Phase
2A added calm hero and carousel motion, traveller-facing guidance,
same-origin geographic suggestions, and beta-stage locality discovery within
selected broad scopes. Explicit localities are reserved first; countries and
regions expand into concrete contained localities through fair allocation. AI
may propose bounded candidate pools for broad or blank discovery, but Google
must validate every locality and Solara's
existing deterministic seasonal evidence still owns final scores and ranking.
Explicit-city comparisons do not call candidate-proposal AI. Phase 2B
experience expands the local hero and Popular Escapes catalogue to
exactly twelve credited destinations with three-second, reduced-motion-aware
movement. The planner now uses accessible premium pace and climate listboxes and
a full-width natural-language composer. Results are traveller-first destination
stories: transient Google Places Photos (New) imagery appears as Postcards;
strict structured narration appears as The Wayfinder; and the UI prioritizes
Seasonal Fit, Places to see, editorial Seasonal feel, and grounded destination-
character Good to know. The generic historical-not-forecast note appears once
for the result, and Good to know is omitted when trusted non-seasonal grounding
is insufficient. No more than 15 concrete destinations proceed to evidence and
scoring. Neither enrichment can rank or rescore, and either may fail without
losing the deterministic result. The next planned milestone is Commit 49 -
Itinerary Studio / Build This Trip. Destination Knowledge + RAG Grounding is
deferred entirely to MVP2, and no vector database provider has been selected.
Bookings and accounts remain pending.

See the [deployment guide](docs/deployment.md) for local, container, and hosted
operational details.

## Current structure

```text
Solara/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
├── src/
│   └── solara_travel/
│       └── __init__.py
├── tests/
│   └── test_package.py
├── .gitignore
├── LICENSE
├── README.md
└── pyproject.toml
```

The architecture will grow incrementally through small, reviewed commits.

## Documentation

- [Product scope](docs/product-scope.md)
- [Architecture](docs/architecture.md)
- [Development guide](docs/development.md)
- [Deployment configuration](docs/deployment.md)
- [Roadmap](docs/roadmap.md)

## Package names

- Product name: `Solara`
- Python distribution: `solara-travel-ai`
- Python import package: `solara_travel`

The distinct Python import name avoids collision with the unrelated package
distributed under the name `solara`.

## License

Solara is licensed under the MIT License.

## Author

Jervis Anthony Saldanha
