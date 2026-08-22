# Solara Deployment Configuration

## Scope and architecture

Commit 45 prepares Solara for a portable hosted MVP1 deployment. Commit 46
establishes the first live public-alpha service on Render and adds the
repository-side definition of its intended configuration. Provider-backed
recommendation, narration, feedback, and broader browser validation remain
Commit 47.

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

## Render MVP1 Blueprint

The live deployment is:

| Setting | Value |
| --- | --- |
| Provider | Render |
| Service | `solara-travel-mvp1` |
| Public URL | <https://solara-travel-mvp1.onrender.com> |
| Region | Singapore |
| Runtime | Docker |
| Plan | Free |
| Source | GitHub `main` |
| Deployed baseline | `f325e419af1e7a88963c581c5d81ac9473de44fe` |
| Topology | One service, one instance, one Uvicorn worker |
| Health endpoint | `/health` |
| Hosted API docs | Disabled |
| Auto-deploy policy | After CI checks pass |
| Render hostname | Enabled |
| Narration model | `gpt-5.6-luna` |

The existing service was manually provisioned from the already-merged `main`
baseline because [`render.yaml`](../render.yaml) existed only on the local
Commit 46 branch at the time. The live service is therefore **not yet managed by
a Render Blueprint**. The file captures the canonical desired MVP1 Render
configuration. After Commit 46 reaches a remote branch or `main`, the operator
can match the existing `solara-travel-mvp1` service and synchronize it with a
Blueprint. Do not create a second service, and keep existing secret values in
Render rather than moving them into source control.

The Blueprint declares one `solara-travel-mvp1` Docker web service on Render
Free in Singapore, with exactly one instance. It builds the root `Dockerfile`,
lets Render provide `PORT`, and lets the Dockerfile `CMD` start the server. No
database, Key Value/Redis, worker, cron job, preview environment, autoscaling,
or separate frontend exists.

The long-term deployment branch is `main`. Render's Git integration deploys
after the linked branch's CI checks pass. `GET /health` is the service health
check, and the Render-provided HTTPS hostname remains enabled. No custom domain,
Render API token, or GitHub Actions deployment credential is configured.

The Blueprint declares `SOLARA_GOOGLE_PLACES_API_KEY` and
`SOLARA_OPENAI_API_KEY` with `sync: false`. During initial provisioning, enter
the real values only through Render's environment/secret interface. All other
hosted policy values are explicit strings in the Blueprint. Hosted API docs are
disabled, and the initial optional narration model is `gpt-5.6-luna` because
narration is cost-sensitive and follows the authoritative deterministic
recommendation. Changing that model requires a reviewed deployment
configuration change.

### Free-instance trade-offs

Render Free may spin down after inactivity, cold-start on the next request, and
restart. Solara's safeguards are process-local, so a restart resets their state.
This one-instance design is an MVP1 trade-off, not an always-on or
production-grade guarantee, and the safeguards reduce risk without imposing a
financial hard cap. Do not add self-pings, scheduled keepalive traffic, or an
external wake-up service; upgrade the instance if always-on behavior becomes a
requirement.

Render terminates TLS and supplies the initial managed HTTPS hostname. Solara
does not add certificate code, HTTPS redirect middleware, or a custom domain for
MVP1. The deployment server continues to use `proxy_headers=False` and
`access_log=False`.

### Provider credential checklist

Before launch, the operator must:

- create or use a dedicated server-side Google Maps Platform key for Solara;
- enable and restrict that key to Places API (New), the API used by the current
  text-search and nearby-search adapter;
- keep the key out of browser JavaScript and source, and store it only in
  Render's environment/secret configuration;
- set Google Cloud usage and quota controls appropriate for the public alpha,
  without claiming an IP restriction that has not been configured;
- use an OpenAI API project intended for Solara and store its key only in
  Render, never in source or browser code;
- limit project model access where supported and configure operator-owned usage
  or budget alerts and spending controls.

For the first deployment, the dedicated Google key was rotated before launch
and restricted to Places API (New). No application/IP restriction is claimed:
that remains intentionally unconfigured until a stable outbound-IP restriction
is verified. Google Cloud billing is enabled for the dedicated project; quotas,
budgets, and provider billing still require operator monitoring.

The OpenAI key belongs to the dedicated Solara Travel API project and is scoped
to write access for the Responses endpoint. Unnecessary API capabilities are
disabled. The project uses conservative prepaid billing with auto-reload off,
but neither provider controls nor Solara's safeguards constitute a guaranteed
hard cost ceiling.

### First deployment checklist

- [x] Render account and `solara-travel-mvp1` service created
- [x] GitHub repository connected with `main` selected
- [x] Docker runtime, Singapore region, and Free instance selected
- [x] One-service, one-instance, one-worker topology preserved
- [x] Google Places and OpenAI secrets configured server-side
- [x] `gpt-5.6-luna` model configured and hosted docs disabled
- [x] `/health` configured and auto-deploy set to After CI Checks Pass
- [x] Docker image built and application process started successfully
- [x] Managed HTTPS endpoint assigned: <https://solara-travel-mvp1.onrender.com>
- [x] `GET /health` verified as `200` with `{"status":"ok"}`
- [x] `GET /` verified as `200`
- [x] `GET /docs` and `GET /redoc` verified as `404`
- [x] Premium Solara shell and approved branding rendered
- [ ] Existing service adopted by a Render Blueprint after Commit 46 is remote

Commit 47 remains responsible for:

- real Google Places, Open-Meteo evidence, and OpenAI narration flows;
- complete recommendation and error-state browser interaction;
- tester feedback submission and repeated-click behavior;
- responsive/mobile checks and cold-start user experience;
- public-alpha copy cleanup, including review of `DEVELOPMENT PREVIEW`;
- the broader public-alpha browser smoke suite.

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
