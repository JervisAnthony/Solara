# Commit 51 hosted acceptance record

**Phase A: PENDING. Commit 51 IN PROGRESS; MVP1 NOT YET CLOSED.**

| Release record | Value |
| --- | --- |
| Public service | https://solara-travel-mvp1.onrender.com |
| Expected corrected candidate SHA | PENDING OWNER COMMIT |
| Previous owner-observed deployment | `61391e7cc0229acdbcc4da28b1ab3bc950b79bb6`; corrected cold UI visible |
| New `/release` SHA and version | PENDING owner commit/deployment; expected version 0.1.0 |
| Acceptance date/operator/evidence | PENDING |
| Launch decision | PENDING |

After owner review/commit/push, deploy the exact candidate SHA to the existing
service. Use the corrected verifier with that commit object available locally
(fetch if necessary; HEAD may differ) before running the read-only integrity smoke:

```powershell
python scripts/verify_hosted_release.py https://solara-travel-mvp1.onrender.com --expected-sha <40-character-pushed-SHA>
```

This performs only GETs for health, release, root, docs/redoc and eight functional
assets. It makes no recommendation/provider requests and submits no feedback.
It fails nonzero for identity, entrypoint, asset hash or canonical Git-blob mismatch,
and safely fails if Git or the requested revision is unavailable. Each live hash
must match its URL fingerprint and each live asset must match the exact validated
release commit, independent of Windows checkout newline conversion. Null-revision
worktree fallback cannot satisfy this acceptance procedure.
The optional SHA argument is required by this acceptance procedure. A successful
integrity smoke alone does not establish traveller acceptance.

The manual checks below can consume provider quota. The operator records actual
inputs, observations, request references where applicable, date and deployed SHA
for each row. Record defects truthfully, fix them on the same feature branch and
deploy/retest the new exact SHA. Empty/failure states should be observed safely
where possible; do not manufacture passes or exhaust provider quotas to test limits.

| Area | Required observation | Hosted status / evidence |
| --- | --- | --- |
| Deployment | Render expected SHA equals `/release`; package 0.1.0 | PENDING |
| Operational surfaces | Health/root 200; docs/redoc 404 | PENDING |
| Asset integrity | All eight live hashes match URLs and bytes match the exact release Git blobs; no mixed old/new frontend | PENDING |
| Discovery: city | Explicit canonical city evaluation | PENDING |
| Discovery: country | Country expands to validated localities | PENDING |
| Discovery: region | Region containment and locality identity | PENDING |
| Discovery: mixed | Exact cities and broad scopes together | PENDING |
| Discovery: worldwide | Blank destination produces bounded discovery | PENDING |
| Discovery: typo | Autocomplete recovery and confirmed selection | PENDING |
| Discovery: maximum | 15-scope boundary, duplicates and over-limit recovery | PENDING |
| Climate A | Thailand + Philippines + Singapore, Cold — required: zero matches when historical temperatures fail the threshold; no tropical fallback | PENDING |
| Climate B | Portugal + Thailand + Philippines + Singapore, Cold — required: only individually qualifying cold candidates survive | PENDING |
| Climate C | Cold — required + warm/island/beach narrative: hard cold eligibility wins | PENDING |
| Climate D | No snowfall, snow cover or ski-condition claim inferred from temperature evidence | PENDING |
| Climate recovery | Change climate, Change destinations, Broaden search | PENDING |
| Recommendation | Postcards and optional-media fallback | PENDING |
| Recommendation | Wayfinder and narration failure fallback | PENDING |
| Recommendation | Seasonal Fit and deterministic ordering | PENDING |
| Recommendation | Places to See, Seasonal Feel, grounded/omitted Good to Know | PENDING |
| Disclosure | Historical-not-forecast note visible | PENDING |
| Build entrypoints | Build this trip and Build a multi-stop trip visible | PENDING |
| Build flow | Single-stop and multi-stop flows | PENDING |
| Studio context | Traveller composition, pace, reduced walking, frequent rests | PENDING |
| Studio allocation | Destination order, positive day allocations, Morning/Afternoon/Evening | PENDING |
| Studio edits | Activity discovery, add, remove, replace, move and reorder | PENDING |
| Activity API | Real POST `/api/v1/itinerary-activities`; canonical locality identity | PENDING |
| Activity states | Loading, success, observable empty state and failure degradation preserve plan | PENDING |
| Feasibility | Normal day; deliberately overloaded day; Full/Very Full guidance where appropriate | PENDING |
| Travel honesty | Unresolved stays unresolved; no fake 90-minute journey, generic transport buttons or default road mode | PENDING |
| Dated journeys | Dated destination route, multi-country route, transition day and unresolved wording | PENDING |
| Journey edits | Route reordering and activity city/country identity preserved | PENDING |
| Handoff formats | JSON and text downloads retain unresolved journeys | PENDING |
| Handoff privacy | Requirements excluded by default, included only by explicit choice | PENDING |
| Handoff boundaries | No booking claim, external submission or browser persistence | PENDING |
| Devices | Desktop/mobile and no horizontal overflow | PENDING |
| Accessibility | Keyboard, touch targets and reduced motion | PENDING |
| Feedback | Explicit tester submission and repeated-click behavior | PENDING |
| Public alpha | Rate-limit/cooldown UX where safe; request reference behavior | PENDING |
| Resilience | Real cold-start experience and provider degradation | PENDING |

The owner's pre-correction hosted testing identified the climate wording defect.
This local correction pass establishes no corrected-build hosted acceptance.
Local fake-provider tests are recorded in [the correction report](commit51-climate-correction.md);
the original Phase A results remain [historical](commit51-phase-a-validation.md).
Phase B fills this record with observed evidence, closes the [launch checklist](mvp1-release.md)
and records GO/NO-GO only when justified. Final main deployment must also match
its intended SHA and assets before launch.

The old Phase A SHA `c66e3eba01bbf2f6f35bf780ffadba799184614f` is pre-correction
history and cannot establish final acceptance. After owner commit/push, rerun CI,
CodeQL and Dependency Review, deploy the new exact head and verify `/release` plus
all asset bytes against that exact Git revision before the corrected manual climate cases.
Cold eligibility uses historical mean ≤12°C AND minimum ≤5°C; it never verifies
snowfall. All results above remain PENDING. Commit 51 and MVP1 remain open.

The owner confirmed the prior deployment identity and corrected cold label, then
encountered the Windows worktree comparison defect. These observations do not
complete the matrix. [The platform-independent verifier correction](commit51-verifier-correction.md)
requires owner commit/push, exact-SHA deployment and fresh integrity/acceptance
evidence; the new candidate SHA remains PENDING OWNER COMMIT.
