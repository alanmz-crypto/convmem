# Design review: issue #286 Stage 2 wedge fixes (C1, C2, relaxed invariants)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Reviewer:** Kiro (design review lane — review only; no code, tests, scripts, or config)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `c7072fc` (base `origin/main` `458b9f6`)
**Scope:** C1 (one store-wide index write window), C2 (source-scoped recovery), and the two relaxed invariants. C3/C4 read only as far as they bear on C1/C2 soundness and the review questions.

**Verdict: PASS with conditions.**

The C1/C2 design is sound and the C2 argument holds *given* C1's coverage, which I verified across every production write path I could find. The conditions are a cross-arc boundary issue (G7), one PR-draft accuracy fix, and a recommendation on G5 for canary 2. None of the conditions change the C1/C2 mechanism; they are disposition and accuracy items for Ryan before merge.

---

## What I read

- Handoff spec: `CURSOR-2026-10-12-issue-286-stage2-fixes-handoff.md` (C1–C4, integration points, acceptance).
- Verify round 6: `CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md` — "Review focus" and "PR draft".
- Diff `origin/main...c7072fc`: `purge_locks.py`, `incremental_jsonl.py`, `ingest.py`, `ingest_dedupe.py`, `monitor.py`, `convmem.py`, `process_lock.py`, `watch.py`, `watch_circuit_breaker.py`, `incremental_retry_state.py`, `doctor.py`, `eval_corpus/r2b_v2/coverage/inventory.py`.
- Arc brief: `STATUS-codex-jsonl-production-integration.md`.

Confidence that I have the material the questions depend on: **95%**. The 5% is the full repo-wide writer census (I traced the production write paths the handoff names plus the CLI write commands; a writer in a path I did not open could still exist — see Q1).

---

## C1 — one store-wide index write window

**Design: sound. Confidence 90%.**

The implementation adds `purge_locks.index_write_flock(cfg)`, a single exclusive flock at `<data_root>/locks/index_write.lock`, re-entrant per thread via a thread-local depth counter. The lock order is enforced by `assert_lock_ordering_ok`:

- `source` may not be acquired while holding `export`;
- `index_write` may not be acquired while holding `export`;
- `export` may not be acquired **without** `index_write` already held.

This encodes the intended order `source_flock → index_write → Chroma writer session → export_flock`. The export helper (`export_flock_path`) auto-acquires `index_write` when it is not already held, so a bare `export_flock` call cannot escape the window. That is a good defensive choice: it means a future writer that only touches the export still enters the shared window without the author remembering to wrap it.

Coverage I verified writes `index_write_flock`:

| Writer | Path | Lock held |
|---|---|---|
| Incremental apply | `incremental_jsonl._commit_generation` | yes — wraps snapshot → `_apply_prepared` → `_write_checkpoint` → `_reconcile_export` → `_reconcile_dedupe`, inside `source_flock` |
| Incremental rollback | `incremental_jsonl._roll_back_apply` (replay/rollback entry) | yes — digest captured and verified under the same hold |
| Legacy chunk write | `ingest._commit_chunk_to_stores` | yes — inside `source_flock`; `export_flock` now nested inside it |
| Legacy reindex snapshot | `ingest._snapshot_reindex_rows` | yes (now takes `cfg`) |
| Legacy reindex prune | `ingest._prune_completed_reindex` | yes (per handoff; same pattern) |
| Ingest dedupe sidecars | `ingest_dedupe.persist_ingest_dedupe` | yes |
| `convmem add` | `convmem.add` | yes |
| `convmem forget` | `convmem.forget_command` | yes |
| `convmem monitor` | `monitor.run_monitor` via `live_cfg` | yes **when `live_cfg` is passed** (CLI passes it) |
| `convmem index --file` / observe | `convmem.index` | yes |

**No lock across paid work.** I confirmed `_apply_prepared` consumes already-prepared artifacts (`summary_embedding`, `row["embedding"]` are read from the prepared cache) and makes no summarize/distill/embed call. Paid work lives in the prepare phase, which runs before the window opens. So the window covers store and export writes only, and a slow model call cannot stall every writer. This satisfies the binding "never hold it during paid provider work" requirement.

**Soundness caveat (the basis for condition CO-1 below).** `monitor.run_monitor` only takes the lock when `live_cfg is not None`; the default is `None`, in which case `ingest_observation` writes summaries/units with no `index_write` lock. In production the CLI (`convmem.monitor_command`) now passes `live_cfg`, so the live monitor path is covered. The residual risk is any *other* caller of `run_monitor(... )` (or any direct `ingest_observation` / `store.add_*` caller) that does not pass `live_cfg` and does not wrap the write. I did not find such a caller in the paths I read, but I did not exhaustively census every `add_unit`/`add_summary`/export-append call site in the repo. This is exactly the hole that would make a C2 isolation failure a false "foreign writer." See Q1 and CO-1.

---

## C2 — source-scoped recovery

**Design: sound. Confidence 88%.**

Two changes:

1. **Isolation is pinned to this attempt, not the journal.** `_commit_generation` now captures `attempt_non_source = self._non_source_collection_digest()` immediately after acquiring `index_write_flock`, and after the apply calls `_verify_non_source_collections(attempt_non_source)`. The compared baseline is the state at the start of *this* locked attempt, taken under the lock, rather than the digest frozen in the rollback journal at the original transaction start. `_roll_back_apply` does the same: capture under the lock, restore, verify against the attempt-start digest. Because the lock is held across capture → apply/restore → verify, no cooperating writer can move non-source state inside that span, so a mismatch now means a genuinely non-cooperating writer. This is the correct reading of the spec.

2. **Export rollback no longer demands byte-identical foreign bytes.** The old `_restore_export` recomputed a foreign digest/byte/line authority and raised `rollback_export_foreign_changed` if it differed from the before-image. That branch is removed. Foreign (not-owned-by-this-source) lines now pass through unchanged and in order. Source-owned lines are validated against `allowed_unit_ids = preimage_unit_ids ∪ current_store_unit_ids_for_source`; a source-owned line whose id is outside that set, or a before-image id whose parsed content changed, is counted and dropped (see relaxed invariant 2). The old positional `foreign_lines_before` gate on re-inserting source lines is gone; restored source lines are appended after the pass. The authority checks that remain — rollback journal hash, source path, prepared keys, prefix revalidation — are untouched.

Both changes are internally consistent with C1: the isolation digest is only trustworthy because the lock makes the capture-to-verify span exclusive.

---

## Answers to the five questions

### Q1 — Is the C2 argument sound? Can any writer change summaries, units, or the export outside the C1 lock?

**The argument is sound, conditional on C1 coverage being total. Confidence 85%.**

The argument — "C1 forbids foreign writes during an apply, so foreign changes *between* attempts are legitimate" — is valid *if and only if* every writer that can mutate summaries, units, or the export acquires the C1 lock. If one does not, then a foreign write **can** land during the apply window, `_verify_non_source_collections` will (correctly) catch it as `non_source_isolation_changed`, and C2 will treat the next attempt's divergence as legitimate between-attempt drift — silently absorbing a write that actually overlapped the apply. The failure mode is not a crash; it is a lost isolation guarantee.

So the question "can any writer change summaries, units, or the export outside the C1 lock?" is the load-bearing one. From the paths I read, the answer in **production** is no: `_commit_chunk_to_stores`, `_snapshot_reindex_rows`, `_prune_completed_reindex`, `persist_ingest_dedupe`, `convmem add/forget/monitor/index` all hold the lock, and `export_flock_path` self-acquires it. The two gaps I could not fully close:

- `run_monitor(live_cfg=None)` writes unlocked. Production passes `live_cfg`; non-production callers may not.
- I did not exhaustively enumerate every `store.add_summary` / `store.add_unit` / export-append call site repo-wide. The semantic/deferred dedupe writers are named in the handoff as "if they write those collections" — the author was asked to list the writers they wrapped. **I did not find that writer list in the verify doc's PR draft.**

Net: the mechanism is correct; the guarantee is only as strong as the census. I accept it with condition CO-1 (publish the wrapped-writer list and confirm no unlocked production writer of summaries/units/export remains, including the semantic/deferred dedupe writers).

### Q2 — Accept or reject relaxed invariant 1 and relaxed invariant 2; is the diagnostic's definition right?

**Relaxed invariant 1 (foreign export + store state need not match transaction start between attempts): ACCEPT. Confidence 90%.**
Under C1 the only time foreign state could change relative to the transaction start is *between* locked attempts, which is legitimate concurrent progress by another cooperating source. Pinning isolation to the attempt-start digest instead of the journal digest is the right scope. This directly unwedges P1: a second source indexing between retries no longer poisons recovery forever.

**Relaxed invariant 2 (source-owned export tamper dropped with a diagnostic instead of refused): ACCEPT with a caveat. Confidence 78%.**
The rationale is correct: by the time export rollback runs, the store rows for this source have already been restored (unknown rows deleted without a tamper veto). Refusing in the export after the store is restored would leave a half-rolled-back transaction that can never complete — strictly worse than dropping. So "drop and continue" is the right liveness choice. The caveat: this is a genuine *weakening* of a tamper guarantee for source-owned lines — tamper on this source's own export line is now a `stderr` line and a counter, not a refusal. That is acceptable because (a) the store, not the export, is the serving projection, and (b) the before-image is the authority being restored. But it means a silent-ish data event is downgraded to a diagnostic, so the diagnostic must be observable. See the diagnostic assessment next.

**Is the diagnostic's definition right? Mostly, with one wording concern. Confidence 72%.**
The dropped-line count (`[incremental] rollback dropped N unexpected export lines for <source>`) counts two cases: (a) source-owned ids neither in the before-image nor in current store rows; (b) before-image ids whose parsed content changed. It deliberately does *not* count a line whose id the store also holds (that is a legitimate store-backed line and is removed only because the before-image is authoritative). That partition is defensible. Two concerns:
- **Observability.** It is a `print(..., file=sys.stderr)` with no structured record and no doctor surface. Round 6 notes the watcher can drop child stderr (P5, unauthorized here). A dropped-tamper event that only exists on a line the watcher may discard is close to invisible. I would want the drop count folded into the checkpoint/last_evidence or the doctor WARN before this runs under a live watcher — not blocking for a hermetic merge, but a canary-2 condition.
- **Wording.** "unexpected export lines" conflates benign (store-backed id that simply is not in the before-image) and malign (content-changed before-image line) causes under one count. For an operator this is fine as a tripwire; for forensics it is lossy. Minor; not blocking.

Net on Q2: accept both invariants; make the drop diagnostic durable (structured record or doctor field) before canary 2.

### Q3 — G5: should a clean rollback hold the session until `--clear-quarantine`, or release it when the prefix changes?

**Recommendation for canary 2: release a clean `rolled_back` on prefix change, the same as a wedged quarantine. Confidence 70%.**

The current branch is asymmetric, and the asymmetry runs the wrong way round. In `watch_circuit_breaker.should_skip_refusal_quarantine`:
- a `wedged_incremental_transaction_*` quarantine is released when the live prefix digest no longer matches the stored one (good — new content is a new chance);
- any other refusal, **including `rolled_back`**, returns `True` unconditionally — held until `convmem watch --clear-quarantine`.

But a clean `rolled_back` is the *more* benign outcome: the store and export were restored to a consistent before-image, nothing is torn. A wedged transaction is the *less* benign one. Holding the benign case harder than the wedged case is backwards. The practical consequence: after a clean rollback, the session will not re-index even after the user appends new messages, until someone manually clears it — which on an active session is surprising and defeats the point of a *clean* rollback.

I would keep the hold-until-clear behavior only for terminal/ambiguous refusals, and let a prefix change release a clean `rolled_back` just as it releases a wedged one. The burn-safety argument for holding is weaker here because the next attempt on a changed prefix reuses prepared work (0 paid calls for already-prepared chunks, per the C2 acceptance case).

This is explicitly a canary-2 decision in the verify doc, and I agree it does not block the hermetic merge. My recommendation is: **ship c7072fc as-is, and in canary 2 measure whether clean-rollback sessions get stuck; if they do, move `rolled_back` to the prefix-release branch.** Confidence is 70% rather than higher because I have not seen canary data on how often a clean rollback is immediately followed by legitimate new content versus by a genuinely bad source that should stay held.

### Q4 — G7: is adding `review-bundles/` to the R2b writer-scan skip list acceptable for that arc?

**Acceptable in intent, but it is a cross-arc guard change made inside a Codex-arc branch, so it needs explicit R2b-arc sign-off. Confidence 80% on acceptability, condition CO-2 on process.**

`_SKIP_SCAN_PREFIXES` in `eval_corpus/r2b_v2/coverage/inventory.py` excludes directories from the R2b undocumented-writer scan (`ROOT.rglob("*.py")`). The existing entries are all non-production trees (`tests/`, `docs/`, `.worktrees/`, `.tmp/`, `.git/`, `node_modules/`). `review-bundles/` is a gitignored, untracked local folder (`.gitignore` lines 43–44) that holds review artifacts. The scan walks the working tree, so a stray `.py` inside a local `review-bundles/` would otherwise be scanned and could perturb the deterministic R2b inventory / implementation-revision digest. Excluding ephemeral local review artifacts from a *production writer* census is consistent with the other skip entries, and the risk is low: review bundles are not production and would not contain a governed writer by design.

The concern is boundary, not substance. This edits an R2b-arc guard (R2b capture authorization) from a Codex-arc branch. The STATUS protocol and arc-boundary rule say a lane should not change another arc's guard without that arc's authorization. The `governed_mutation_sinks` coordinate was also re-pinned (`convmem.py:699` → `:721`) because the C4 `--now` flag shifted lines — that is a mechanical regeneration and is fine. But *adding a new skip prefix* is a policy change to R2b's coverage surface. It should be called out to whoever owns R2b and ideally land in its own tiny change, not ride inside the wedge-fix PR unremarked. The PR draft does mention it ("G7: review-bundles/ was added to the R2b writer-scan skip list"), which is the right disclosure; I want it confirmed-acceptable by the R2b owner before merge rather than assumed.

### Q5 — Does the PR draft misstate anything in the design?

**One factual mismatch and two softer gaps. Confidence 85%.**

- **Full-suite claim vs. verdict.** The PR draft states "The hermetic full suite at main `458b9f6` and at the tip fails the same 151 known local tests, with 0 failing only at the tip." The round-6 verdict says the full suite was "still running when I pushed this; I'll add the result in a follow-up commit." The PR draft asserts a completed full-suite result that the verdict itself had not yet confirmed. This must be reconciled before Ryan relies on it — either the follow-up run finished and the number is real, or the PR body is ahead of the evidence. **Condition CO-3.**
- **"Relaxed invariants (reviewed by Kiro)" / "Kiro reviewed it".** The draft pre-asserts Kiro review as done. This document is that review; it returns PASS *with conditions*, not an unconditional pass. The PR body should say "reviewed by Kiro: PASS with conditions (see KIRO-2026-10-13-…-design-review.md)" rather than implying a clean pass.
- **Writer list.** The handoff's acceptance criteria require the report to "list the writers wrapped by the C1 lock" and confirm the lock order and no-lock-across-paid-calls. The PR draft gives the lock order and the no-paid-call claim but does not include the enumerated writer list. That list is the evidence behind the C2 soundness argument (Q1) and should be in the PR body or linked report.

Otherwise the PR draft's description of the mechanism (one store-wide lock; source-scoped replay/rollback; bounded retries surfaced to watcher and doctor; watcher ignores opens; `index --file` defers) matches the code I read.

---

## C3 note (read for C1/C2 bearing)

The bounded-retry logic (`incremental_retry_state.record_incremental_retry_failure`) returns "refuse" when the *prior* persisted record already matched the same `error_code` + `prefix_digest` — i.e. the second identical failure on an unchanged prefix exits 91. A success clears the state; a prefix change resets `consecutive` to 1. This matches the C3 "twice in a row → refuse" contract and interacts correctly with C2: a wedged transaction that C2 cannot recover will fail identically twice and then quarantine, rather than retrying and paying forever. The doctor WARN names source, transaction id, code, and remedy, and additionally lists stale `PREPARING`/`APPLYING` transactions — which is how the 3 stale Stage 2 transactions will surface after deploy. Consistent with the design; no finding.

One small edge the verify doc already flags (K1): an error raised before any prefix digest is known records an empty digest and is never held, so it re-spawns on each event. These fire before paid work and exit 91, so the burn exposure is bounded, but a persistently crashing pre-digest path would spin the watcher. Not in scope to fix here; worth a canary-2 watch item.

---

## Conditions (for Ryan, before merge / before canary 2)

| ID | Condition | Blocks | Why |
|---|---|---|---|
| CO-1 | Publish the enumerated list of writers wrapped by the C1 lock, and confirm no unlocked production writer of summaries/units/export remains — explicitly covering the semantic/deferred dedupe writers and any non-CLI `run_monitor`/`ingest_observation` caller. | Merge confidence in the C2 argument | C2's "foreign changes between attempts are legitimate" is only true if C1 coverage is total (Q1). |
| CO-2 | Get R2b-arc owner acknowledgement that `review-bundles/` belongs in `_SKIP_SCAN_PREFIXES`; keep the disclosure in the PR body. | Arc-boundary cleanliness | Cross-arc guard change made from the Codex branch (Q4). |
| CO-3 | Reconcile the PR draft's "151 known local tests, 0 failing only at the tip" with the round-6 verdict's "full suite still running"; state Kiro review as PASS-with-conditions, not a clean pass. | PR accuracy before Ryan merges | Draft asserts a result the verify doc had not confirmed (Q5). |
| CO-4 (canary 2) | Make the C2 export-drop event durable (structured record or doctor field), not only a watcher-droppable stderr line. | Not merge; canary 2 | Relaxed invariant 2 downgrades tamper to a diagnostic; it must be observable (Q2). |
| CO-5 (canary 2) | Decide G5: release a clean `rolled_back` on prefix change like a wedged quarantine, rather than hold-until-clear. | Not merge; canary 2 | Current asymmetry holds the benign case harder than the wedged case (Q3). |

CO-1 through CO-3 are documentation/disposition items on an otherwise correct mechanism; none require a code change to the C1/C2 logic. CO-4 and CO-5 are explicitly deferred to canary 2 by the verify doc and I concur.

---

## Confidence summary

| Judgement | Confidence |
|---|---|
| C1 lock design (order, re-entrancy, no-lock-across-paid-work) is correct | 90% |
| C2 isolation re-scoping (attempt-start digest under lock) is correct | 88% |
| C2 export rollback re-scoping is correct | 85% |
| Q1: C2 argument sound, conditional on total C1 coverage | 85% |
| Q2: accept invariant 1 | 90% |
| Q2: accept invariant 2 (tamper → drop) | 78% |
| Q2: drop diagnostic definition acceptable, needs durability | 72% |
| Q3: release clean rollback on prefix change (canary 2) | 70% |
| Q4: `review-bundles/` skip acceptable in intent | 80% |
| Q5: PR draft has a full-suite mismatch to fix | 85% |
| Overall: PASS with conditions | 86% |

---

## Verdict

**PASS with conditions.** C1 and C2 are correctly designed and mutually consistent; the C2 argument is sound given C1's coverage, which I verified across the production write paths. Merge the hermetic branch after CO-1 (writer-list evidence), CO-2 (R2b owner ack), and CO-3 (PR-draft accuracy). CO-4 and CO-5 are canary-2 conditions, not merge blockers. I found no defect in the C1/C2 mechanism itself.

── Next steps ──
- I finished: Kiro design review of C1, C2, and the relaxed invariants at `c7072fc`.
- Next step: Ryan resolves CO-1/CO-2/CO-3, then opens/merges the PR; CO-4/CO-5 fold into canary 2.
- Next lane: Ryan (disposition + merge); Cursor only if CO-1 surfaces an unlocked writer.
- See my work: `docs/inter-model/KIRO-2026-10-13-issue-286-stage2-fixes-design-review.md` on `docs/2026-10-13-issue-286-stage2-fixes-design-review`.

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Codex | The arc making Kiro/Codex JSONL transcript indexing incremental and crash-replayable; see `STATUS-codex-jsonl-production-integration.md`. |
| C1 | Spec item: one store-wide exclusive index write lock covering all summary/unit/export writes. |
| C2 | Spec item: recovery (replay + rollback) proves only this source's state, not foreign state at transaction start. |
| C3 | Spec item: bounded retries — a second identical failure on an unchanged prefix refuses (exit 91). |
| C4 | Spec item: watcher ignores non-writing FS events and `index --file` defers to a live watcher. |
| G5 / G7 / K1 | Round-6 "Review focus" items: G5 = clean-rollback quarantine release policy; G7 = R2b skip-list change; K1 = empty-prefix-digest re-spawn edge. |
| P1–P7 | Problems from the Stage 2 canary report; P1 = the wedge, P2 = agent self-indexing, P3 = plain-open index storms (P4–P7 unauthorized here). |
| source_flock / export_flock / index_write_flock | Per-source, per-export-file, and store-wide write locks in `purge_locks.py`; required order is source → index_write → Chroma → export. |
| rollback journal / before-image | The persisted authority (hash-bound) of pre-transaction store rows and export lines used to restore on rollback. |
| non_source_isolation_changed | Error when foreign (not-owned-by-this-source) collection state differs from the expected digest during an apply. |
| rollback_export_foreign_changed | Pre-C2 refusal when foreign export bytes diverged from the before-image; removed by C2. |
| wedged_incremental_transaction_* | Refusal outcome recorded when a transaction fails identically twice; its watcher quarantine releases on a prefix change. |
| rolled_back | Outcome of a clean rollback; currently quarantined until `--clear-quarantine` (G5 question). |
| prefix digest | SHA-256 of the source's complete-prefix content; used to tell "same source state" from "new content". |
| R2b | Separate arc: capture-authorization writer-coverage inventory in `eval_corpus/r2b_v2/`; owns `_SKIP_SCAN_PREFIXES`. |
| governed_mutation_sinks | R2b inventory coordinates naming where governed Chroma writes occur. |
| Track A | Indexing a session chat transcript into convmem (vs. Track B = indexing a `logs/*.md` artifact). |
| canary 2 | The next watcher canary run that will exercise these fixes against the live Stage 2 wedged transactions. |
| CO-1..CO-5 | Conditions this review attaches to its PASS (see Conditions table). |
