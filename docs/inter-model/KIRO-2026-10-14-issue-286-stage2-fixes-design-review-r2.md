# Design review (round 2): issue #286 Stage 2 wedge fixes, correctives 6–11

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-14
**Reviewer:** Kiro (design review lane — review only; no code, tests, scripts, or config)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `0ee6994` (base `origin/main`)
**Weighting:** `git diff origin/main...0ee6994`, weighted toward `git diff c7072fc 0ee6994` (correctives 6–11 since my round-1 review).
**Prior review:** `KIRO-2026-10-13-issue-286-stage2-fixes-design-review.md` at `c7072fc` — PASS with conditions CO-1..CO-5.

## Verdict: PASS with conditions.

Correctives 6–11 are a substantial, well-aimed strengthening of the C1/C2 design I reviewed at `c7072fc`. The headline change — a deny-by-default `_IndexWriteGuardedChromaStore` wrapper plus store-bound lock identity — converts my largest round-1 conditional (CO-1, "the C2 argument is only as strong as the writer census") from a documentation promise into a structural guarantee: a production store mutation without the correct index-write lock now raises rather than writing silently. That is the right design and it closes the load-bearing gap in the C2 isolation argument.

The remaining conditions are two accuracy/disposition items (one carried from round 1) and two performance observations that Ryan should weigh for canary 2. None require a change to the C1/C2 mechanism.

---

## What I read

- Verify round 13: `CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md` — "Review focus", Kiro questions 1–5, and the Z2 finding.
- My round-1 review: `KIRO-2026-10-13-issue-286-stage2-fixes-design-review.md` (`c7072fc`), conditions CO-1..CO-5.
- `git diff c7072fc 0ee6994` for production code: `purge_locks.py`, `chroma_write_store.py`, `chroma_readonly.py`, `observe.py`, `refine.py`, `monitor.py`, `incremental_jsonl.py`, `incremental_retry_state.py`, `inter_model_index.py`, `propose_decision.py`, `repository_knowledge_sync.py`, `source_purge.py`, `doctor.py`, `watch.py`, `watch_circuit_breaker.py`, `eval_corpus/r2b_v2/coverage/inventory.py`.
- `canonical_target` in `chroma_write_guard.py` and `ChromaStore.chroma_dir` in `chroma_store.py` to confirm the symlink-normalization claim.
- `config/agent-protocol.md` and `config/kiro-steering-convmem.example.md` for the Z2 Track-A text.

Confidence that I have the material the questions depend on: **90%**. I did not re-run the suite (review-only lane) and I did not independently re-census every `store.add_*` call site repo-wide — but the guarded-store wrapper (below) makes that census far less load-bearing than it was in round 1.

---

## The structural change since `c7072fc` (bears on every question)

Two additions change the trust model:

1. **`_IndexWriteGuardedChromaStore` (deny-by-default).** `production_chroma_write_session` and `open_production_write_store` now yield the production store wrapped in this guard. Every method that is **not** in an explicit read allow-list (`query_*`, `count_*`, `*_metadata`, `get_unit*`, `ids_for_source`, `snapshot_source_rows`, `non_source_inventory_digest`, `close`, …) calls `require_index_write_lock_held(chroma_dir=self._inner.chroma_dir)` before delegating. Raw `.client` access is refused outright. `_collection(...)` is specially wrapped so even collection-level writes assert the lock.

2. **Store-bound lock identity.** `index_write_flock` records the config's `index.chroma_dir` (resolved) on a thread-local when it takes the outermost lock. `require_index_write_lock_held(chroma_dir=...)` compares that bound directory against the store's canonical directory and raises `index write lock belongs to Chroma dir X, not Y` on mismatch. New lock-ordering assertions also forbid acquiring `source` while holding `index_write`, and forbid acquiring `index_write` while a Chroma writer session is already open — pinning the order `source → index_write → Chroma session → export`.

The consequence for C2: a production writer that forgets the lock, or holds a lock bound to a different store, no longer silently lands a foreign write that `_verify_non_source_collections` would later (mis)attribute to legitimate between-attempt drift. It fails closed with a `RuntimeError` at the write call. This is exactly the backstop round-1 CO-1 asked for, now enforced in code rather than argued from a census.

---

## Answers to the five round-13 Kiro questions

### Q1 — Is binding C1 to its store the right design? (lock remembers `chroma_dir`; guard compares canonical paths; a symlinked `chroma_dir` is accepted.)

**Yes. Confidence 90%.**

Binding the lock to a store identity is the correct way to make "the index write lock is held" mean "held *for this store*". Without it, a lock taken for store A would satisfy a mutation on store B — meaningless in a single-store deployment but a real hole the moment a second store (a scratch worktree, a canary store, a test fixture sharing the process) exists. The guard closes that.

The symlink handling is sound and I verified it is consistent on both sides:

- The lock side resolves `cfg["index"]["chroma_dir"]` with `Path(...).expanduser().resolve()`.
- The guard side resolves the store's `chroma_dir`, which `ChromaStore.__init__` already set via `canonical_target(...)` = `expanduser().resolve(strict=False)`, and `require_index_write_lock_held` resolves it again the same way.

Both reduce a symlinked path to the same real target, so a store opened through a symlinked `chroma_dir` is accepted against a lock bound through the real path (and vice-versa). This matches round 13's claim. The two sides use slightly different spellings (`Path.resolve()` vs `canonical_target(...).resolve()`); they are equivalent today, and I'd note (not block on) that routing both through `canonical_target` would make the equivalence impossible to drift. **Design-level nit N1, non-blocking.**

Deny-by-default is the right polarity: the allow-list is reads, everything else needs the lock. The failure mode on a miscategorised method is a spurious `RuntimeError`, not a silent unlocked write — fail-closed, which is correct for a safety guard. One residual: the guarantee is only as strong as the read allow-list being complete and genuinely read-only. If a listed name (e.g. `snapshot_source_rows`) ever mutates, it bypasses the guard. The names on the list are all plausibly read-only, and the burden is now a small fixed list rather than a repo-wide writer census — a large net improvement — but the list is the new thing to keep honest. **Condition CO-1 (revised, below).**

### Q2 — The readonly reader trades open-time cost for not holding a Chroma system across writes (X2). Accept as is with X2 as a follow-up, or must X2 land before merge?

**Accept as-is; X2 is a legitimate post-merge follow-up, with a performance caveat Ryan should see (CO-6). Confidence 80%.**

The design is right: refine and monitor now do their paid/scan work against `open_readonly_unit_store` (SQLite `mode=ro`, no Chroma system) with no lock held, then take C1 and open a short write session only to persist. Crucially — and this answers Astra's parallel Q2 — the write path does **not** trust the readonly snapshot: every refine job re-fetches the row fresh under the lock (`fresh = wstore.get_unit(...)`) and bases both the undo snapshot and the new metadata on that fresh read, not on the stale readonly `m`. So a write is never built from a readonly row. That is the correct boundary and it is a genuine improvement over `c7072fc`, where these jobs held one long write store.

X2 (open-time cost: plain `add` 0.7s → 4.8s, 151 → 617 MB on a 109k store) is a performance regression of the write-session open, not a correctness defect, and the branch is being merged hermetically (not deployed) with canary 2 gated separately. It does not need to land before merge.

**But there is a performance interaction that is new since `c7072fc` and that I want surfaced before canary 2 (CO-6):** several refine jobs now open a *fresh* `_refine_write_scope` — which is C1 + a full `production_chroma_write_session` open — **once per mutated row inside a loop** (`job_chroma_dedupe`, `job_backfill_domain`, `job_stale_source_flag`), and `repository_knowledge_sync._apply_retirements` likewise re-opens the lock+session per retire record. Combined with X2's open cost, a refine pass that tombstones/updates N rows pays the ~4.8s open N times and serialises every other writer behind N separate lock acquisitions. For the small batch sizes refine runs today this is tolerable; at scale it is a latency and lock-contention cliff. This is a design observation for canary 2, not a merge blocker: correctness is fine (each row is independently fresh-read and locked), but the per-row session churn is worth measuring and likely worth batching later.

### Q3 — Is `observe`'s prepare/commit split the right boundary for monitor?

**Yes. Confidence 88%.**

The split is clean and places the boundary where C1 wants it:

- `prepare_observation_ingest` validates and embeds (the paid `ollama_embed` call) and returns a `PreparedObservationIngest` dataclass **without opening a write session**.
- `commit_observation_ingest` persists a prepared unit under an already-open write store and does no paid work.
- `prepare_observation_file_rows` precomputes every embedding against a readonly `embed_store`; `ingest_observation_file` then commits them under the lock. `propose_decision.ingest_approved_file` uses exactly this prepare-readonly / commit-locked shape.

`run_monitor` adopts it correctly: it prepares each observation against a readonly store (no lock), buffers the prepared ingests, and at the end — only when `live_cfg is not None and not dry_run` — takes a single `index_write_flock` + one `production_chroma_write_session` and commits the whole batch. One lock window, paid work entirely outside it. This is the right boundary and it answers Astra Q3 (no provider call under the lock) for the monitor path.

Three sub-points, none blocking:
- **Dead line.** `run_monitor` ends with `if owned_store: pass` — the readonly store opened when `store is None` is never explicitly closed. Readonly SQLite handles are released on GC, so this is a cosmetic/leak-hygiene nit, not a correctness issue. **Nit N2.**
- **`by_ledger_id` staleness across the prepare→commit gap.** The upsert decision (changed vs unchanged, and the target chroma id) is computed in `prepare` against the readonly index, then committed later. Under total C1 coverage no other writer can move that row between prepare and commit within the same monitor run, so the decision stays valid; and `commit` re-reads nothing it needs to (it applies the decided op). This is sound *given* C1 totality — the same dependency as Q1. Worth noting but not a new risk.
- **Non-live callers.** When `live_cfg is None`, `_ingest_locked` commits immediately against `kwargs["store"]` with no lock. That is the test/non-production path; production always passes `live_cfg`. Consistent with the round-1 finding and not a regression.

### Q4 — Z2: should the Track A protocol text be corrected in this PR?

**Yes — recommend a one-line correction, but it does not block the merge. Confidence 85%. (Condition CO-7.)**

The text in `config/agent-protocol.md` and `config/kiro-steering-convmem.example.md` tells agents the running watcher "captures Codex, Kiro, Cursor, Copilot, and Crush transcripts automatically", so `index --file` on those paths is deferred unless `--now`. The branch already correctly amended the same sentence for Claude (`should_defer_index_file` returns False for `jsonl_claude_session`, and the text now says "Claude transcripts are not watch roots"). The gap round 13 flags is Crush: by the #393 census only 1 of 47 Crush databases sits under a watch root; for the other 46 the deferral never applies and each `index --file` re-pays the whole database. So the blanket "captures … Crush … automatically" is misleading in the direction that matters (it implies deferral is safe/automatic for Crush paths generally).

The behavior is safe either way — `should_defer_index_file` keys off `is_watchable`, so a non-watched Crush DB is simply not deferred and gets indexed; nothing silently drops. This is a documentation-accuracy fix, not a code fix. I recommend amending the sentence to say the watcher captures those transcripts **under the watch roots** (and that Crush databases outside a watch root are not deferred — see #393), landing in this PR since the surrounding sentence is already being edited on this branch. Minor enough that if Ryan prefers to fold it into the #393 follow-up, that is also acceptable; it does not gate the hermetic merge.

### Q5 — Is anything in the round-6 design (C1 window, C2 recovery, relaxed invariants) contradicted by correctives 6–11?

**No contradiction. Correctives 6–11 reinforce the round-6 design and resolve two of my round-1 conditions outright. Confidence 88%.**

- **C1 window.** Unchanged in intent and strengthened in enforcement. The window still covers store+export writes only; `_apply_prepared` and the new `commit_*`/`_refine_write_scope` paths consume already-prepared embeddings and make no paid call under the lock. The guarded store plus the new lock-ordering asserts make "no mutation outside the window" a runtime invariant rather than a convention. Consistent with round 6.
- **C2 recovery.** Isolation is still pinned to the attempt-start non-source digest captured under the lock; the guarded store means a mismatch now genuinely implies a non-cooperating writer (there is no longer a plausible "a production writer forgot the lock" explanation that would make the mismatch a false positive). This *tightens* the round-6 argument. The dedupe-file rollback was also reworked to filter by `transaction_id` rather than restore a captured preimage blob — a more precise scope that is consistent with "recover only this source's effects".
- **Relaxed invariant 1** (foreign state need not match transaction start between attempts): unchanged and still correct under C1.
- **Relaxed invariant 2** (source-owned export tamper dropped, not refused): unchanged in policy, but the diagnostic is now **durable** — `incremental_jsonl` appends a structured `rollback_export_tamper.jsonl` record (source, transaction id, dropped count) and `doctor._check_incremental_rollback_tamper` surfaces a 7-day WARN. This directly satisfies my round-1 CO-4; the drop event is no longer a watcher-droppable stderr line only.
- **Round-6 K1 edge** (an error before any prefix digest records an empty digest and re-spawns forever): improved. `_raise_incremental_retry_refusal` now backfills the prefix digest from the source when `last_evidence` has none, and the circuit breaker's wedged branch now holds (`return True`) when the live prefix digest is empty instead of letting an empty digest fall through. The catch-all `except Exception` in `maybe_route_incremental` routes through `classify_incremental_escape` into the same bounded-retry refusal, and re-raises `KeyboardInterrupt`/`SystemExit`. The retry gate runs before `coordinator.run()`, so a second identical failure refuses (exit 91) before paid work — the C3 contract, now covering unexpected escapes too.
- **G5** (clean-rollback quarantine release): the `rolled_back` asymmetry I flagged in round-1 CO-5 is unchanged — a clean `rolled_back` still holds until `--clear-quarantine`. That was explicitly a canary-2 item, not a merge blocker, and `clear_incremental_retry_states_for_source` is now wired so the clear path releases both the circuit breaker and the retry-state hold. CO-5 stands as a canary-2 recommendation.
- **G7** (`review-bundles/` in the R2b `_SKIP_SCAN_PREFIXES`): still a cross-arc guard edit; see CO-2 (carried).

---

## Disposition of round-1 conditions

| Round-1 | Status at `0ee6994` |
|---|---|
| CO-1 (publish writer list; confirm no unlocked production writer) | **Substantially resolved → revised.** The `_IndexWriteGuardedChromaStore` deny-by-default guard makes an unlocked production store mutation raise rather than write. The remaining obligation is narrow (keep the read allow-list honest) — see CO-1 (revised). |
| CO-2 (R2b owner ack for `review-bundles/` skip) | **Carried.** Still a cross-arc guard edit from the Codex branch; R2b-owner acknowledgement still wanted. |
| CO-3 (PR-draft accuracy: full-suite claim; Kiro = PASS-with-conditions) | **Carried to PR time.** Round 13 reports a completed like-for-like full-suite comparison (142 failure ids each, 0 branch-caused), which addresses the *substance* of the old CO-3; the PR body must still state Kiro review as PASS-with-conditions and cite real numbers. |
| CO-4 (make the export-drop event durable) | **Resolved.** `rollback_export_tamper.jsonl` + doctor `incremental_rollback_tamper` WARN. |
| CO-5 (G5: release clean rollback on prefix change) | **Carried as canary-2 recommendation.** Unchanged on the branch, by design. |

## Conditions (round 2)

| ID | Condition | Blocks | Why |
|---|---|---|---|
| CO-1 (revised) | Treat the `_IndexWriteGuardedChromaStore` read allow-list as a safety-critical list: confirm each listed method is genuinely read-only, and keep the list under review when store methods change. | Merge confidence (low effort) | The guard's correctness now rests on this list, not on a repo-wide writer census; a mutating method on the list would bypass C1. |
| CO-2 (carried) | R2b-arc owner acknowledgement that `review-bundles/` belongs in `_SKIP_SCAN_PREFIXES`; keep the disclosure in the PR body. | Arc-boundary cleanliness | Cross-arc guard change from the Codex branch (Q4, round 1). |
| CO-3 (carried) | PR body states Kiro review as **PASS with conditions** (not a clean pass) and cites the round-13 full-suite numbers that actually ran. | PR accuracy before merge | Avoids the round-1 draft overstatement. |
| CO-7 | Correct the Track A text so the watcher's auto-capture claim is scoped to transcripts **under the watch roots**, noting Crush databases outside a watch root are not deferred (#393). | Not merge; recommended in this PR | Z2: current blanket text overstates Crush coverage. |
| CO-6 (canary 2) | Measure per-row write-session churn in refine jobs and `_apply_retirements` (fresh C1 + `production_chroma_write_session` per mutated row) against X2's open cost; batch if the latency/lock-contention is material. | Not merge; canary 2 | New since `c7072fc`; correct but potentially slow at scale. |
| CO-5 (carried, canary 2) | Decide whether a clean `rolled_back` releases on prefix change like a wedged quarantine. | Not merge; canary 2 | Benign case still held harder than the wedged case. |

CO-1 (revised), CO-2, CO-3, and CO-7 are low-effort accuracy/disposition items on an otherwise correct and improved mechanism. CO-5 and CO-6 are canary-2 observations. None require a change to the C1/C2 logic.

## Non-blocking nits

- **N1.** The lock side spells path normalization as `Path(...).expanduser().resolve()` while the guard side uses `canonical_target(...).resolve()`. Equivalent today; routing both through `canonical_target` would prevent future drift.
- **N2.** `run_monitor` ends with `if owned_store: pass` — the readonly store it opened is never explicitly closed (released on GC). Cosmetic.

## Confidence summary

| Judgement | Confidence |
|---|---|
| Q1: store-bound lock + deny-by-default guard is the right design | 90% |
| Q2: accept readonly reader as-is; X2 is a post-merge follow-up | 80% |
| Q3: observe prepare/commit split is the right boundary for monitor | 88% |
| Q4: Z2 Track A text should be corrected (non-blocking) | 85% |
| Q5: no round-6 design contradiction; two round-1 conditions resolved | 88% |
| Overall: PASS with conditions | 87% |

## Verdict

**PASS with conditions.** Correctives 6–11 strengthen the C1/C2 design rather than alter it. The deny-by-default guarded store and store-bound lock identity turn my largest round-1 condition into a structural guarantee; the durable tamper record resolves CO-4; the observe prepare/commit split and the readonly-reader write boundary are correctly placed and re-read rows fresh under the lock. I found no defect in the C1/C2 mechanism at `0ee6994`. Merge the hermetic branch after the low-effort items CO-1(revised)/CO-2/CO-3/CO-7; CO-5 and CO-6 fold into canary 2.

---

## Forward announcement

I finished: Kiro round-2 design review of issue #286 Stage 2 correctives 6–11 at `0ee6994` — verdict PASS with conditions.
Next step:  Ryan dispositions CO-1(revised)/CO-2/CO-3/CO-7 (low-effort), then opens/merges the PR; CO-5/CO-6 fold into canary 2. Astra's parallel safety audit still gates the merge alongside this review.
Next lane:  Ryan (disposition + merge); Cursor only if CO-1's allow-list review surfaces a mutating method.
See my work: `docs/inter-model/KIRO-2026-10-14-issue-286-stage2-fixes-design-review-r2.md` on `docs/2026-10-14-issue-286-stage2-fixes-design-review-r2`.

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Codex (#286) | Arc making Kiro/Codex JSONL transcript indexing incremental and crash-replayable. |
| C1 | One store-wide exclusive index write lock covering all summary/unit/export writes. |
| C2 | Source-scoped recovery: replay/rollback proves only this source's state, not foreign state at transaction start. |
| C3 | Bounded retries — a second identical failure on an unchanged prefix refuses (exit 91). |
| `_IndexWriteGuardedChromaStore` | Deny-by-default wrapper: any non-read store method asserts the index write lock (bound to the store's `chroma_dir`) before mutating. |
| store-bound lock | `index_write_flock` records the store's resolved `chroma_dir`; the guard compares it to the store being mutated, so a lock for store A can't satisfy a write to store B. |
| readonly reader | `open_readonly_unit_store` (SQLite `mode=ro`, no Chroma system) used for scan/paid work outside the lock; writes re-open a fresh write store under C1. |
| prepare/commit split | `observe.prepare_observation_ingest` (validate+embed, no session) → `commit_observation_ingest` (persist under an open write store, no paid work). |
| relaxed invariant 2 | Source-owned export tamper is dropped-with-diagnostic, not refused; now recorded durably in `rollback_export_tamper.jsonl` + a doctor WARN. |
| G5 / G7 / K1 | Round-6 items: G5 = clean-rollback quarantine release; G7 = R2b skip-list edit; K1 = empty-prefix-digest re-spawn edge. |
| X2 | Follow-up: readonly/write-store open-time cost (plain `add` 0.7s → 4.8s on a 109k store). |
| Z2 | Round-13 finding: Track A protocol text overstates the watcher's Crush auto-capture coverage (#393). |
| #393 | Separate burn path: re-indexing a changed Crush database re-pays every chunk. |
| CO-1..CO-7 | Conditions this review attaches to its PASS (see Conditions table). |

**TL;DR:** PASS with conditions at `0ee6994`. Correctives 6–11 strengthen the C1/C2 design: the deny-by-default `_IndexWriteGuardedChromaStore` plus store-bound lock identity turn my round-1 CO-1 (writer-census) into a structural fail-closed guarantee, and the durable `rollback_export_tamper.jsonl` + doctor WARN resolve CO-4. The observe prepare/commit split and the readonly-reader write path are correctly placed and re-read rows fresh under the lock. Remaining conditions are low-effort accuracy/disposition items (CO-1 revised: keep the read allow-list honest; CO-2 R2b ack; CO-3 PR-body accuracy; CO-7 Z2 text) plus two canary-2 observations (CO-5 clean-rollback release; CO-6 per-row write-session churn). No defect found in the C1/C2 mechanism.
