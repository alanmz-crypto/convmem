# [Arc Codex #286] Kiro review — scoped-write proof in shadow mode

**Reviewer:** Kiro, 2026-10-18. **Design under review:**
`docs/plans/DESIGN-issue-286-scoped-proof-shadow.md` at `7021b87` on
`origin/docs/2026-10-18-issue-286-scoped-proof-shadow`.
**Baseline verified against:** `origin/main` `07117ed` (PR #404 deployed).
**Scope:** review-only. No implementation; new branch from `origin/main`; no PR.

**Verdict: PASS-with-conditions** for implementing the shadow slice (T1–T4).

## Consequence for Ryan

Codex may build an **opt-in SHADOW observer** that runs the proposed source-scoped
write policy alongside today's two full inventory digests, records where they
disagree, and changes **no** commit or recovery decision. This slice removes zero
scans and is expected to be *slower* by the observer overhead. It buys evidence,
not speed. The ~144 s/commit opportunity (the two full `non_source_digest` +
`verify_non_source` passes) stays untouched until a *later* scoped-enforcement
slice clears gates M/R/P — which this design correctly defers and does not
self-approve. Approving this does not approve removing any scan.

## Verification I performed

I checked the load-bearing code claims against baseline `07117ed` directly, not
from chat memory:

- **Commit sequence (§2) — CONFIRMED.** `incremental_jsonl.py:_commit_generation`
  (2270) takes `source_flock` then `index_write_flock` (C1), then runs, in order:
  `non_source_digest` phase → `before_images` → `journal` (writes rollback +
  `APPLYING` transaction) → `apply` → `verify_non_source` → checkpoint. The two
  full scans are `_non_source_collection_digest()` called inside the
  `non_source_digest` and `verify_non_source` phase spans (2323, 1657–1658). The
  phase-span names match Ryan's live timing (`non_source_digest` ~72 s,
  `verify_non_source` ~72 s). The design's claim is exact.
- **`_verify_non_source_collections` reuses a value, not a third scan — CONFIRMED.**
  It compares against the `expected` dict captured earlier; §6's "capture full
  comparison outcome without taking a third scan" is faithful to the code.
- **Rollback authority / APPLYING (§2, §6) — CONFIRMED.** `_require_rollback_authority`
  (2457) re-checks the journal SHA; replay retains the original SHA. The design's
  "foreign commits between attempts must survive" maps to real behavior.
- **Promotion blocker (§2) — ACCEPTED as stated.** The design flags, as a *blocker
  for the later enforcing slice* (not a live exploit), that a holder of a
  `_collection` handle can mutate outside `_native`. It explicitly keeps this out
  of the shadow slice and lists closing it under gate M. That honesty is correct.

The design's self-description of its own validation (read pinned refs + Slice 1
code; traced seams; ran no benchmarks/tests/migration) matches what a design-only
turn should claim.

## Ruling on the five requested areas

### §3 — Shadow-mode noninterference contract: PASS

The contract is sound and the right strength:

- `off`/`shadow` only; `scoped` is explicitly refused at config parse before any
  operation — no env-var shortcut. This matches the strict, fail-closed
  `incremental_jsonl_settings` parser already in `config.py`, so the new enum has
  a precedent to follow.
- Authoritative evidence stays `full_inventory_v1`; the diagnostic
  `scoped_writes_shadow_v1` / policy `scoped_writes_v1` never denies a native call
  (`would_deny` is diagnostic-only). No shadow result touches return status,
  checkpoint/export/processed publication, retry, quarantine, paid work, rollback
  selection or cleanup.
- The error-handling boundary is explicitly correct: observer failures are caught
  only around observer-owned reads/serialization/IO; the native call and guard
  exit are **never** wrapped in a broad swallow. Process termination and real
  storage errors propagate unchanged.
- The design states plainly that "no-change means unchanged decisions and
  authoritative artifacts, **not** zero overhead." Good — this prevents a false
  "shadow is free" reading.

**Condition C-SH1 (binding):** The off/shadow differential tests (§8 "Behavior
parity") must assert byte-identical authoritative artifacts — native argument
order, checkpoint, transaction, **original rollback bytes**, export bytes/order,
processed state, prepared reuse, and paid-call count — including the case where
the observer itself fails mid-attempt. T2's exit criterion already names this;
I am making it a gate, not a nice-to-have.

### §4.3 — Honest coverage boundary: PASS (this is the strongest part)

The design refuses to let the observer grade its own homework:

- It mandates **independent low-level mutation spies** in tests, and requires that
  a raw-handle bypass touching only an owned row **must fail the coverage test
  even though the full digest passes**. This is exactly the right oracle
  separation and directly exercises the `_collection`-handle promotion blocker.
- It requires a static inventory of supported writers / raw clients / aliases /
  dynamic dispatch / nested sessions / lifecycle / recovery routes, regenerated at
  the candidate SHA, with an owner/disposition each; unresolved raw access is
  reported `coverage_unqualified`.
- It is explicit that a compliant observed census is still only diagnostic and
  **does not prove mediation** — mediation is gate M, on the later enforcing
  implementation.

**Condition C-SH2 (binding):** The writer/route inventory (§4.3) must be
regenerated and diffed at the exact promotion SHA, and any new or unclassified
mutation route must fail T1/T3 rather than default to "covered." The design says
this; the implementer must not let the inventory silently drift.

### §6 — Failure and comparison semantics: PASS

The four-quadrant comparison table is correct and does not over-claim:

- `full changed + candidate compliant` is correctly named a **detection-gap**
  disagreement that preserves `non_source_isolation_changed`; on an injected
  untouched-foreign-row edit this is the *expected* limitation, and on an ordinary
  run it *blocks promotion*. The design does not auto-label anything a "false
  positive."
- `Any incomplete / full not reached` is explicitly "not a passing sample" — no
  invented comparison, no inferred equality.
- Guard-finalization failure, partial batch, cancellation, segment restoration and
  quarantine evidence all invalidate clean candidate evidence and route through
  **existing** containment/recovery; no Safe Harbor repair is added here. Correct.
- Restart uses the original transaction protocol + fresh full baseline + original
  journal SHA; old diagnostic files cannot authorize replay or replace a
  before-image. This preserves the recovery invariants I care about most.

**Condition C-SH3 (binding):** §6 says "diagnostic reasons … do not create new
production refusal codes in this slice." The implementer must verify no new
`refusal`/quarantine code path becomes reachable in `shadow` mode — the failure
injection suite (§8) must include a control that asserts the set of reachable
terminal outcomes in `shadow` is a subset of `off` plus purely-diagnostic events.

### §8 — Tests and controls that must fail: PASS

The negative-control discipline is exactly what a shadow slice needs. The
must-fail controls are well chosen:

- Bypass `_native` with an owned-row raw write → independent coverage test must
  fail (catches the promotion blocker).
- Remove one receipt → completeness fails.
- Make the candidate always `allow` → policy tests fail.
- Omit derived physical IDs → valid-case parity fails.
- Mutate a foreign row's document / metadata / vector / membership separately
  (touched source rows kept valid) → full comparison must detect, candidate may
  stay compliant, detection-gap event must be recorded.
- Accounting controls: a third full digest, a removed post digest, reading all
  foreign payloads, unbounded receipt scans, or synchronous/post-return
  compaction must all fail structural/performance tests. OFF emits no observer IO.

**Condition C-SH4 (binding):** The hermetic-only injection of invalid writes
(§3: "invalid writes injected into a disposable SHADOW fixture may reach Chroma
and then fail today's full check") must be fenced so it can never run against a
live Chroma or a real provider. §8 already requires network-denied children with
disposable HOME/XDG/data and production-path/network escape controls that refuse
before access — the implementer must demonstrate these controls actually refuse
(a passing "control that must fail" is itself a required artifact).

### §9 — Acceptance gates before any switch to scoped mode: PASS

The S/Q/M/R/P ladder is the right shape and the dependency direction is correct:

- **S** accepts the shadow implementation only; it "permits a request for
  production shadow observation, **not** scan removal."
- **Q** requires ≥100 complete ordinary one-chunk attempts over ≥24 h, ≥3 sources,
  both first and appended commits, zero unexplained disagreements, with
  scheduled/started/terminal reconciliation. A clean cohort "supports the design;
  it does not prove mediation."
- **M** (prove enforcing mediation) requires native-entry spies showing **zero
  calls** for foreign/ownerless collisions, scope widening, nested sessions,
  threads/subprocesses, raw handles, unrestricted predicates, create/drop/reset;
  requires closing the inventoried bypasses; and explicitly states "C3 attestation
  alone is insufficient" and "tests against an evaluator or mock wrapper alone do
  not clear M." A no-other-writer deployment window is required.
- **R** requires versioned `scoped_writes_v1` receipts durably complete before
  checkpoint, forbids falling back to a newly computed full baseline after an
  unproven scoped mutation, keeps old full-mode journals replaying full with their
  original SHA, and requires scoped recovery to re-check current ownership
  immediately before every restore/delete.
- **P** requires measured zero foreign inventories and matched full/shadow/scoped
  fixtures with Gates A/B labeled independently.

Crucially, the design states **S/Q do not clear M/R/P** and "no count of clean
shadow runs auto-enables scoped mode." That is the single most important property
of this ladder and it is stated correctly.

**The §9 "Human acceptance" clause is the heart of the review and it is correct.**
It requires that any eventual scoped-mode grant explicitly accept **loss of
immediate per-commit detection of changes to untouched foreign content**, and it
states the grant **must not cite `chroma_audit` as compensation**. §2 reinforces
this: the scheduled Chroma audit "is not a compensating control for this loss, at
any cadence," and a future periodic content audit still would not restore
immediate per-commit observation. This is exactly the condition my commit-cost
review attached, carried faithfully. **I confirm:** the scoped-write proof is
acceptable *only* with its explicit detection loss acknowledged, and the Chroma
audit is **not** a compensating control.

**Condition C-SH5 (binding, carried from the commit-cost review):** No future
Execute PR, VERIFY section, or grant may describe `chroma_audit` (or any periodic
segment/vector-loss audit) as mitigating the lost per-commit foreign-content
detection. If a reviewer sees that framing, it is an automatic FAIL for the
scoped-mode switch regardless of timing results.

### §10 — Cost model and Gates A/B: PASS (with the design's own honesty preserved)

The cost model is honest in exactly the ways it needs to be:

- SHADOW saves **0** on both target phases and is slower by observer overhead.
  The engineering budget (paired median added C1/commit ≤5 s, p95 ≤10 s each) is a
  per-slice budget, explicitly **not** Gate B.
- The ~144 s gross opportunity is scoped-mode-only. The design does the subtraction
  but labels the residual an "illustrative arithmetic residual, not a predicted
  median," because the inputs are unpaired phase summaries and whole-run samples.
- It states outright: "this slice cannot plausibly establish Gate B. Gate A is also
  unproven." Gates A/B are carried **unchanged** (Gate A ≤60 s end-to-end; Gate B
  max continuous **and** total C1 hold <5 s), with "never infer either gate from
  the other, the live median, a plan PASS, merge or a structural scan reduction."

This is the correct posture: the shadow slice is not allowed to borrow credit from
a future speedup, and the live-median saving from Slice 1 (which my deploy review
accepted) is explicitly **not** a Gate A/B pass for this slice.

**Condition C-SH6 (non-blocking, measurement hygiene):** §10's measurement
protocol (≥30 paired commits per condition, pinned host/deps/fixture, the
111,348-unit synthetic fixture, foreign-row sweep 10k/~111k/2×) applies to the
*later scoped* performance work, not to T4's shadow-overhead budget. The
implementer should not conflate the two; T4 only owes the overhead budget plus
structural criteria, and must label Gates A/B `NOT_MEASURED` for the shadow slice
rather than attempting them.

## Are T1–T4 bounded and execution-ready?

Yes. The task decomposition is serial, each task has a concrete exit criterion,
and the stop-conditions are real (T2: "stop for review if a required hook would
change a guard/recovery decision or require a new cross-arc contract"). The
proposed new files (`incremental_mutation_proof.py`,
`tests/test_issue_286_scoped_proof_shadow.py`) are additive and do not touch the
authoritative path when `off`. T1 (policy + coverage spec, no enforcing mode),
T2 (wiring + bounded receipts, scan budget stays exactly two per collection), T3
(adversarial + recovery), T4 (overhead + handoff evidence) are each reviewable in
isolation. The design is correct that T4 ends the slice and that production shadow
observation, scoped enforcement, and digest removal each need separate authority.

## Conditions summary (all must hold for the Execute PR to pass Kiro)

- **C-SH1** — off/shadow differential tests assert byte-identical authoritative
  artifacts (incl. rollback bytes and paid-call count), including under observer
  failure.
- **C-SH2** — writer/route inventory regenerated and diffed at the promotion SHA;
  any unclassified mutation route fails T1/T3, never defaults to "covered."
- **C-SH3** — a failure-injection control asserts the reachable terminal-outcome
  set in `shadow` is a subset of `off` plus purely-diagnostic events (no new
  reachable refusal/quarantine code).
- **C-SH4** — production-path/network/live-Chroma escape controls are demonstrated
  to refuse before access; the "controls that must fail" are themselves delivered
  as evidence.
- **C-SH5** — no artifact may frame `chroma_audit` or any periodic audit as
  compensating for lost per-commit foreign-content detection; doing so is an
  automatic FAIL for the later scoped switch.
- **C-SH6** (non-blocking) — T4 owes only the shadow overhead budget + structural
  criteria; Gates A/B are labeled `NOT_MEASURED` for this slice.

None of these change the design's architecture; they bind the implementer to the
discipline the design already describes. Hence PASS-with-conditions rather than a
request for a redesign.

## What this review does NOT grant

- Not a grant to remove any full digest.
- Not a grant to run shadow observation in production (that is a post-S request).
- Not a grant to implement scoped enforcement (gate M).
- Not a Gate A or Gate B pass.
- Does not clear the pending wedged transaction `46313d43…` (`recovery_unproven`);
  the design correctly leaves it alone and only exercises its *shape* synthetically.

---

I finished: Kiro review of the scoped-proof shadow design (`7021b87`).
Next step:  Ryan decides whether to grant Cursor the T1–T4 Execute slice under
            conditions C-SH1..C-SH6; Cursor implements after the grant.
Next lane:  Ryan (grant), then Cursor (Execute).
See my work: `docs/inter-model/KIRO-2026-10-18-issue-286-scoped-proof-shadow-review.md`

<!-- src: ../plans/DESIGN-issue-286-scoped-proof-shadow.md — 7021b87 on origin/docs/2026-10-18-issue-286-scoped-proof-shadow, the design under review -->
<!-- src: ../../incremental_jsonl.py, ../../scripts/bootstrap-incremental-jsonl.py, ../../incremental_checkpoint_migration.py, ../../config.py — baseline 07117ed seams verified during review -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex routing and future implementation evidence -->
