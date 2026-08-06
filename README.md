# 🌞 Solara
### *Season-smart travel insights powered by AI*


## Project status

Solara is currently undergoing a clean architectural re-foundation.

The original prototype explored:

- attraction discovery;
- historical weather analysis;
- popularity scoring;
- seasonal travel recommendations;
- AI-generated recommendation summaries.

Those ideas are being rebuilt using a test-first architecture with clear
separation between domain logic, application services, external providers,
analytics, workflows, and presentation layers.

The current development version establishes the Python package and engineering
foundation. Production travel-recommendation functionality has not yet been
reintroduced.

## Planned capabilities

Solara is intended to support:

- destination and attraction discovery;
- climate and seasonal suitability analysis;
- traveller preferences and trip styles;
- deterministic and explainable recommendation scoring;
- budget-aware and duration-aware recommendations;
- personalized itinerary generation;
- AI-assisted recommendation narratives;
- API, web, and desktop-facing experiences.

Planned features are not presented as implemented functionality.

## Requirements

- Python 3.11 or newer
- Git

## Development setup

Create and activate a virtual environment on Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1