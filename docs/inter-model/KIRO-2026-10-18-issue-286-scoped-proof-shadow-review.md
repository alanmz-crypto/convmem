# [Arc Codex #286] Kiro design review — qualify the scoped-write proof in shadow mode

**Verdict: PASS-with-conditions for implementing the shadow slice (T1–T4).**
The design is bounded, execution-ready, and honest about what it does and does
not prove. Conditions below are mostly "do not let this slice drift into
enforcement or scan removal," not defects in the plan.

**Arc: Codex (#286).**

**Who / what / when / why / how:** Kiro (design-review lane), 2026-10-18.
Reviewing Codex's `docs/plans/DESIGN-issue-286-scoped-proof-shadow.md` on
`origin/docs/2026-10-18-issue-286-scoped-proof-shadow` at `7021b87`, pinned to
baseline `07117ed` (= current `origin/main`, the deployed Slice 1 / PR #404).
This design is the follow-through on my earlier C2 conditions
(`docs/inter-model/KIRO-2026-10-17-issue-286-commit-cost-reduction-review.md`,
`fc56151`): I required that the scoped-write proof's loss of immediate
untouched-row detection be accepted explicitly, that mediation be proven rather
than asserted, and that the Chroma audit not be cited as a compensating control.
This design takes the honest path — it does not switch to scoped enforcement; it
runs the proposed cheaper proof as a non-authoritative observer alongside both
full digests. Ryan asked me to rule on §3 (shadow noninterference), §4.3
(coverage boundary), §6 (failure/comparison semantics), §8 (controls that must
fail), §9 (acceptance gates), and §10 (cost model + Gates A/B), then give a
verdict for implementing the shadow slice.

**This is a review of direction, not an Execute grant. No code was written, no
indexing run, no provider called, no live config or `.worktrees/runtime-main`
touched. Delivered as one document on a new branch from `origin/main`, pushed
with an explicit refspec, no PR.**

---

## 0. Overall verdict and why

**PASS-with-conditions.** Cursor may implement T1–T4 after Ryan's Execute grant.

The core design decision is right: this slice removes **zero** scans, changes
**zero** commit/recovery decisions, and keeps `full_inventory_v1` authoritative
while a diagnostic `scoped_writes_shadow_v1` observer records what the proposed
policy *would* do. That is exactly the shape my prior review asked for — prove
the cheaper proof before trusting it, and never conflate a clean shadow cohort
with proven mediation. The design states its own ceiling plainly: SHADOW saves
0 s, Gates A and B remain unproven, and the ~144 s gross opportunity belongs to
a later, separately-authorized scoped mode gated behind S/Q/M/R/P.

I verified every load-bearing seam the design integrates against (§"What I
verified" below). They are accurate at `07117ed`, including the two claims that
most matter for soundness: (1) the `_native` observation point sits inside the
guard after client reload and before the API call, with completion tied to guard
exit; and (2) `_IndexWriteGuardedChromaStore` denies raw `client` but returns a
C1-gated `_collection` handle a caller can mutate outside `_native` — a real
coverage gap for shadow and a hard promotion blocker for later enforcing mode,
which the design labels correctly rather than hiding.

The conditions are guardrails against scope creep, plus two I want tightened:
the honest-coverage inventory must be a build-time artifact with an explicit
owner per route (not a prose list), and the §8 differential negative controls
must be wired as real failing-by-construction tests, not assertions the
implementer could soften.

---

## 1. §3 — Shadow-mode noninterference contract: PASS

The noninterference contract is the thing this slice lives or dies on, and it is
specified correctly.

- **Config surface is fail-closed and matches the house pattern.** A strictly
  parsed `index.incremental_jsonl.mutation_proof_observer` with `off` (default)
  and `shadow`, refusing invalid values **including `scoped`** before an
  operation begins, fits the existing `IncrementalJsonlConfigError` /
  `incremental_jsonl_settings` parser in `config.py` (fail-closed table parsing
  is already the established idiom). No env-var shortcut, no production scoped
  switch. Correct: `scoped` must not be silently acceptable config in this slice.
- **OFF is byte-identical to Slice 1.** Same mutation calls, journal/checkpoint
  schemas, scan counts, error handling; no new files or ownership lookups. This
  is testable (§8 behavior parity) and is the right default.
- **SHADOW cannot change authority.** The design is explicit that no shadow
  result changes return status, checkpoint/export/processed publication, retry,
  quarantine, paid work, rollback selection or cleanup. A diagnostic
  `would_deny` never denies a native call. This is the correct inversion of the
  usual policy-gate: the observer watches the real route; the real route never
  waits on the observer.
- **Error containment is scoped narrowly and correctly.** Observer failures are
  caught **only** around observer-owned reads/serialization/diagnostic I/O —
  never around the native call or guard exit. This is the single most important
  implementation constraint, and the design calls out the anti-pattern (a broad
  "ignore observer error" handler wrapping the native call) by name. T2's exit
  criterion must enforce it.
- **Honest about overhead.** "No change" means unchanged decisions and
  authoritative artifacts, **not** zero overhead; extra reads/fsyncs cost
  latency. Good — this is why §10's overhead budget exists and why SHADOW is
  expected to be *slower*.

One condition:

- **SC-1 (noninterference proven by differential, not inspection).** T2's
  off-vs-shadow parity must assert equality of native argument order, results,
  refusals, checkpoint/transaction/rollback bytes, export bytes/order, processed
  state, prepared reuse and paid-call count — **including when the observer is
  forced to fail** (ENOSPC/short-write/fsync/read error injected observer-side).
  A parity test that only runs the happy path does not prove noninterference.
  The design already lists this under §8 failure injection; SC-1 makes it a gate
  on T2, not a nice-to-have.

---

## 2. §4.3 — Honest coverage boundary: PASS-with-conditions

This section is the design's strongest contribution and the reason I trust the
rest of it. It refuses to let the observer grade its own homework.

- The claim "a context carried through `_native` proves only what it observed"
  is correct and is backed by the real seam: the C1-gated `_collection` handle
  returned by `_IndexWriteGuardedChromaStore.__getattr__` (confirmed at
  `chroma_write_store.py` ~1077–1083) lets a caller issue `.add/.upsert/.delete`
  directly, bypassing `_native` entirely. An observer wired only into `_native`
  cannot see that write. The design states this as a **promotion blocker**, not
  an exploit, and does not pretend the shadow observer closes it. That is the
  honest call.
- Requiring independent low-level mutation spies (not the observer's own
  counter) as the coverage oracle is exactly right. "A raw-handle bypass must
  make the coverage test fail even if the full digest passes because the bypass
  touched only an owned row" is the correct, adversarial framing — it is the
  test that distinguishes a real mediation proof from a census that merely
  agrees with itself.
- `coverage_unqualified` as a first-class diagnostic result (a compliant census
  is still only diagnostic) preserves the boundary into the evidence schema.

Conditions:

- **CC-1 (inventory is a build artifact, not prose).** "Maintain a static
  inventory of supported production writers, raw clients/collections, aliases,
  dynamic dispatch, nested sessions, collection lifecycle and recovery routes,
  with an owner/disposition for each … regenerate it at the candidate SHA." This
  must ship as a checked-in, regenerable artifact with one explicit
  owner/disposition per route and a test that fails when a new writer route
  appears without a disposition. A paragraph in a design doc is not an
  inventory; the next model will not maintain prose. T1's exit ("no unknown
  route is silently marked covered") is only real if the inventory is
  machine-checked.
- **CC-2 (bypass census is enumerated, not sampled).** The known bypasses — the
  C1-gated `_collection` handle, nested/same-thread sessions, thread/fork copies
  of the attempt token, stale clients — must each have a named coverage test
  that currently records `coverage_unqualified` or `would_deny`/`incomplete`.
  "We spied and saw nothing" is not coverage; "we enumerated every raw path and
  each is explicitly accounted for" is.

---

## 3. §6 — Comparison and failure semantics: PASS

The five-way comparison matrix is sound and, importantly, resists the two
tempting errors (auto-classifying disagreements, and inferring equality from a
missing scan).

- **Full equal + candidate compliant → qualified only if coverage is
  established.** Correct, and the "this alone never proves mediation" caveat is
  the right ceiling.
- **Full equal + candidate would-deny → policy disagreement, no auto
  false-positive.** Correct. The design acknowledges full mode may have
  permitted a self-restoring foreign no-op, or the candidate may be too strict,
  and refuses to label it. Investigate before promotion.
- **Full changed + candidate compliant → detection-gap, preserve
  `non_source_isolation_changed`.** This is the crux loss from my C2 review, and
  it is handled correctly: on a deliberately injected untouched-foreign edit it
  is the *expected* limitation; on an ordinary run it **blocks promotion** and
  forces a fresh qualification cohort. The design does not let the gap pass
  silently.
- **Full changed + candidate would-deny → do not merge meanings.** Only the full
  digest establishes observed changed state. Correct refusal to conflate.
- **Any incomplete / full not reached → not a passing sample.** Correct. No
  invented comparison, no declared equality.

The implementation detail that makes this cheap is also verified: §6 observes
the value `_verify_non_source_collections` already produces (confirmed call site
at `incremental_jsonl.py:2373–2374`, after `apply`) and preserves its exception
rather than taking a third scan. The outer `finally` for diagnostic
finalization, and the "a kill may leave only an incomplete file" acknowledgement,
are consistent with the APPLYING/journal protocol as it actually exists
(`_commit_generation` at 2270; APPLYING transaction written at 2340; replay via
`_restore_replay_before_images` at 2475 retaining the original journal SHA
through `_require_rollback_authority` at 2457).

- **FC-1 (restart leaves authority untouched).** The condition I want explicit:
  on restart, old diagnostic files must never authorize replay, replace a
  before-image, or trigger a paid transform; recovery uses the original journal
  SHA and a fresh full baseline, and foreign commits between attempts survive.
  The design says this; FC-1 pins it as a T3 recovery-qualification gate with a
  failing-by-construction test (feed a surviving shadow receipt into recovery
  and assert it is ignored).

---

## 4. §8 — Required tests and controls that must fail: PASS-with-conditions

The negative-control discipline here is good and is the right way to prove a
diagnostic observer is actually load-bearing. The must-fail controls are the
point: if making the candidate "always allow" does not break the policy tests,
the policy tests prove nothing.

Accepted as specified: behavior parity (OFF vs SHADOW on frozen fixtures);
policy/coverage adversarial cases (foreign collision, missing owner, ownership
change, wrong root/UUID/source/transaction/attempt/SHA, broad delete, duplicate
IDs, wrong derivation, unknown op/create/drop/reset, nested session, thread/fork,
stale client, raw handle); differential negative controls (raw-write bypass must
fail coverage; removed receipt must fail completeness; always-allow must fail
policy; omitted physical IDs must fail parity); the separately-injected
foreign-row document/metadata/vector/membership mutations where full detects and
candidate may stay compliant; failure injection at every phase boundary; and the
accounting controls (a third full digest, removed post digest, foreign payload
reads, unbounded receipt scans, synchronous/post-return compaction must all fail
structural/performance tests; OFF emits no observer I/O).

Conditions:

- **TC-1 (controls fail by construction, verified red-then-green).** Each
  must-fail control must be demonstrated actually failing against a deliberately
  broken implementation before it is wired to pass — i.e. the implementer shows
  the red. Otherwise a weak assertion silently "passes" and the control is
  theater. This is the single biggest risk in a diagnostic-observer test suite.
- **TC-2 (hermetic injection stays hermetic).** §8 and §3 both say invalid
  writes injected into a disposable SHADOW fixture may reach Chroma and then
  fail today's full check, and must **never** be injected in production. T3 must
  run in a network-denied child with disposable HOME/XDG/config/data/cache/
  TMPDIR, fake deterministic providers, real scratch Chroma, and production-path
  / network-escape controls refused before access. Keep the parent arc's
  isolation harness; do not widen adapter admission (admitted Codex + supported
  Kiro fixtures only).
- **TC-3 (the deferred mutants stay deferred).** The design correctly notes the
  parent's re-inline-envelope mutant belongs to the deferred representation
  slice and introduces no reference format here. Hold that line — no envelope
  side store, no provenance/hash redefinition sneaks in under "diagnostic
  commitments."

---

## 5. §9 — Acceptance gates before any switch to scoped mode: PASS

The S/Q/M/R/P ladder is the correct generalization of my prior C2-a…C2-e
conditions, and the sequencing is right: accepting the shadow implementation (S)
does **not** clear mediation (M), recovery (R) or substitution (P), and no count
of clean shadow runs auto-enables scoped mode. That non-transitivity is the
whole safety argument and the design states it twice.

- **S — accept the shadow implementation.** Scoped to T1–T4 at one pinned
  revision, two full inventories per collection preserved, diagnostics never
  authoritative, failure samples not excluded, §10 overhead budget passes.
  Correct that S "permits a request for production shadow observation, not scan
  removal." This is the gate this review feeds.
- **Q — qualify observations.** ≥100 complete ordinary one-chunk shadow attempts
  over ≥24 h, ≥3 sources, both first and appended commits, zero unexplained
  disagreements/would-deny/incomplete/guard-invalidated/unaccounted attempts,
  reconciled scheduled/started/terminal counts. The requirement that any
  unexplained event stops qualification and forces a *fresh pinned cohort* (not a
  patched-up continuation) is the right discipline. Diagnostic loss counts as an
  evidence failure — correct; this is what makes the §5 fsync/cap/no-auto-delete
  rules matter.
- **M — prove enforcing mediation.** This is where my C2-b lands, and it is
  specified at the right strength: native-entry spies showing **zero** calls for
  foreign/ownerless collisions, scope widening, hidden/nested sessions,
  threads/subprocesses, raw handles, unrestricted predicates and
  create/drop/reset; all writers obey C1 or are refused; a no-other-writer
  deployment window where older processes cannot enforce admission; and
  explicitly "tests against an evaluator or a mock wrapper alone do not clear M."
  Crucially, M requires **closing the raw-handle bypass** I verified in §2 —
  which is correctly deferred out of this shadow slice.
- **R — qualify authoritative receipts and recovery.** This is my C2-c (distinct
  typed outcomes) and C2-e (recovery routing) made concrete, and it is the
  sharpest part of the ladder. The non-negotiables are all present: never fall
  back to a newly computed full baseline after an unproven scoped mutation (it
  cannot reconstruct the missing before-state); old full-mode journals always
  replay in full mode with their original SHA and config cannot convert them;
  scoped recovery rechecks current ownership immediately before every
  restore/delete so a now-foreign/ownerless target refuses rather than being
  overwritten by a stale source preimage; reconcile every ID in an uncertain
  batch. These are the correct lessons from the recovery-authority arc.
- **P — measure and accept the substitution.** Zero full foreign inventories and
  no foreign payload reads for isolation in the eventual scoped fresh path;
  bounded census work across the foreign-count sweep; backend lookup / segment
  I/O reported separately so a hidden global scan fails. "A failed A or B remains
  explicitly failed and cannot be called arc completion" — correct, and consistent
  with how I ruled on the parent.
- **Human acceptance** restates C2-a verbatim in spirit: Kiro's exact-revision
  PASS **and** Ryan's explicit scoped grant must accept loss of immediate
  per-commit detection of untouched-foreign content, and **"the grant must not
  cite `chroma_audit` as compensation."** This is exactly my prior finding (the
  audit covers vector-loss/segment-validity, not foreign-row content; it is not a
  compensating control at any cadence). The design carries it correctly.

No new conditions on §9 — the ladder is sufficient. One note for the record:
S/Q are what the eventual implementation+evidence must clear with me; M/R/P are
separate later reviews (M and R are safety/isolation + recovery changes and get
the charter's targeted independent audit). This document clears none of M/R/P and
does not pre-authorize them.

---

## 6. §10 — Cost model and Gates A/B: PASS (and correctly unmet)

The cost model is honest to the point of arguing against its own slice's
headline, which is what I want from a planning document.

- **Phase effects verified.** `non_source_digest` (~72 s) and `verify_non_source`
  (~72 s) are the two full non-source inventory passes — confirmed as the real
  `phase_span` labels at `incremental_jsonl.py:2321` and `2373`, emitted on the
  `incremental_commit_phase_timing` event (1330). SHADOW saves 0 on both; only a
  later scoped fresh mode removes them (~72 s gross each, before new proof/
  touched-row-verification cost). `before_images` (~25 s) and `export_reconcile`
  (~19 s) get no saving in either mode — correct; Slice 1 already removed the
  redundant inventory inside `before_images`, and flat-JSONL export stays linear.
- **The arithmetic is labeled as arithmetic.** "~71 s plus proof cost, an
  illustrative arithmetic residual, not a predicted median" and "unpaired phase
  summaries and whole-run samples cannot prove it" — this is the correct posture
  given Ryan's live numbers came without sample count, host/cache distribution,
  or paired raw events. The design treats them as planning inputs, not
  measurements, exactly as it should.
- **Gates A/B are correctly declared unproven.** "The surviving measured
  before-image/export phases alone total roughly 44 s; this slice cannot
  plausibly establish Gate B. Gate A is also unproven." Agreed, and consistent
  with my parent review where I ruled the gates correct and unmet. The ≥30
  commits/condition harness, pinned host/deps/fixture seed, the live-shape
  synthetic fixture (111,348 units / 5,106 summaries / 203,441 export rows /
  ~5.19 GiB nonsparse), the foreign-row 10k/~111k/2× sweep, and "sparse data /
  warm cache cannot conceal a scan" are all the right controls.
- **Overhead budget is an engineering gate, not Gate B.** Paired median added
  C1/commit ≤5 s and p95 ≤10 s each, with max + RSS/bytes reported. The design
  is explicit that failing it keeps shadow rollout gated and "cannot justify
  dropping full digests or skipping receipt durability." Correct separation.

One condition:

- **MC-1 (no double-counting, attributed overhead).** §10 says observer
  ownership/readback/hash/fsync cost is attributed to its actual parent phase
  **plus** a separately labeled nested observer span, and "do not add nested
  subspans to the leaf-phase total twice." T4 must demonstrate the timing event's
  field contract is unchanged (§5) and that nested observer time is reported
  without inflating the phase total. This is easy to get subtly wrong and would
  corrupt the very measurement that gates Q and later P.

---

## 7. Verdict summary

| Section | Question | Verdict |
|---|---|---|
| §3 | Shadow-mode noninterference contract | **PASS** (condition SC-1: parity proven under injected observer failure) |
| §4.3 | Honest coverage boundary | **PASS-with-conditions** (CC-1 inventory is a machine-checked artifact; CC-2 bypasses enumerated, not sampled) |
| §6 | Failure and comparison semantics | **PASS** (condition FC-1: restart/replay never authorized by shadow receipts) |
| §8 | Tests and controls that must fail | **PASS-with-conditions** (TC-1 controls fail red-then-green; TC-2 hermetic isolation; TC-3 no envelope creep) |
| §9 | Acceptance gates before scoped mode | **PASS** — S/Q/M/R/P sufficient; audit still NOT a compensating control at any cadence; this doc clears none of M/R/P |
| §10 | Cost model and Gates A/B | **PASS** — model honest; SHADOW saves 0; Gates A/B correctly unproven (condition MC-1: no double-counted overhead) |
| — | **Implement the shadow slice (T1–T4)** | **PASS-with-conditions** |

**Conditions, consolidated (all are implementation gates for Cursor, verified by
me at the pinned revision before S is cleared):**

- **SC-1** — off/shadow differential parity holds even when the observer is
  forced to fail; narrow error containment never wraps the native call or guard
  exit.
- **CC-1** — the writer/raw-route inventory ships as a regenerable, checked-in
  artifact with one owner/disposition per route and a test that fails on an
  undisposed new route.
- **CC-2** — every known bypass (C1-gated `_collection` handle, nested sessions,
  thread/fork token copies, stale clients) has a named test recording
  `coverage_unqualified`/`would_deny`/`incomplete`.
- **FC-1** — on restart, shadow receipts never authorize replay, replace a
  before-image, or trigger a paid transform; recovery uses the original journal
  SHA and a fresh full baseline; foreign intervening commits survive.
- **TC-1** — each must-fail control is demonstrated red against a deliberately
  broken build before being wired green.
- **TC-2** — T3 runs network-denied, disposable env, fake providers, real scratch
  Chroma; production-path/network controls refused; no adapter-admission widening.
- **TC-3** — no envelope side store, reference format, or provenance/hash
  redefinition enters under "diagnostic commitments."
- **MC-1** — observer overhead attributed to its parent phase plus a separate
  nested span, never double-counted; the existing timing event field contract is
  unchanged.

None of these conditions change the design's direction; they harden the
implementation against the two ways a diagnostic observer rots (self-grading
coverage, and must-fail controls that never actually fail).

---

## 8. What I verified vs. did not

**Verified (read-only, against baseline `07117ed` via `git show`):**

- `_commit_generation` (`incremental_jsonl.py:2270`) takes `source_flock` then
  `index_write_flock` (C1), captures the full baseline in
  `phase_span("non_source_digest")` (2321), reuses it in `_snapshot_before_images`
  (2326, def at 1601), writes the rollback journal + APPLYING transaction (2330–
  2340), applies (2367), then runs `_verify_non_source_collections` (2373–2374,
  def at 1657) before checkpoint (2408). Order matches §2 exactly.
- `_restore_replay_before_images` (2475) takes a fresh baseline; replay retains
  the original journal SHA through `_require_rollback_authority` (2457). Matches §2.
- `chroma_store.py:_native` (179): obtains the collection inside
  `guard.native_write(... reload_client=self._reload_client)` after reload, and
  the native call's completion is bound to guard-context exit — "native API
  return alone does not establish successful guard finalization" is accurate. The
  design's observation point (inside the guard, after reload, before the API
  call) is a real seam.
- `chroma_write_store.py:_IndexWriteGuardedChromaStore` (1029): `__getattr__`
  raises on `client` (1067–1069) but returns a `_collection` wrapper gated only
  by `require_index_write_lock_held` (1077–1083). A holder of that handle can
  mutate outside `_native`. The "promotion blocker / C1 possession is not source
  ownership" claim is accurate.
- `_apply_prepared` (1440) routes through `provenance_binding.provenance_identity`
  and `ingest_dedupe.evaluate_ingest_batch`, so the final physical ID can differ
  from the prepared ID — supporting §2/§4.2's "observe the final ID, not just the
  original prepared ID."
- `config.py` has fail-closed `IncrementalJsonlConfigError` /
  `incremental_jsonl_settings` parsing (strict table parse already the idiom), so
  a strictly-parsed `mutation_proof_observer` with `off|shadow` refusing invalid
  (incl. `scoped`) fits.
- All seven cited regression test files exist under `tests/` at `07117ed`.
- `incremental_commit_phase_timing` event (1330) emits the phase labels the
  design cites; `non_source_digest` and `verify_non_source` are the two targeted
  full scans.

**Did not verify (out of review scope / not yet built):**

- No implementation exists to run; I ran no tests, no benchmark, no indexing, no
  provider, no recovery. Gate A/B numbers are unmeasured by design.
- The ~72 s/72 s/25 s/19 s and 215 s-median live timings are Ryan's supplied
  inputs; I did not re-measure them and the design does not claim to.
- The known wedged APPLYING transaction `46313d437ae4446282a752270770c614`
  (doctor WARN, `recovery_unproven`) is untouched; the design exercises its shape
  synthetically only and does not repair it. Not my concern for this verdict.
- M/R/P are later reviews; this document clears none of them.

---

## 9. Review-scope conformance

Review-only. One document, created on a new branch
`docs/2026-10-18-issue-286-scoped-proof-shadow-review` cut from `origin/main`
(`07117ed`), pushed with an explicit refspec, no PR. No source, tests, config,
scripts, STATUS or LATEST were modified. `.worktrees/runtime-main` and live
config were not touched. No implementation, indexing, or provider call occurred.

---

## 10. Forward announcement

I finished: Kiro design review of the scoped-proof shadow slice (#286).
Next step:  Ryan decides a Cursor Execute grant for T1–T4; Cursor implements the
            opt-in shadow observer with conditions SC-1/CC-1/CC-2/FC-1/TC-1/TC-2/
            TC-3/MC-1, then returns code + evidence for my exact-revision S review.
Next lane:  Ryan (grant) → Cursor (implement) → Kiro (S acceptance).
See my work: docs/inter-model/KIRO-2026-10-18-issue-286-scoped-proof-shadow-review.md

---

**TL;DR:** PASS-with-conditions for implementing the shadow slice (T1–T4). The
design does the honest thing — runs the proposed cheaper source-scoped proof as a
non-authoritative observer beside both full digests, removes zero scans, changes
zero commit/recovery decisions, and never cites the Chroma audit as compensation.
§3 noninterference, §6 comparison semantics, §9 S/Q/M/R/P gates and §10 cost model
all PASS; §4.3 coverage boundary and §8 must-fail controls PASS with conditions
that harden the two failure modes of a diagnostic observer (self-grading coverage;
controls that never actually fail). Verified every integration seam at `07117ed`,
including the real `_native` observation point and the C1-gated `_collection`
promotion blocker. SHADOW saves 0 s; the ~144 s opportunity and Gates A/B belong
to a later, separately-gated scoped mode this review does not authorize.

<!-- src: ../plans/DESIGN-issue-286-scoped-proof-shadow.md — 7021b87 on origin/docs/2026-10-18-issue-286-scoped-proof-shadow, baseline 07117ed -->
<!-- src: ./KIRO-2026-10-17-issue-286-commit-cost-reduction-review.md — fc56151, the prior C2 conditions this design follows through -->
<!-- src: ../../incremental_jsonl.py, ../../chroma_store.py, ../../chroma_write_store.py, ../../config.py — baseline 07117ed seams verified for this review -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md, ../plans/VERIFY-codex-jsonl-production-integration.md — Arc Codex routing and the future implementation evidence section -->
