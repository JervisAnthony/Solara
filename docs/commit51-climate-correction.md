# PR #48 climate correction and validation record

Local validation completed on 2026-10-07 (Asia/Calcutta).
**Corrected candidate SHA: PENDING OWNER COMMIT. Hosted acceptance PENDING.
Commit 51 IN PROGRESS. MVP1 NOT YET CLOSED.**

## 1. PR and baseline verification

[PR #48](https://github.com/JervisAnthony/Solara/pull/48), `chore: prepare MVP1
release candidate`, is open on `feature/mvp1-release-readiness`, targeting main.
Previous reviewed head, actual correction baseline, local HEAD and remote head:
`c66e3eba01bbf2f6f35bf780ffadba799184614f`. Main/origin main and merge-base:
`9ea9fda8536a69f158bdb3d9b391c700889a4eb7`. Fetch/prune confirmed no later work
to reconcile. The working tree/index were clean, with no untracked user work.
The PR had one commit, 28 changed files and no commits behind main. Its reported
CI, CodeQL and Dependency Review checks succeeded for the pre-correction head;
those results do not establish checks for this uncommitted correction.

## 2. Complete pre-correction baseline

| Gate | Actual result before editing |
| --- | --- |
| Full pytest | 1,866 passed |
| Standalone Chromium | 44 passed |
| Statements | 4,257 / 4,257; 100% |
| Branches | 1,574 / 1,574; 100% |
| Ruff lint / dependency checks | Passed |
| JavaScript syntax | All seven functional JS files passed |
| Wheel / sdist | 0.1.0 built successfully |
| Fresh core / web installs | Passed; site-packages imports and 0.1.0/Alpha metadata |
| Archive / installed assets | Runtime files matched checkout; eight fingerprints/delivery passed |
| Release endpoint / verifier / privacy/security | Passed in full suite and package smoke |

All baseline gates completed before production/test/documentation edits. Logs
and fresh environments are ignored `.venv/c51-cold-baseline-*` artifacts.

## 3. Root cause

The prior UI exposed **Cold or snowy — required**, the domain/API condition was
`cold_or_snowy`, and the browser sent it for `cold_snowy`. The service explicitly
had no snowfall provider and used only historical temperature evidence. Its
combined label therefore could not substantiate snow and overstated capability.

## 4. Domain and API correction

The sole condition is now `ClimateCondition.COLD = "cold"`. Request/response
literals and generic enum mappings use `cold`; hard severity remains `hard`.
Legacy combined and unsupported snow conditions are rejected, not aliased.
Unknown fields remain forbidden and ordinary preferences retain existing
validation/context behavior.

The unchanged rule requires historical seasonal mean ≤12°C **AND** minimum ≤5°C.
It evaluates each canonical candidate for the requested dates before ranking.
There is no country blacklist or AI climate authority. Candidate proposal,
free text, interests and pace cannot override hard eligibility. Eligibility is
independent of the general temperature-comfort Seasonal Fit score.

## 5. Traveller UI and successful zero matches

The control shows **Cold — required**, sends preference `cold` and the explicit
hard `cold` constraint, explains historical temperature evidence and visibly
states that Solara does not currently verify snowfall. Other climate options
remain ordinary search preferences.

Only an empty response echoing `cold` + `hard` shows **No places match your
required climate**, with evidence-supported cold conditions and recovery wording.
Other empty responses use the generic **No destinations returned this time**.
The browser derives this from response authority, not the current select value.
Recovery preserves traveller inputs and never silently removes the requirement.
Two existing recovery targets pointed at nonexistent `destination-search`; they
now focus `destination-input`. Climate recovery focuses the climate control.

## 6. Snow truthfulness and Wayfinder

**NO SNOWFALL IS INFERRED FROM TEMPERATURE.** Below-freezing temperatures do not
establish snowfall, snow cover, ski conditions or reliable snow availability.
Trusted Wayfinder instructions state this boundary. Its existing plain-text
validation rejects snow-language enrichment and falls back to the unchanged
deterministic result. Canonical destination names remain identity, so a place
named Snow Mountain is not itself misclassified as a weather claim.
No snowfall, forecast, precipitation, ski or other provider was introduced.

## 7. Regression coverage

- All-warm Bangkok/Thailand, Manila/Philippines and Singapore fixtures yield zero
  hard-cold matches, even with warm-island/beach/diving free text.
- Real mixed-scope orchestration covers Portugal + Thailand + Philippines +
  Singapore: only the qualifying Portuguese fixture survives; if its evidence
  is also warm, the result is empty. Proposal receives contradictory context
  but deterministic eligibility owns the result.
- Six threshold cases cover exact boundaries, independent mean/minimum failures,
  freezing evidence, warmth, and a qualifying Singapore fixture to prove that
  geography names never determine eligibility.
- Domain rejects legacy/snow values. HTTP accepts and echoes cold/hard, returns
  only qualifying evidence, and rejects legacy/unknown conditions and extra fields.
- Desktop/mobile browser cases check cold label, visible disclosure, keyboard
  selection, ARIA, request contract, truthful zero state, recovery focus, retained
  inputs and overflow. Warm/mild/cool send no hard constraint. None/soft response
  constraints restore generic copy even while the UI still selects cold.
- Six Wayfinder fixtures reject snow claims across all prose/highlight fields;
  prompt and grounding tests preserve evidence boundaries and rank authority.
- Full Commit 49/50 itinerary, activity, feasibility, dated journey, partner,
  snapshot, export, privacy and no-persistence regressions remain green.

## 8. Release integrity

Package remains 0.1.0/Alpha; `/release`, revision validation, health, HTML
revalidation and the operator verifier are unchanged. All eight functional
assets remain fingerprinted. Changed `app.js` and `results.js` bytes automatically
produce new URLs; the other six fingerprints stay identical. Fresh installed
web checks confirm the cold-only schema/copy and exact source-equivalent bytes.
The verifier still uses only read-only operational/asset GETs and consumes no
Google/OpenAI provider quota or feedback mutation. It was not run live here.

| Asset | Pre-correction hash | Corrected hash |
| --- | --- | --- |
| app.js | d2a43aee41d661a8 | 34bc84e479f42296 |
| results.js | 922672d0ba858519 | 9938e242e6c66eac |

## 9. Documentation and complete wording audit

Updated README, architecture, development, product scope, roadmap, tester guide,
release guide and hosted matrix. The old Phase A validation record now identifies
the owner-created `c66e3eba01bbf2f6f35bf780ffadba799184614f` as **pre-correction
history**. It must not be used for final corrected acceptance. The older Commit
50 record labels its former combined-climate tests historical.

Repository-wide cold/snow search classification:

| Remaining location | Classification |
| --- | --- |
| Application comments/instructions/Wayfinder validator | Explicit unsupported-snow boundary |
| Browser help | Explicit snowfall limitation |
| Domain/API rejection and browser absence assertions | Negative regression fixtures |
| Narration snow phrases | Rejected enrichment fixtures |
| Snow Mountain fixture | Canonical name identity, no weather claim |
| HTTP `rain & snow` fixture | Unrelated query-encoding regression |
| Development/correction descriptions of the old contract | Migration/history, explicitly rejected |
| Release/scope/tester/architecture/roadmap copy | Unsupported-snow disclosure and correction history |

No active source enum, HTTP literal, browser value or UI label retains the
combined contract. The hosted matrix explicitly includes corrected cases A–D;
every hosted result remains **PENDING**. Launch/closure remain pending.

## 10. Full final local validation

| Gate | Actual corrected result |
| --- | --- |
| Full pytest | 1,895 passed; zero failures |
| Standalone Chromium | 50 passed; zero failures |
| Statements | 4,260 / 4,260; 100% |
| Branches | 1,576 / 1,576; 100% |
| Ruff lint | Passed |
| pip check | Editable, fresh core and fresh web environments passed |
| JavaScript syntax | All seven functional JS files passed |
| Wheel / sdist | 0.1.0 built successfully |
| Fresh core / web installs | Passed; actual site-packages imports and Alpha/version metadata |
| Package contents | Every runtime module/template/static file matched checkout bytes in both archives |
| Release assets / endpoint / verifier tests | All 3 / 10 / 37 cases passed in the full suite |
| Installed release integrity | Root/health/release/docs policy, all eight fingerprints and changed-asset checks passed |
| Security/privacy/static, unsafe DOM, browser storage | Existing full-suite contracts passed; correction manually reviewed and credential-scanned |
| Working/staged diff checks | Passed |
| Docker | CLI 28.4.0 installed; daemon unavailable (desktop-linux engine pipe absent); no local container validation claimed |

No thresholds were lowered and no failing test was skipped. Existing Starlette/
httpx deprecation and pytest-cache permission warnings are non-failing. Ruff lint
is the repository gate; its formatter gate remains deferred by existing CI.
Successful archive creation was confirmed from build logs and actual archive/
install checks despite PowerShell treating build stderr as a native-command error.

```powershell
.venv\Scripts\python.exe -m pytest --cov=solara_travel --cov-branch --cov-report=term-missing --cov-report=json:.venv/c51-cold-final-coverage.json
.venv\Scripts\python.exe -m pytest tests/browser
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m build --outdir .venv/c51-cold-final-dist
git diff --check
git diff --cached --check
```

Final logs/environments use ignored `.venv/c51-cold-final-*` paths. Fresh installs
use the built wheel; web adds its web extra and httpx for local smoke. The ignored
package-check helper verifies archives, installed metadata, root/release and
fingerprints. No generated artifacts, logs or secret values are staged.

## 11. Final Git state

Same branch: `feature/mvp1-release-readiness`. **29 intended correction files
staged; zero unstaged changes; zero untracked files.** No new feature branch or
branch deletion. PR #48 remains open; HEAD remains the pre-correction SHA.
The manifest comprises ten updated documentation files plus this report, eight
runtime files and ten test files. Scope excludes booking/routing providers,
inventory/pricing/payments, accounts/persistence, RAG/vector storage and commercial
integrations. The existing release verifier and package version were not changed.

```text
README.md
docs/architecture.md
docs/commit50-validation.md
docs/commit51-climate-correction.md
docs/commit51-phase-a-validation.md
docs/development.md
docs/hosted-acceptance.md
docs/mvp1-release.md
docs/product-scope.md
docs/roadmap.md
docs/tester-guide.md
src/solara_travel/application/narration.py
src/solara_travel/application/recommendation_service.py
src/solara_travel/application/wayfinder.py
src/solara_travel/domain/constraints.py
src/solara_travel/presentation/api/recommendation_schemas.py
src/solara_travel/presentation/web/static/app.js
src/solara_travel/presentation/web/static/results.js
src/solara_travel/presentation/web/templates/index.html
tests/application/test_geographic_discovery.py
tests/application/test_narration.py
tests/application/test_recommendation_service.py
tests/application/test_wayfinder.py
tests/browser/test_public_alpha.py
tests/domain/test_constraints.py
tests/domain/test_recommendation_request.py
tests/presentation/api/test_recommendation_mapping.py
tests/presentation/api/test_recommendations.py
tests/presentation/web/test_intelligent_planner.py
```

## 12. Permissions and required stop

NO COMMIT CREATED. NO COMMIT AMENDED. NO PUSH PERFORMED. NO PR MODIFIED.
NO MERGE PERFORMED. NO REBASE PERFORMED. NO TAG CREATED. NO RELEASE CREATED.
MAIN NOT MODIFIED DIRECTLY. CORRECTION STAGED ONLY.

The owner reviews the staged diff, creates a second commit and pushes using
GitHub Desktop. The new exact PR head must pass CI/CodeQL/Dependency Review, be
deployed to the existing Render service, match `/release`, pass the unchanged
integrity verifier and then the corrected climate plus remaining hosted matrix.
Only then may Phase B justify launch and close Commit 51/MVP1.
