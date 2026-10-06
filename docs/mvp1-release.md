# MVP1 release candidate: 0.1.0 public alpha

Commit 51 is **IN PROGRESS — Phase A release candidate**. Hosted acceptance and
the launch decision are **PENDING**. MVP1 is **NOT YET CLOSED**. Local validation
is recorded in [the Phase A report](commit51-phase-a-validation.md).

Package version `0.1.0` identifies the alpha package; a Git SHA identifies a
deployed revision; each functional asset's SHA-256 prefix identifies its bytes.
No release tag or GitHub Release is created in Phase A. The candidate SHA cannot
be recorded until the owner commits and pushes the staged work.

## Product and architecture

MVP1 supports explicit-city evaluation, comparisons, country/region/mixed-scope
and worldwide discovery, with up to 15 selected scopes and 15 concrete candidates.
Google Places validates locality identity and containment. Open-Meteo supplies
historical seasonal evidence. Deterministic analytics own eligibility, Seasonal
Fit and ordering. OpenAI proposes bounded discovery candidates and supplies
optional narration; neither can override evidence or ranking. Hard cold/snow
requirements exclude candidates without supporting evidence. Interests, pace
and trip descriptions guide discovery and presentation without becoming invented
numeric score components. Historical conditions are not a forecast.

Commit 48 adds optional Postcards and Wayfinder storytelling, grounded Good to
Know, Places to See, Seasonal Feel and a reduced-motion-aware visual experience.
Commit 49 adds Build This Trip and Itinerary Studio: party and practical needs,
positive day allocations, activity discovery and edits across Morning/Afternoon/
Evening, and deterministic day-load guidance. Unknown duration/accessibility
remains unknown. Commit 50 adds dated multi-country allocations, transition days,
truthful unresolved journeys and local text/JSON handoff. Partner offers, journey
evidence, snapshot repositories and branding are future contracts only.

The domain and application remain provider independent; adapters normalize
external evidence; FastAPI composes the API and packaged browser shell. See
[architecture](architecture.md) and [product scope](product-scope.md).

## Privacy and security

Provider credentials stay server-side. Browser assets expose no secrets, raw
provider payloads, analytics, tracking or external scripts. There are no accounts,
identity cookies or account identifiers; identity-free limits are process-local.
Safe DOM/text insertion and bounded untrusted text are covered by existing
contracts. CORS remains restrictive; arbitrary redirect targets are not enabled.

Trips exist in active page memory, with no server trip store, localStorage,
sessionStorage or IndexedDB persistence. Exports use explicit local downloads;
practical requirements are excluded by default and included only by deliberate
choice. There is no automatic agency submission. Travel providers receive the
inputs necessary for the requested service; this is not a claim of zero external
processing. Existing request-reference logging remains privacy-conscious.
`/release` exposes only global build identity and bypasses client event logging.
This summary makes no security certification or penetration-test claim.

## Operational limitations and non-goals

The intended topology is one Render Free Docker service in Singapore, one
instance and one Uvicorn worker. Cold starts and restarts are expected;
process-local safeguards reset on restart and are not a guaranteed financial
hard cap. Provider quotas and billing need operator monitoring. Optional provider
failures may degrade imagery, discovery or narration; required evidence failures
must remain explicit. There are no keepalive services or additional replicas.

There is no configured routing provider; inter-destination travel stays unresolved,
with no fake 90-minute duration, generic transport buttons or default road mode.
There are no live schedules, hotel/activity/transport inventory, prices, booking,
payments, accounts, saved trips, server/browser trip persistence or collaboration.
Solara has no visa, immigration or legal authority. Destination Knowledge/RAG,
vector retrieval and a curated knowledge corpus remain MVP2. These are scope
limitations, not promises of functionality in this candidate.

## Acceptance and definitive launch checklist

The owner reviews, commits and pushes Phase A, then deploys that exact SHA to the
existing service and runs [hosted acceptance](hosted-acceptance.md). Feature-branch
candidate testing precedes the eventual merge and final main deployment. A changed
SHA or asset set requires renewed identity and affected-flow acceptance.

| Category | Required evidence | Phase A state |
| --- | --- | --- |
| Source | Commit 51 merged; clean main; CI, CodeQL and Dependency Review green | PENDING |
| Identity | Package 0.1.0, Alpha classifier | Locally validated; hosted PENDING |
| Build | Wheel, sdist, fresh core/web installs, packaged assets and content fingerprints | See local validation report |
| Container | Docker build and runtime checks | UNAVAILABLE locally: daemon absent; PENDING |
| Deployment | Exact expected SHA; final source main; health/release; docs/redoc disabled | PENDING |
| Configuration | Correct server secrets, no documented secret values; one instance/worker; auto-deploy policy confirmed | PENDING operator review |
| Hosted acceptance | All matrix rows, critical cold-climate regression, studio, journeys/exports and mobile/accessibility | PENDING |
| Operations | Google and OpenAI quota/billing review; last known-good rollback SHA | PENDING |
| Documentation | Limitations, deployment procedure and tester guide | Prepared |
| Launch decision | Owner records GO or NO-GO against observed evidence | **PENDING** |

## Rollback

Record the current Render deployment SHA and `/release` identity, then identify
the last actually accepted known-good SHA from deployment/acceptance records.
That SHA is **PENDING identification** here; the historical first deployment is
not automatically the rollback target. Use Render's specific-commit deployment
facility on the existing service with its existing secrets and topology. Check
`/health`, `/release`, the root and functional assets; from a checkout of that
same known-good SHA run the verifier with `--expected-sha`, then repeat critical
traveller flows. The verifier targets this 0.1.0 candidate; an older revision
without `/release` or fingerprints needs its own documented verification and
must not be called verified by this tool. Do not create a second service, copy
secrets into source, force-push main or delete history.

Phase B records the real accepted SHA/date/results, resolves defects and remaining
checklist items, and justifies a GO decision before closing Commit 51 and MVP1.
