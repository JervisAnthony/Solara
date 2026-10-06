# PR #48 platform-independent release verifier correction

Local validation record: 2026-10-07 (Asia/Calcutta). **Correction SHA PENDING
OWNER COMMIT; hosted acceptance PENDING; Commit 51 IN PROGRESS; MVP1 OPEN.**

## Baseline and defect

Branch: `feature/mvp1-release-readiness`. Clean initial worktree/index, no untracked
files. HEAD and fetched origin branch: `61391e7cc0229acdbcc4da28b1ab3bc950b79bb6`.
Main, origin/main and merge-base: `9ea9fda8536a69f158bdb3d9b391c700889a4eb7`.
[PR #48](https://github.com/JervisAnthony/Solara/pull/48) remains open.

The owner reported that `/release` identifies that climate-corrected deployment
and the browser shows **Cold — required**. Full hosted integrity and the manual
acceptance matrix are still pending. The subsequent transient network failure is
separate from the confirmed byte-comparison defect; no retry mechanism was added.

Locally, `core.autocrlf=true`; Git records LF but `app.js` and `feedback.js` have
CRLF worktree bytes, and `styles.css` has mixed worktree endings. `app.js` has
29,138 canonical Git bytes versus 29,980 worktree bytes (842 CRLF sequences).
Their fingerprints differ: `e24fe31ab735073d` versus `34bc84e479f42296`.
No asset was edited or normalized to reproduce or resolve this defect.

The old verifier correctly checked the live hash against the served URL, then
incorrectly treated platform-converted worktree bytes as the release authority.
The Linux-hosted canonical bytes consequently failed that second check on Windows.

The complete baseline passed before edits: 1,895 tests, 50 separate browser tests,
4,260/4,260 statements and 1,576/1,576 branches (100% each). Ruff, pip check,
seven JavaScript syntax checks, wheel/sdist, fresh core/web installs, installed
metadata and all packaged runtime files/assets passed. Existing security/privacy/
static contracts passed in the full suite. No baseline behavior was repaired.

## Exact authority and safe execution

The verifier preserves byte-exact live SHA-256 URL validation, then compares
against canonical blob bytes from the validated deployed revision. No newline
normalization is used. `--expected-sha` must match `/release` before asset requests
or Git reads; its normalized value selects the objects. Without that option,
a valid `source_revision` selects the objects. HEAD need not match the revision.

`git cat-file blob` receives an argument array with `shell=False`, a validated
40-hex revision, a fixed repository-relative prefix and one of eight allowlisted
asset names. The repository root is fixed from the script location, execution
is limited to ten seconds, and stderr is discarded. Git/object/timeout failures
return a concise `VerificationError` with no Git output, local paths or chained
diagnostics exposed. No branch switch or repository write is performed.

Null `source_revision` without an expected SHA retains exact worktree comparison
only as a labeled local fallback. Its success output expressly says there is no
authoritative Git revision. Exact success says **8 assets match release commit**;
byte disagreement says **live asset differs from deployed Git revision**.

Health, product/version, expected identity, disabled docs/redoc, root entrypoint
identities, exactly eight safe same-origin functional URLs, status checks and live
fingerprints remain enforced. Only operational and asset GETs are issued: no
recommendations, provider calls, activity requests or feedback submissions.

## Regression tests and documentation

The real Git regression reads all eight blobs from HEAD, constructs live responses
with those exact LF bytes, and verifies them while the supplied worktree directory
contains different CRLF bytes. It creates no commits and changes no browser assets.
Additional tests cover genuine byte differences with a valid live fingerprint,
fingerprint failures, early expected-SHA rejection, revision selection without
`--expected-sha`, null-revision fallback, safe Git failures, argument allowlisting,
fixed invocation/timeout and direct object access without a HEAD lookup.

Current deployment, release, acceptance, architecture and development instructions
now describe Git-object authority and fetching missing objects without switching
HEAD. README and historical reports distinguish the committed climate fix from
this pending correction; historical validation totals remain intact. The tester
guide needs no verifier-specific change. No hosted matrix row is marked complete.

## Final validation

| Gate | Actual final result |
| --- | --- |
| Full pytest | 1,907 passed; zero failures (215.89 seconds) |
| Separate Chromium browser suite | 50 passed; zero failures (203.24 seconds) |
| Statement coverage | 4,260 / 4,260; 100%; zero missing |
| Branch coverage | 1,576 / 1,576; 100%; zero missing/partial |
| Ruff | Passed repository-wide; coverage thresholds unchanged |
| Dependencies | Editable, fresh core and fresh web `pip check` passed |
| JavaScript | All seven functional JavaScript files passed `node --check` |
| Wheel and sdist | Both 0.1.0 artifacts built successfully |
| Fresh installs | Separate new core and web environments installed and passed smoke checks |
| Installed metadata | 0.1.0 and Alpha classifier; imports came from site-packages |
| Packaged runtime/assets | Every module/template/static file byte-exact in wheel/sdist; all eight installed asset fingerprints and delivery passed |
| Release endpoint / assets / verifier | 10 / 3 / 49 cases passed in the full suite; 62 focused cases also passed |
| Older revision | Real offline verification of all eight blobs at `c66e3eba01bbf2f6f35bf780ffadba799184614f` succeeded with HEAD still `61391e7cc0229acdbcc4da28b1ab3bc950b79bb6` |
| Missing object | Real unavailable object failed with the safe concise Git-asset message |
| Security/privacy/static | Full-suite contracts passed; exact change scope, fixed invocation, credential-pattern scan, documentation links and manual diff review passed |
| Diff whitespace | `git diff --check` and staged whitespace check passed |
| Docker | CLI 28.4.0 installed; desktop-linux daemon unavailable (engine pipe absent); container build/runtime validation not performed |

The existing httpx deprecation and pytest-cache permission warnings are
non-failing. An initial sandboxed focused run could not access pytest temporary
directories; its authorized rerun passed. PowerShell reported native build stderr
as exit 1, but both build logs explicitly confirmed successful artifacts, which
the fresh installs and complete archive checks independently validated.

Validation commands used `.venv/Scripts/python.exe` with pytest coverage and
`tests/browser`, Ruff, pip check and `build`; outputs and package/object smoke
helpers are ignored under `.venv/c51-git-*`. No live service or provider acceptance
was performed in this correction pass.

## Staged manifest

Eleven intended files, with zero unstaged modifications or untracked files:

```text
README.md
docs/architecture.md
docs/commit51-climate-correction.md
docs/commit51-phase-a-validation.md
docs/commit51-verifier-correction.md
docs/deployment.md
docs/development.md
docs/hosted-acceptance.md
docs/mvp1-release.md
scripts/verify_hosted_release.py
tests/tools/test_hosted_release.py
```

## Scope and stopping point

Only the operator verifier, its tests and relevant documentation change. All
runtime modules, templates, browser functional assets and configuration remain
unchanged. Climate, recommendations, itinerary/journey/export behavior, provider
contracts and privacy boundaries remain unchanged. No routing, booking,
persistence, accounts or RAG/vector capabilities are added.

The owner must review, commit/push, deploy the new exact SHA and rerun integrity
and the pending hosted matrix before acceptance or launch closure.

**NO COMMIT CREATED. NO PUSH PERFORMED. NO MERGE PERFORMED. MAIN NOT MODIFIED
DIRECTLY. VERIFIER CORRECTION STAGED ONLY. HOSTED ACCEPTANCE STILL PENDING.
COMMIT 51 STILL IN PROGRESS. MVP1 STILL OPEN.**
