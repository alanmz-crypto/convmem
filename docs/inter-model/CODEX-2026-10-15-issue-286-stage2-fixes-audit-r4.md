# [Arc Codex #286] Stage 2 safety audit — round 4

**Verdict: FAIL at `74c8ee7b341c6d3e21cf501c0ab0cdd84afa9ea7`.**

**Auditor:** Codex, performing Ryan's explicitly requested independent safety re-audit.
**Date:** 2026-10-15 UTC. **Implementation owner:** Cursor; supplied verification: Claude rounds 20–21.

Cursor's corrective 16 closes all three round-3 findings and both lower-severity observations in the exercised scenarios. The expanded per-source lock serializes admission, execution, and failure accounting across threads and processes. However, moving admission inside `run()` introduces two independently reproduced regressions: corrupt retry evidence is overwritten and subsequent attempts resume transform work; refused attempts without a pending transaction accumulate complete source snapshots. Both new safety assertions pass at round-3 revision `7d46e6e` and fail at the requested revision.

This report supplies evidence for Ryan's disposition. It grants no implementation, merge, deployment, provider call, activation, or canary authority.

## Exact revisions and scope

- **Audited implementation:** `origin/fix/2026-10-12-issue-286-stage2-wedge-fixes`, exactly `74c8ee7b341c6d3e21cf501c0ab0cdd84afa9ea7`, confirmed after fetching origin. Reviewed all eight changed files in `7d46e6e..74c8ee7`, including corrective commits `9324d03`, `928700b` and inventory regeneration `74c8ee7`. Relevant callers and retry-state helpers were inspected too.
- **Prior audit:** Codex's round-3 FAIL report at `3af90a3001159464f82770d513c917b0addd1a4b`, branch `docs/2026-10-15-issue-286-stage2-fixes-audit-r3`; its unchanged seven scratch probes are the reproduction baseline.
- **Supplied verification:** Claude's report at `1a8fd7e98b566866b0654bb85dc2328cd2b5bdae`, on `origin/docs/2026-10-12-issue-286-stage2-fixes-handoff`, in `docs/inter-model/CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md`. Rounds 20–21 and their appended probes were read; the six appended tests were independently rerun. Claude's full-suite comparison and diff-coverage census are supplied evidence, not independently reproduced results of this audit.
- **Report branch:** `docs/2026-10-15-issue-286-stage2-fixes-audit-r4`, created from fetched `origin/main` at `c6f07241ccf1a71d9d874fee963a37b04091b3ce`. Only this report is a tracked change. Implementation line references below refer to `74c8ee7`, not the documentation branch.

The Arc Codex STATUS brief and the reproduction/verification guidance were read. The STATUS brief's older operational narrative is not evidence of current deployment. Known #393, Z1 and X2–X5 are not re-audited or used as blockers. No Kiro verdict was solicited and no conflict-adjudication process was invoked.

## Blocking findings

### R4-F1 — High: an admission refusal rewrites corrupt retry evidence and re-admits transform work

**Locations:** `incremental_jsonl.py:2540,2641,2840–2848`; `incremental_retry_state.py:33–59,297–324`.

Admission now runs inside `coordinator.run()`, within the wrapper's ordinary execution-error handler. When `_read_or_raise_unavailable` detects malformed retry JSON, it correctly raises `retry_state_unavailable`. The wrapper then calls `_raise_incremental_retry_refusal`, which calls `record_incremental_retry_failure`. That helper reads the same corrupt file through the permissive `_read`, treats it as an empty state, and replaces the evidence with valid JSON containing `attempts_on_prefix=0`. A later invocation can reserve and perform another transform. The source lock prevents competing writes but does not prevent this reset by the current owner.

**Scratch reproduction:** use the actual admitted Codex route, real source lock and state files, fake providers, and a synthetic `_write_prepared` filesystem failure. Reach the same-error hold after two fake summaries; a third invocation is refused without another summary. Replace only the scratch `retry_state.json` with malformed JSON, then invoke the route three more times against the unchanged source.

**Observed at `74c8ee7`:** the first invocation returns `retry_state_unavailable` but replaces the corrupt bytes with a new state and counter zero. The next two invocations perform two additional fake summaries. Total summaries rise from two to four on the same prefix, while persisted attempts rise only to two. The malformed state was injected once; it was not repeatedly reset by the test.

**Control at `7d46e6e`:** all three invocations return `retry_state_unavailable`; the corrupt bytes remain unchanged and the summary count remains two. Before this delta, admission was outside the execution-error handler.

**Impact and boundary:** this violates the fail-closed retry-evidence contract and exceeds the three-attempt bound after one corruption event. The corruption is an injected filesystem-state fault, not a claim that atomic publication normally truncates its own JSON. Watcher quarantine can suppress further automatic invocations; the actual route remains callable by manual indexing, the same surface exercised by the existing retry tests. The retained `test_q2c_corrupt_retry_state_fails_closed` checks only the first refusal and summary count; it misses the evidence rewrite and next invocation.

**Required correction:** distinguish pre-work admission failure from a failed admitted attempt. Preserve unavailable/corrupt accounting evidence and continue refusing until explicit recovery; do not replace it with a new zero-count history. Keep the source lock across admission and subsequent accounting. Add a repeated-invocation test that checks both unchanged corrupt bytes and zero additional transform work. No fix was made in this audit.

### R4-F2 — Medium: already-refused retries leak a complete source snapshot on every invocation

**Locations:** `incremental_jsonl.py:2542–2544,2641,2747–2749`; snapshot creation at `:770–803`.

For a source without a pending transaction, the new ordering captures and durably publishes a fresh UUID-named source snapshot before enforcing retry admission. If admission then refuses, neither `run()`'s `finally` nor the wrapper removes that snapshot. There is no transaction pointing to it. Later invocations create different snapshot directories, so the leak grows with the number of refused attempts.

**Scratch reproduction:** use the real route and fake summaries, with `ingest.distill` raising a synthetic failure. The existing transform-failure path cleans its transaction and snapshot; after two failures the same-prefix hold is established and no transaction remains. Invoke the unchanged source four more times.

**Observed at `74c8ee7`:** all four extra invocations return `live_route_refused` and perform no additional summaries, but retained snapshot-file counts grow `1, 2, 3, 4`; retained bytes grow `1234, 2468, 3702, 4936`, exactly one complete 1,234-byte source per refusal. No transaction exists after any of these calls.

**Control at `7d46e6e`:** the identical six-invocation sequence leaves zero snapshot files and zero snapshot bytes throughout; both revisions perform only two fake summaries.

**Impact and boundary:** a hold still bounds provider work, but repeated manual invocations of a held source now consume disk proportional to the full selected prefix each time, with no pending transaction to clean these copies later. Watcher quarantine limits the automatic case; this is not evidence of an automatic infinite loop. Large sources make repeated refused retries materially expensive in disk and I/O.

**Required correction:** preserve the successful unchanged-prefix short-circuit while either admitting before snapshot publication or cleaning only the newly captured, unowned snapshot on refusal. Never delete an existing transaction's recovery snapshot. Test repeated refusal after a transform failure that leaves no transaction. No fix was made here.

## Round-3 disposition and source-lock evidence

- **R3-F1 — closed for the original concurrency defect.** Independent nonblocking `flock` checks show another file descriptor cannot acquire the source lock during admission, `_write_prepared`, failure recording, or successful-state clearing. It becomes acquirable after every tested return/refusal. A second real route remains blocked while the first is paused inside failure accounting; both reservations and both consecutive failures are preserved. Eight concurrent callers with failure-record publication disabled perform exactly three fake summaries and persist three reservations, then refuse five callers. Claude's extracted concurrency probe independently reran: eight threads and six forked processes each perform two fake summaries and retain two attempts. R4-F1 is a different admission-error regression, not recurrence of lost concurrent reservations.
- **R3-F2 — closed.** The original repair drift interleaving now completes with `repaired=1`, `skipped=0`, `missing_source=0`. Both embedding callbacks run at `(index_write_lock_depth, production_chroma_store_session_depth) == (0, 0)`. The refreshed reader is document-accurate and no undefined-name exception occurs.
- **R3-F3 — closed.** The original monitor skip-to-update interleaving now completes with five verifications, `errors=0` and `drift_refused=0`. Exactly one replacement embedding runs at `(0, 0)`; no empty embedding reaches Chroma.
- **R3-O1 — closed.** Export failures after both insert and update invalidate the ledger cache. The independent probe contains no explicit test-side cache invalidation after either failed export. The retained corrective test itself calls `invalidate_ledger_index_cache` before its post-write assertion, so that test alone is insufficient evidence; the unchanged original counterexample and the new probe cover the gap.
- **R3-O2 — closed.** The original temporary-Git-repository probe now finds both tracked artifact and tracked review-bundle writers. The inventory/baseline checks pass at the regenerated tip.

The source lock wraps the same existing commit order: incremental source lock, governed source lock, C1/write-store scope. The broadened outer scope adds retry admission and accounting; provider preparation remains outside C1. A successful first run followed by an unchanged run clears state while holding the source lock; the unchanged run performs no retry reservation or transform work. The class-capability fallback in `928700b` exists for minimal test doubles; the constructed production coordinator has both lock helpers. No executed production lock bypass was found there.

Claude round-21's four additional probes also pass: approved-ledger drift recovery, bounded refusal under persistent drift, dedupe approval of one then all remaining rows, and out-of-range dedupe refusal. These results do not cover R4-F1/F2's repeated error-path behavior.

## Execution results and limits

Implementation worktree: `/home/lauer/.kiro/audit-286-r4/code`, detached at the exact target. Report worktree: `/home/lauer/.kiro/audit-286-r4/docs`. Probes and outputs: `/home/lauer/.kiro/audit-286-r4/harness/`. The shared checkout was not switched or edited.

The runner uses `/home/lauer/miniforge3/envs/convmem/bin/python`, `env -i`, private HOME/TMPDIR, disabled plugin autoload/bytecode/pytest cache, closed-port provider endpoint overrides, fake providers, and a pre-import audit hook denying Python network connections and production-path opens. Repository fixtures redirect configuration and writer defaults to scratch. All new probe code remains outside tracked worktrees. These controls are the scoped round-3 harness, not a claim to certify every native-library behavior.

Independent results:

- **Unchanged original round-3 probes:** 2 passed, 5 failed, 12.42 s. Both safety controls still pass. The five failures are old assertions of unsafe behavior that no longer holds. The old concurrency barrier times out because the lock now serializes its participants; it records one initial reservation and two total summaries, not four lost reservations. That timeout is a limitation of the old reproducer, not a production failure. New concurrent tests establish the corrected bounds directly.
- **Focused repository suite:** 134 passed plus 5 subtests, 11.55 s. Includes corrective 12, wedge probes, the retained round-3 safe-direction tests, Claude rounds 8b/9/15–17, upsert, ledger-document, monitor, add-severity, propose-decision, and live-boundary tests.
- **Inventory/baseline subset:** 54 passed, 11.37 s: `test_r2b_v2_corrective_viii.py`, `test_r2b_v2_implementation_revision.py`, `test_shadow_writer_coverage_scan.py`, `test_shadow_writer_gate_c3.py`, and `test_incremental_jsonl_canary_baseline.py`.
- **Final scratch checks:** 13 passed, 2 failed, 5.04 s. Seven new independent tests, two stricter round-3 recovery checks, and six extracted Claude round-20/21 tests. The two failing safety assertions are exactly R4-F1 and R4-F2.
- **Differential controls:** the same two final safety assertions pass unchanged at `7d46e6e`: 2 passed, 1.49 s. The earlier diagnostic runs reproduce the same old/new split.
- **Whitespace:** `git diff --check 7d46e6e..74c8ee7` passed. Implementation checkout remained clean.

No full-suite rerun, D1 subprocess sequence, independent coverage census, timing benchmark, or production canary was performed. Claude's full-suite comparison is not promoted to an independent audit result. The two final failing assertions establish new regressions, rather than the unrelated environment failures described in older reports.

The required startup doctor/brief/unresolved and corpus search were read-only orientation; doctor exited 0 with nonfatal warnings. No paid provider call, production data mutation, service/config/runtime change, implementation fix, PR creation, merge, or force-push was performed. Track A indexing is withheld under Ryan's task-specific no-production-state/no-paid-call restriction, as in round 3; session ingestion would exceed that scope.

## Reproduction artifacts

All paths in this section are under `/home/lauer/.kiro/audit-286-r4/harness/` unless stated otherwise.

- `test_audit_r4.py`: seven independent checks; SHA-256 `fb7726ec3fa4170314568928d230d872e0f6364ac18e1463b002a3bb176e64bd`.
- `test_audit_r3.py`: unchanged original seven probes; SHA-256 `3d8cab2077ee58a298dd599ce882a1f9cbfe195d33b9f6d7a3d6ba8db19718c5`.
- `test_r3_recovery_strict.py`: original repair/monitor scenarios with explicit successful-outcome assertions; SHA-256 `aebd3576420fd86606e5413f6a17707de38616559ff70470bc09040d62ebd014`. Only those two named tests were selected.
- `test_claude20.py` / `test_claude21.py`: extracted directly from the exact supplied report; SHA-256 `830e2ba757dbdb185276cefd0b9c78abe0b4f850a58e0369b0b785e9cb6a5abf` / `873af8cf2e2c996162980279729af25d70d4e3365543c71083d69ed9b235d451`.
- `run-tests.sh`: SHA-256 `41c311b89b6192d7a2aeebbc135a56092e71f2385eca99b4808b00ab359599d4`.
- `sitecustomize.py`: SHA-256 `dcf8ea6d65be2103cc5deec8cc9a864dd779aa209da079a798957f6099e7a78a`.
- Final evidence: `final-results.txt`, `baseline-final-results.txt`, `r3-original-results.txt`, `focused-results.txt`, `inventory-results.txt`. Earlier diagnostic runs are retained alongside these files.

Reproduce both new safety failures with a new, unused basetemp:

```bash
bash /home/lauer/.kiro/audit-286-r4/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r4/harness/base-reproduce-new \
  -q -s \
  /home/lauer/.kiro/audit-286-r4/harness/test_audit_r4.py::test_corrupt_retry_admission_differential \
  /home/lauer/.kiro/audit-286-r4/harness/test_audit_r4.py::test_refusal_snapshot_growth_differential
```

For the old-revision control, use `/home/lauer/.kiro/audit-286-r3/harness/run-tests.sh`, a new basetemp under its own `harness/` directory, and the same two absolute test selectors. That runner points to the retained exact `7d46e6e` checkout. The scenario descriptions above are sufficient to reconstruct the probes if local scratch artifacts are unavailable.

## [Arc Codex #286] Handoff

I finished: round-4 safety re-audit of exact implementation `74c8ee7` — **FAIL**.
Next step: Ryan routes the two new blockers for correction, then requests an exact-revision recheck.
Next lane: Ryan for disposition; Cursor for implementation if authorized.
See my work: this report's R4-F1/R4-F2 reproductions and old/new differential results.

Branch: `docs/2026-10-15-issue-286-stage2-fixes-audit-r4`. Final documentation SHA and explicit-refspec push result are supplied in the chat handoff. This report is the only tracked change; no PR was requested or created.

### Optional PR text for Ryan

**Title:** Document retry-evidence reset and snapshot leaks in Stage 2

**Description:**

This publishes the round-4 FAIL verdict so Ryan can route two remaining corrections before accepting Stage 2. Codex audited Cursor's implementation at exact revision `74c8ee7` on 2026-10-15, independently reran the round-3 probes and Claude's rounds 20–21 additions, and checked the expanded source lock. All five round-3 findings are corrected, but corrupt admission evidence is overwritten and allows further transform attempts, and refused retries without a transaction retain full source snapshots. Only this report changes; implementation and production state are untouched.

Validation: 134 focused tests plus 5 subtests and 54 inventory/baseline tests pass. Final scratch checks yield 13 passes and two safety failures; the same two assertions pass at `7d46e6e`. Thread/process serialization and provider-outside-C1 checks pass. No full-suite or production run was performed.

**TL;DR:** [Arc Codex #286] Documentation only; **FAIL** on two new regressions, with the original five findings closed.

## TL;DR

- [Arc Codex #286] **FAIL at `74c8ee7`:** corrupt retry evidence is reset and permits more work; refused retries leak full source snapshots.
- All original round-3 findings close in the exercised paths. Source-lock serialization, failure-accounting exclusion, drift recovery and cache invalidation pass.
- Both new safety assertions pass on `7d46e6e` and fail on `74c8ee7`. Only this audit report is committed; probes remain scratch-only.

<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc orientation; no activation authority -->
<!-- src: /home/lauer/.kiro/audit-286-r3/docs/docs/inter-model/CODEX-2026-10-15-issue-286-stage2-fixes-audit-r3.md, /home/lauer/.kiro/audit-286-r4/harness/test_audit_r4.py, /home/lauer/.kiro/audit-286-r4/harness/final-results.txt, /home/lauer/.kiro/audit-286-r4/harness/baseline-final-results.txt — prior findings and independent reproduction evidence -->
