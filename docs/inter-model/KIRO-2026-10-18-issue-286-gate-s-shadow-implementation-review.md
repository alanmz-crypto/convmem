# [Arc Codex #286] Kiro Gate-S review — scoped-proof SHADOW implementation

**Reviewer:** Kiro (design-review / sign-off lane), 2026-10-18.
**Revision under review:** `dbf45c5` (`dbf45c523ca4b3470e0119c83f12974ef0c34995`)
on `fix/2026-10-18-2026-10-18-issue-286-scoped-proof-shadow`.
**Baseline:** `origin/main` `07117ed` (PR #404 deployed).
**Binding conditions:** C-SH1..C-SH6 (the `kiro/2026-10-18-issue-286-shadow-proof-review`
copy of `KIRO-2026-10-18-issue-286-scoped-proof-shadow-review.md`) and the
equivalent SC-1 / CC-1 / CC-2 / FC-1 / TC-1..TC-3 / MC-1 conditions (the
`docs/2026-10-18-issue-286-scoped-proof-shadow-review` copy).
**Scope:** review-only. New branch cut from `origin/main`; explicit refspec; no PR.
`.worktrees/runtime-main` and the live config were not touched.

**Arc: Codex (#286).**

---

## Verdict: PASS-with-conditions (merge + deploy, shadow only)

The implementation is sound and safe to merge and run in **shadow** mode. I
independently confirmed the three properties Ryan asked me to check:

1. **Each must-fail control actually fails when its protection is removed** —
   verified by live mutation (red-then-green shown against the real code, not
   just asserted in the suite).
2. **The observer changes no commit or recovery decision** — verified by direct
   runtime test: a `would_deny` never blocks the native write, observer errors
   never propagate into `_native`, a native exception is re-raised unchanged
   through the observer after-hook, and the authoritative full digest keeps its
   exception and refusal codes.
3. **The chroma_store.py hooks cannot affect native writes** — the hooks sit
   strictly around the native call; the call's result and exception are never
   gated by the observer.

The conditions below are **test-strength** gaps (the guarantees hold by
construction and I verified them directly; the suite under-asserts two of them).
None change behavior or weaken the shadow slice's safety invariant. They are
carry-forward items the eventual production-shadow (Q) and scoped (M/R/P)
reviews must not inherit as "already proven."

---

## Consequence for Ryan

You may merge `dbf45c5` and deploy it in **shadow** mode. Doing so:

- removes **zero** scans (SHADOW is slower by observer overhead — it buys
  evidence, not speed);
- changes **zero** commit/recovery decisions (`full_inventory_v1` stays
  authoritative; `would_deny` is diagnostic only);
- does **not** approve production-shadow qualification (Q), scoped enforcement
  (M), authoritative receipts/recovery (R), or any Gate A/B speed claim.

This Gate-S PASS clears **S only**. The ~144 s/commit opportunity stays locked
behind a later, separately-gated scoped mode.

---

## What I ran (independent verification at `dbf45c5`)

I checked out `dbf45c5` in a throwaway detached worktree (`/tmp/convmem-gateS-dbf45c5`,
removed after review), ran the suite, and performed deliberate mutation
experiments. No live config, no `.worktrees/runtime-main`, no provider calls.

### Full #286 suite — PASS

`tests/test_issue_286_scoped_proof_shadow.py`: **18 passed** at the exact
revision (config rejection, C-SH1/SC-1 parity under observer failure, C-SH2/CC-1
inventory, C-SH3/CC-2 enumerated bypasses + raw-handle unqualified, CC-2 thread
mismatch, C-SH4/FC-1 restart, C-SH5/TC-1 red-then-green, TC-1 completeness,
TC-2 hermetic network-denied child, TC-3 no-envelope, C-SH6/MC-1 timing span,
advisory classification, comparison matrix).

### Blast-radius modules — 208 passed, 16 pre-existing env failures (not the slice)

Ran config, incremental state/isolation/config/recovery-parity/canary-baseline,
`test_incremental_transform_compatibility`, `test_complete_data_restore`,
`test_codex_incremental_jsonl_route`, `test_chroma_readonly`,
`test_chroma_restore_drill`, `test_issue_286_commit_digest_reuse`,
`test_chroma_write_guard`: **208 passed, 16 failed**.

**The 16 failures are all in `tests/test_chroma_write_guard.py` and are a
pre-existing environmental harness bug, not a regression:**

- Root cause: `tests/_chroma_write_guard_worker.py:52` references
  `validate_chroma_argv_path`, which is only imported when
  `SAFE_HARBOR_T3_BOOTSTRAPPED=1` (line 23). Run outside the Safe Harbor
  launcher, the name is unbound → `NameError`.
- The slice touches **neither** `tests/_chroma_write_guard_worker.py` nor
  `tests/test_chroma_write_guard.py` (empty diff vs `origin/main`).
- The identical unbound reference exists at `origin/main` `07117ed`.

Conclusion: these failures reproduce on baseline and belong to the Safe Harbor
arc's launcher-isolation protocol, not to `dbf45c5`. Claude's "725 pass" at
`dbf45c5` is consistent with running under the Safe Harbor bootstrap launcher
(or deselecting those modules); I could not reproduce that exact total without
the bootstrap env, but every shadow-slice and blast-radius test I could run
without the bootstrap passed.

### Must-fail controls — confirmed red-then-green against the real code

I stripped each protection and re-ran its control; each went **red**, proving
the control is load-bearing rather than theater:

| Control | Mutation applied | Result |
|---|---|---|
| TC-1 / C-SH5 policy (`foreign_target`) | replaced `would_deny("foreign_target")` returns with `allow` | `test_c_sh5_tc1_must_fail_controls_red_then_green` **FAILED** (`assert 'allow' == 'would_deny'`) |
| TC-1 receipt completeness | `receipts_complete()` → `return True` | `test_tc1_receipt_completeness_red_then_green` **FAILED** |
| CC-2 raw-handle coverage | removed the `len(_spy_events) > len(self.calls)` unqualified flag | `test_c_sh3_cc2_raw_collection_handle_bypass_unqualified` **FAILED** (`coverage_unqualified` stayed `False`) |

The CC-2 result is the important one: it confirms the coverage oracle is
**independent** of the observer's own counter — a raw write through the C1-gated
`_collection` handle bypasses `_native`, so `_spy_events` exceeds `self.calls`
and the attempt is correctly marked `coverage_unqualified` even though the full
digest passed. That is exactly the promotion-blocker seam, exercised adversarially.

### Observer non-interference — proven by direct runtime test

Driving the observer hooks directly (not just via the suite):

- A foreign write classified `would_deny` **still executed natively** and
  returned its real result — `would_deny` never denies.
- With `set_test_observer_io_error(RuntimeError(...))` forcing the observer to
  raise, `on_native_before` did **not** propagate — the hook's internal
  `try/except` contains it and only sets `coverage_unqualified`.
- Simulating `_native`'s guarded branch, a native exception raised during the
  call was **re-raised unchanged** through the `on_native_after(succeeded=False)`
  after-hook (observer cannot mask a real storage error).

### Integration seam (incremental_jsonl.py 2365–2411 at this rev)

- The shadow attempt wraps `apply` + `verify_non_source`, but the native call is
  **not** wrapped in observer error handling — the observer runs through the
  separate `on_native_before/after` hooks inside `_native`.
- `full_compare` is derived from the **real** `_verify_non_source_collections`
  result; its `IncrementalJsonlError` (incl. `non_source_isolation_changed`) is
  re-raised and stays authoritative.
- `shadow_session.finalize(...)` is diagnostic only, wrapped in
  `try/except OSError: pass`, and its return value is discarded.
- `scoped_proof_observer` is attributed as its own phase key (MC-1), not folded
  into a leaf phase total.

### chroma_store.py `_native` (179–230) — hook isolation

OFF is a no-op (`on_native_before/after` early-return when
`mode != "shadow"`). In both guarded and unguarded branches the native call's
result/exception path is independent of the observer; on native failure the
after-hook records `succeeded=False` and the original exception is re-raised.
The observer cannot alter, delay, or suppress a native write.

### Config fail-closed (config.py)

`mutation_proof_observer` accepts only `off|shadow`; `scoped` is refused at parse
with `IncrementalJsonlConfigError` (`test_config_rejects_scoped_observer`). No
env-var shortcut.

### Recovery advisory (complete_data_restore.py 1861)

`classify_scoped_shadow_diagnostic` marks any `scoped-shadow/` receipt
`OUTCOME_ADVISORY`. Combined with the FC-1 restart test (forged terminal receipt;
checkpoint byte-identical before/after replay), shadow receipts cannot authorize
replay or replace a before-image. FC-1 holds.

---

## Condition-by-condition ruling

| Binding | Property | Ruling |
|---|---|---|
| **C-SH1 / SC-1** | off/shadow authoritative parity incl. under observer failure | **PASS-with-condition** — parity proven for `outcome/chunks/units/exact_suppressed/commit_state` under forced observer `OSError`; see GS-1 |
| **C-SH2 / CC-1** | writer/route inventory regenerable + machine-checked | **PASS-with-condition** — byte-stable regeneration + all 4 bypasses enumerated; see GS-2 |
| **C-SH2 / CC-2** | known bypasses enumerated, not sampled; raw-handle unqualified | **PASS** — enumerated + adversarial coverage test confirmed red when protection removed |
| **C-SH3** | shadow terminal outcomes ⊆ off + diagnostic; no new refusal/quarantine | **PASS-with-condition** — holds by construction (5 comparison strings are diagnostic-only; full-path refusal codes unchanged); see GS-3 |
| **C-SH4 / TC-2** | hermetic network-denied child; production/network escape refused | **PASS** — `test_tc2` asserts `network==IsolationViolation`, `watcher==IsolationViolation`, no credentials; committed in child |
| **C-SH4 / FC-1** | restart ignores shadow receipts; recovery uses original journal SHA | **PASS** — forged terminal receipt leaves checkpoint byte-identical; receipts classified advisory |
| **C-SH5 / TC-1** | must-fail controls fail by construction, red-then-green | **PASS** — three controls independently reproduced red under mutation |
| **TC-3** | no envelope side store / reference format / hash redefinition | **PASS** — schema pinned (`scoped_writes_shadow_v1` / `scoped_writes_v1`); forbidden-token guard |
| **C-SH6 / MC-1** | observer overhead a separate span, not double-counted; timing contract intact | **PASS** — `scoped_proof_observer` phase key + `observer_seconds` event field; existing timing event unchanged |

### Conditions (test-strength, carry-forward — none block merge/deploy of shadow)

- **GS-1 (tighten C-SH1 before Q).** `test_c_sh1_sc1_*` asserts logical-result
  parity and `commit_state`, but **not** byte-identical rollback/transaction/
  checkpoint bytes, export bytes/order, or paid-call count — the `_commit_artifacts`
  helper is defined but never called. The guarantee holds by construction (the
  observer is physically separate from artifact writing, verified above), but the
  binding's literal "byte-identical authoritative artifacts incl. original
  rollback bytes and paid-call count" is not asserted. The production-shadow (Q)
  evidence must wire `_commit_artifacts` into a byte-level off-vs-shadow diff
  (same fixture) and add a paid-call-count equality assertion.

- **GS-2 (CC-1 inventory is not code-scanned).** The inventory is machine-checked
  against its **source JSON** (`SHADOW-WRITER-COVERAGE-INVENTORY.json`), not
  against a live scan of mutation call sites. A new production writer added in
  code but absent from the source JSON would not auto-fail T1/T3. The 4 known
  bypasses are enumerated and tested; this gap is bounded to *future* writers.
  Before M, the inventory generator must fail on an undisposed mutation route
  discovered by scanning code, not only by re-serializing a hand-maintained JSON.

- **GS-3 (C-SH3 has no explicit subset control).** No single failure-injection
  test asserts "reachable terminal outcomes in `shadow` ⊆ `off` + purely-diagnostic
  events." I verified the property by construction (comparison outputs are
  diagnostic strings written only to receipts + the stderr event; the coordinator
  outcome/refusal path is the unchanged full path). Add a control that enumerates
  reachable coordinator terminal outcomes in `shadow` and asserts the subset,
  including under failure injection, before Q.

- **GS-4 (non-blocking, native-exception sentinel).** The suite has no dedicated
  test asserting that a native write exception is **not** masked by
  `on_native_after`. I proved it directly at runtime; a one-line regression
  sentinel (inject a native raise, assert the original exception type
  propagates) would lock the behavior against future refactors.

None of GS-1..GS-4 change behavior or admit a path where the observer alters a
commit, recovery decision, or native write. They are evidence-strength items for
the next gates, consistent with the design's own ladder (S does not clear Q/M/R/P).

---

## C-SH5 carried intact (Chroma audit is not a compensating control)

The implementation introduces no artifact or framing that cites `chroma_audit`
(or any periodic segment/vector-loss audit) as compensating for the lost
per-commit foreign-content detection. This Gate-S PASS does not relax C-SH5: any
future scoped-mode grant, VERIFY section, or PR that frames the audit as
compensation is an automatic FAIL for the scoped switch, regardless of timing.

## What this review does NOT grant

- Not a grant to remove any full digest (SHADOW saves 0 s).
- Not a Q (production-shadow qualification), M (enforcing mediation), R
  (authoritative receipts/recovery), or P (substitution) pass.
- Not a Gate A or Gate B pass — both remain `NOT_MEASURED` for this slice (C-SH6).
- Does not touch or clear the wedged APPLYING transaction
  `46313d437ae4446282a752270770c614` (`recovery_unproven`); the slice exercises
  only its synthetic shape.

## Review-scope conformance

Review-only. One document on a new branch
`docs/2026-10-18-2026-10-18-issue-286-gate-s-shadow-review` cut from `origin/main`
(`07117ed`), pushed with an explicit refspec, no PR. No source/tests/config/
scripts/STATUS/LATEST modified. `.worktrees/runtime-main` and live config
untouched. The review worktree at `dbf45c5` was detached, read-only to tracked
files, and removed after use.

---

I finished: Kiro Gate-S implementation review of the scoped-proof SHADOW slice at `dbf45c5`.
Next step:  Ryan gives the PR command for `fix/2026-10-18-2026-10-18-issue-286-scoped-proof-shadow`; merge + deploy shadow mode only. GS-1..GS-3 are carried into the production-shadow (Q) evidence, not merge blockers.
Next lane:  Ryan (PR + merge), then Cursor/Codex for the Q qualification cohort under GS conditions.
See my work: docs/inter-model/KIRO-2026-10-18-issue-286-gate-s-shadow-implementation-review.md

---

**TL;DR:** **PASS-with-conditions** — `dbf45c5` is safe to merge and deploy in
shadow mode. I independently confirmed all three required properties: every
must-fail control goes red when its protection is removed (verified by live
mutation, not just the suite); the observer changes no commit or recovery
decision (`would_deny` never denies, observer errors never reach `_native`,
native exceptions re-raise unchanged); and the `chroma_store.py` hooks cannot
affect native writes. 18/18 shadow tests pass and 208 blast-radius tests pass;
the 16 `test_chroma_write_guard.py` failures are a pre-existing Safe Harbor
harness bug present identically on `origin/main`, not a regression. Four
test-strength conditions (GS-1 byte-level artifact parity + paid-call count;
GS-2 code-scanned inventory; GS-3 explicit terminal-outcome subset control;
GS-4 native-exception sentinel) are carried into the later Q/M gates — none
block merge or deploy of shadow. C-SH5 (Chroma audit is not a compensating
control) is carried intact.

<!-- src: ./KIRO-2026-10-18-issue-286-scoped-proof-shadow-review.md — C-SH1..C-SH6 / SC-1,CC-1,CC-2,FC-1,TC-1..3,MC-1 binding conditions -->
<!-- src: ../../incremental_mutation_proof.py, ../../chroma_store.py, ../../incremental_jsonl.py, ../../config.py, ../../complete_data_restore.py, ../../scripts/generate_scoped_proof_writer_inventory.py, ../../tests/test_issue_286_scoped_proof_shadow.py — all read/verified at dbf45c5 -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex routing and future Q/M/R/P evidence -->
