# Commit 51 Phase A implementation and local validation

Historical Phase A validation date: 2026-10-06. The owner subsequently committed
`c66e3eba01bbf2f6f35bf780ffadba799184614f` and opened PR #48. That SHA is now the
**pre-correction candidate**, not the final accepted build. The staged/no-commit
statements below describe the original Phase A stopping point.

The current [climate correction](commit51-climate-correction.md) has candidate SHA
**PENDING OWNER COMMIT**. Hosted acceptance remains PENDING, Commit 51 IN PROGRESS
and MVP1 NOT YET CLOSED.

## 1. Commit 50 verification

[PR #47](https://github.com/JervisAnthony/Solara/pull/47), `feat: add partner and
journey capabilities`, is merged. Expected and actual synchronized main/origin
main: `9ea9fda8536a69f158bdb3d9b391c700889a4eb7`. Dated multi-country journeys,
truthful unresolved travel, partner/offer contracts, local JSON/text exports and
versioned TripSnapshot are present. Persistence remains a port; production has
no routing, commercial provider or hidden trip store.

## 2. Branch state and cleanup

Local branches found: `main`, `feature/itinerary-studio` (`77fb584`),
`feature/partner-journey-capabilities` (`0130732`). Remote branches after fetch/
prune: `origin/main`, `origin/revert-45-feature/visual-travel-experience`, plus
`origin/HEAD`. The revert branch and its unique work are preserved.

No local branch was deleted. The Commit 50 branch is patch-equivalent to its
squash merge and its tree matches main, but Git does not consider its tip an
ancestor of main. It was retained rather than force-deleted. The older itinerary
branch was also retained; no unique-work deletion was attempted.

## 3. Clean-main baseline

Main was synchronized with a fast-forward-only pull and verified clean before
the full baseline and before feature-branch creation.

| Gate | Actual clean-main result |
| --- | --- |
| Full pytest | 1,815 passed |
| Standalone Chromium | 44 passed |
| Statements | 4,221 / 4,221; 100% |
| Branches | 1,570 / 1,570; 100% |
| Ruff lint / pip check | Passed |
| Wheel / sdist | 0.1.0.dev0 built successfully |
| Fresh core / web installs | Passed; metadata and packaged web assets checked |
| Security/privacy/static contracts | Passed in full suite |
| Docker | CLI installed; daemon unavailable; no container result claimed |

Local logs are under ignored `.venv/commit51-baseline-*`; no generated artifacts
or environment contents are staged.

## 4. Commit 51 feature branch

`feature/mvp1-release-readiness` was created only after the baseline passed.
Its base, current HEAD and merge-base with main are
`9ea9fda8536a69f158bdb3d9b391c700889a4eb7`. Main's implementation was not edited.

## 5. Release version

Distribution `solara-travel-ai`: `0.1.0.dev0` → `0.1.0`.
Classifier: `Development Status :: 2 - Pre-Alpha` → `3 - Alpha`.
Editable and fresh installed wheel metadata, wheel METADATA and sdist PKG-INFO
all report 0.1.0/Alpha. This is a public alpha, not production certification.

## 6. Static-asset integrity

All eight assets use `/static/<name>?v=<first-16-hex-of-SHA-256>`:
`travel-scopes.js`, `inspiration.js`, `selects.js`, `app.js`, `results.js`,
`itinerary.js`, `feedback.js`, `styles.css`. Hashes derive from current installed
file bytes, not package version, path, time or randomness. Root HTML has explicit
`Cache-Control: no-cache`; imagery URLs/caching and JS semantics are unchanged.

Three focused tests verify every served reference, exact bytes, StaticFiles query
delivery, unchanged/changed hashes and path independence. The named
`test_new_html_never_references_old_functional_javascript_after_content_change`
keeps version fixed and proves a changed JS fixture necessarily changes the HTML
URL. Fresh installed-web checks reproduce source fingerprints for all eight.

## 7. Release identity

Hidden `GET /release` returns exactly `product`, `version`, `source_revision`.
`RENDER_GIT_COMMIT` must be exactly 40 hex characters and is normalized lowercase;
missing, blank, malformed, oversized or non-hex text becomes null. Installed
metadata is authoritative; uninstalled use has a safe explicit fallback.
Ten focused endpoint cases cover validation, safe allowlisted responses, missing
providers, no request identity/cookies/client logs and unchanged health/OpenAPI.
No environment dump, credential, service ID or internal path is exposed.

## 8. Hosted verification tool

`scripts/verify_hosted_release.py` accepts an origin and optional expected SHA.
It checks health, release identity, root functional entrypoints, disabled docs/
redoc, eight versioned asset responses, live hashes and exact local checkout
bytes. Success uses 13 bounded GETs; redirects and untrusted asset URLs are
refused. Mismatches exit nonzero with safe messages. It sends no recommendation,
activity, narration, provider or feedback request. All 37 verifier tests use
offline fixtures; no live service verification was run in Phase A.

## 9. Documentation

README, architecture, development, deployment, product scope and roadmap now
describe the candidate and pending closure. Commit 50's previous validation
record is explicitly historical and acknowledges the subsequent owner commit/
PR merge. The entire deployment guide was reviewed; historical first-deployment
SHA `f325e419af1e7a88963c581c5d81ac9473de44fe` is separated from the currently
unknown live SHA. Blueprint adoption remains pending actual dashboard evidence.

- [Release guide, limitations, privacy/security and launch checklist](mvp1-release.md)
- [Exact-SHA hosted acceptance matrix](hosted-acceptance.md)
- [Traveller-oriented tester guide](tester-guide.md)
- [Deployment and rollback guidance](deployment.md)

## 10. Hosted acceptance status

**PENDING.** No acceptance timestamp, accepted candidate SHA or live pass result
is fabricated. The launch decision remains PENDING. Owner review/commit/push,
exact-SHA deployment, zero-provider integrity smoke and deliberate real traveller
acceptance must precede Phase B closure.

## 11. Full final local validation

| Gate | Actual candidate result |
| --- | --- |
| Full pytest, including browser tests | 1,866 passed; zero failures |
| Standalone Chromium | 44 passed |
| Statements | 4,257 / 4,257; 100% |
| Branches | 1,574 / 1,574; 100% |
| Focused release assets / endpoint / verifier | 3 / 10 / 37 passed |
| Installed package test | Version and Alpha classifier passed |
| Ruff lint | Passed |
| pip check | Editable, fresh core and fresh web environments passed |
| JavaScript syntax | All seven functional JS files passed `node --check` |
| Wheel / sdist | 0.1.0 artifacts built successfully |
| Archive contents | Every runtime module/template/static file equals checkout bytes in both archives |
| Fresh core install | Imports from site-packages, 0.1.0/Alpha metadata passed |
| Fresh web install | Health/release/root, docs policy, imagery and eight source-equivalent fingerprints passed |
| Security/privacy/static contracts | Passed in full suite; new endpoint/tool manually reviewed |
| Critical climate regression | Thailand/Philippines hard-cold exclusion passed; browser recovery test passed |
| Diff checks | Working and staged whitespace checks passed |
| Docker | CLI 28.4 available; desktop-linux engine pipe absent; daemon unavailable |

The existing Starlette/httpx deprecation and pytest-cache permission warnings
did not fail tests. The optional repository-wide formatter probe reports 42
files needing formatting; CI explicitly defers the format gate pending a
dedicated baseline normalization. Ruff lint is the required gate and passes;
all five newly added Python files pass formatting. No broad formatting refactor
or weakened test/coverage threshold is included.

Commands used include:

```powershell
.venv\Scripts\python.exe -m pytest --cov=solara_travel --cov-branch --cov-report=term-missing --cov-report=json:.venv/commit51-final-coverage.json
.venv\Scripts\python.exe -m pytest tests/browser
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m build --outdir .venv/commit51-final-dist
git diff --check
git diff --cached --check
```

Fresh virtual environments: `.venv/commit51-final-core` and
`.venv/commit51-final-web`; each installed the final built wheel, and the latter
installed the web extra plus httpx for local smoke testing. The ignored
`.venv/commit51-package-check.py` checked both archives, imports, metadata and
installed delivery. Final logs: `.venv/commit51-final-tests.log`,
`commit51-final-browser.log`, `commit51-final-build.log`, core/web install logs
and final coverage JSON. PowerShell reported build stderr as a native-command
error despite successful builds; actual success was confirmed by build logs,
archive validation and clean installs.

## 12. Scope confirmation

No new booking, routing provider, inventory, pricing, payment, account,
persistent trip storage, RAG or vector database. Geography, hard constraints,
ranking, activity/journey evidence and feasibility authority are preserved.
Default tests remain offline and credential-free.

## 13. Git status and staged manifest

Final branch: `feature/mvp1-release-readiness`. Intended files: 28 staged;
zero unstaged changes and zero untracked files. Ignored test/build artifacts
remain outside the staged diff.

```text
README.md
docs/architecture.md
docs/commit50-validation.md
docs/commit51-phase-a-validation.md
docs/deployment.md
docs/development.md
docs/hosted-acceptance.md
docs/mvp1-release.md
docs/product-scope.md
docs/roadmap.md
docs/tester-guide.md
pyproject.toml
scripts/verify_hosted_release.py
src/solara_travel/presentation/api/app.py
src/solara_travel/presentation/api/observability.py
src/solara_travel/presentation/api/routes/release.py
src/solara_travel/presentation/web/assets.py
src/solara_travel/presentation/web/routes.py
tests/presentation/api/test_release.py
tests/presentation/web/test_feedback.py
tests/presentation/web/test_form.py
tests/presentation/web/test_intelligent_planner.py
tests/presentation/web/test_itinerary_studio.py
tests/presentation/web/test_release_assets.py
tests/presentation/web/test_results.py
tests/presentation/web/test_shell.py
tests/test_package.py
tests/tools/test_hosted_release.py
```

## 14. Permission compliance and stopping point

NO COMMIT CREATED. NO COMMIT AMENDED. NO PUSH PERFORMED.
NO PR OPENED OR MODIFIED. NO MERGE PERFORMED. NO REBASE PERFORMED.
NO TAG CREATED. NO RELEASE CREATED. MAIN NOT MODIFIED DIRECTLY.
COMMIT 51 PHASE A STAGED ONLY.

The owner inspects the staged diff and commits/pushes through GitHub Desktop.
Phase B records actual hosted evidence, resolves remaining gates and only then
may close Commit 51 and MVP1.
