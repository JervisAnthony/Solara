# Solara Deployment Configuration

## Scope and architecture

Commit 45 prepares Solara for a portable hosted MVP1 deployment. It does not
create a hosting account, public URL, production service, or infrastructure.
Those operations remain Commit 46.

The hosted entrypoint follows one explicit composition path:

```text
environment variables
        |
        v
solara_travel.config
        |
        v
hosted provider workflow
        |
        v
ApiSettings + ApiDependencies
        |
        v
create_app()
```

`create_deployment_app()` builds a fresh dependency graph on each invocation.
It validates local configuration and creates clients, but it does not contact
Google Places, Open-Meteo, or OpenAI at startup. The ordinary `create_app()`
remains credential-free for development, tests, and library use.

## Required variables

The hosted MVP1 requires all three values, with no defaults:

```text
SOLARA_GOOGLE_PLACES_API_KEY
SOLARA_OPENAI_API_KEY
SOLARA_OPENAI_MODEL
```

Blank values are invalid. Missing variables are reported together by name;
their values are never included in configuration errors. Use the hosting
platform's secret store, for example:

```text
SOLARA_GOOGLE_PLACES_API_KEY=<set-in-host-secret-store>
SOLARA_OPENAI_API_KEY=<set-in-host-secret-store>
SOLARA_OPENAI_MODEL=<set-model-name>
```

The Google and OpenAI key fields are also excluded from dataclass repr output.
Never commit a populated `.env` file, credential JSON, or provider key.

## Optional variables and defaults

| Variable | Default |
| --- | ---: |
| `SOLARA_DOCS_ENABLED` | `false` |
| `SOLARA_GOOGLE_PLACES_TIMEOUT_SECONDS` | `10` |
| `SOLARA_GOOGLE_PLACES_DESTINATION_PAGE_SIZE` | `10` |
| `SOLARA_GOOGLE_PLACES_ATTRACTION_MAX_RESULTS` | `20` |
| `SOLARA_GOOGLE_PLACES_ATTRACTION_RADIUS_METERS` | `30000` |
| `SOLARA_OPEN_METEO_TIMEOUT_SECONDS` | `10` |
| `SOLARA_OPENAI_TIMEOUT_SECONDS` | `30` |
| `SOLARA_OPENAI_MAX_OUTPUT_TOKENS` | `1200` |
| `SOLARA_HISTORICAL_START_DATE` | `2020-01-01` |
| `SOLARA_HISTORICAL_END_DATE` | `2024-12-31` |
| `SOLARA_COMFORT_MIN_CELSIUS` | `18` |
| `SOLARA_COMFORT_MAX_CELSIUS` | `28` |
| `SOLARA_COMFORT_TOLERANCE_CELSIUS` | `10` |
| `SOLARA_SEASONAL_WEIGHT` | `1.0` |
| `SOLARA_RECOMMENDATION_RATE_LIMIT` | `12` |
| `SOLARA_RECOMMENDATION_RATE_WINDOW_SECONDS` | `60` |
| `SOLARA_RECOMMENDATION_BUDGET_LIMIT` | `60` |
| `SOLARA_RECOMMENDATION_BUDGET_WINDOW_SECONDS` | `3600` |
| `SOLARA_RECOMMENDATION_CONCURRENCY_LIMIT` | `2` |
| `SOLARA_FEEDBACK_RATE_LIMIT` | `30` |
| `SOLARA_FEEDBACK_RATE_WINDOW_SECONDS` | `60` |
| `SOLARA_NARRATION_BUDGET_LIMIT` | `30` |
| `SOLARA_NARRATION_BUDGET_WINDOW_SECONDS` | `3600` |
| `PORT` | `8000` |

Boolean values accept case-insensitive `true` or `false`. Numeric and ISO-date
values are validated before Uvicorn starts. Provider endpoints are trusted code
constants and cannot be changed through the environment.

## Local environment use

[`.env.example`](../.env.example) is a reference template only. Solara does not
load `.env` files and has no dotenv dependency. Set variables in the current
shell or inject an explicit mapping in tests.

PowerShell example:

```powershell
$env:SOLARA_GOOGLE_PLACES_API_KEY = "<set-in-host-secret-store>"
$env:SOLARA_OPENAI_API_KEY = "<set-in-host-secret-store>"
$env:SOLARA_OPENAI_MODEL = "<set-model-name>"
python -m solara_travel.presentation.api.server
```

Configuration is loaded when the Uvicorn application factory is invoked, not
when config or deployment modules are imported. Invalid or missing required
values stop startup with a safe `DeploymentConfigurationError`.

## Docker build and run

Build the Python 3.13 slim, non-root runtime image:

```powershell
docker build --tag solara-deployment:local .
```

Run it with secrets injected at runtime:

```powershell
docker run --rm --name solara-deployment `
  --publish 8000:8000 `
  --env SOLARA_GOOGLE_PLACES_API_KEY="<set-in-host-secret-store>" `
  --env SOLARA_OPENAI_API_KEY="<set-in-host-secret-store>" `
  --env SOLARA_OPENAI_MODEL="<set-model-name>" `
  solara-deployment:local
```

`GET /health` is the container liveness check. It proves that the ASGI process
is serving and deliberately does not spend provider quota or depend on provider
availability. API documentation is disabled by default (`/docs` and `/redoc`
return 404), while `/openapi.json` retains the existing application behavior.

## Public-alpha process policy

The server always uses exactly one Uvicorn worker, with `access_log=False`,
`proxy_headers=False`, and the server header disabled. Solara's structured,
privacy-conscious request events remain the handled-request log; forwarding
headers are not trusted for identity or limits.

Commit 44 safeguards are process-local and reset on restart. MVP1 must therefore
start with one worker and one container/instance. Horizontal replicas would
multiply effective limits and require a future shared or distributed safeguard
design. These limits reduce abuse and spend risk but are not a guaranteed cost
ceiling.
