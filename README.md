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

Build the source distribution and wheel:

```powershell
python -m build
```

## Deployment configuration

Commit 45 adds a portable, environment-driven hosted application factory and
Docker image configuration. The hosted factory requires
`SOLARA_GOOGLE_PLACES_API_KEY`, `SOLARA_OPENAI_API_KEY`, and
`SOLARA_OPENAI_MODEL`; [.env.example](.env.example) lists every supported
variable and safe default. Solara does not load that file automatically, and
real credentials must come from the hosting platform's secret store.

See the [deployment configuration guide](docs/deployment.md) for local and
container commands. This repository is prepared for deployment but is not yet
publicly hosted; hosted MVP1 deployment remains Commit 46.

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
