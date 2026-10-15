# Design review (round 3): issue #286 Stage 2 wedge fixes, at `7d46e6e`

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Reviewer:** Kiro (design review lane — review only; no code, tests, scripts, or config)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `7d46e6e` (base `origin/main`)
**Weighting:** `git diff 0ee6994 7d46e6e` (correctives 12–15 since my round-2 review at `0ee6994`), focused on the Q3 recheck the handoff asked for.
**Prior review:** `KIRO-2026-10-14-issue-286-stage2-fixes-design-review-r2.md` at `b07f044` (reviewed tip `0ee6994`) — PASS with conditions CO-1(revised), CO-2, CO-3, CO-7 (merge-level) and CO-5, CO-6 (canary 2).
**Verify read:** Claude round 18 at the top of `CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md` (origin branch `docs/2026-10-12-issue-286-stage2-fixes-handoff`, `7911704`) — PASS at `7d46e6e`.

## Verdict: PASS with conditions.

The Q3 mechanism at this tip is correct and is, if anything, stronger than at `0ee6994`. Rows are revalidated under C1 with **targeted reads** — `get_unit(existing_chroma_id)` for updates and skips, and a targeted `active_units_for_ledger_id(lid)` lookup for inserts — and then written **without re-validation**, trusting the drift check that just passed under the lock. The full-store scan that round 17 (N12) flagged in `unit_document_text` is gone, replaced by a bounded SQL lookup; that was a `convmem doctor` latency defect, never a C1/C2 correctness defect, and it is now closed.

Two of my round-2 merge-level conditions are resolved in-branch at this tip: **CO-1(revised)** (the new insert-side lookup is now on the guarded store's read allow-list, with a per-method read justification in the docstring) and **CO-7** (the Track A text is now scoped to watch roots and names #393). A new runtime guard, `reject_provider_under_write_scope()`, converts "no paid work under the lock" from a convention into a fail-closed assertion at the provider boundary — a strengthening beyond what round 2 required. **CO-2** and **CO-3** remain as PR-time disposition items; **CO-5** and **CO-6** remain canary-2 observations, with CO-6 partially pre-empted by refine batching at this tip.

---

## What I read

- Claude round 18 (top of `CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md` at `7911704`): verdict PASS at `7d46e6e`, N12 closed, suite clean but for the Z1 ext4 inode-reuse flake, leak census 0, follow-ups X5/X2–X4/#393/Z1 (none merge-blocking), and the explicit instruction that Kiro recheck Q3 ("rows are re-read fresh under the lock, now by targeted reads").
- My round-2 review `KIRO-2026-10-14-issue-286-stage2-fixes-design-review-r2.md` (`b07f044`), conditions CO-1(revised), CO-2, CO-3, CO-5, CO-6, CO-7.
- `git diff 0ee6994 7d46e6e` for the production code that bears on Q3 and the C1/C2 mechanism: `observe.py`, `propose_decision.py`, `monitor.py`, `refine.py`, `chroma_readonly.py`, `chroma_store.py`, `chroma_write_store.py`, `purge_locks.py`, `llm.py`, `distill.py`, `incremental_jsonl.py`, `incremental_retry_state.py`, `eval_corpus/r2b_v2/coverage/inventory.py`, and the two Track A config surfaces.
- The Q3 path end-to-end in `observe.py`: `prepare_observation_ingest` → `PreparedObservationIngest` → `_prepared_observation_drifted` → `commit_observation_ingest` → `_write_prepared_observation_ingest`.
- The guarded store's `_READS` allow-list and `__getattr__` dispatch in `chroma_write_store.py`.

Confidence that I have the material the recheck depends on: **90%**. I did not re-run the suite (review-only lane); I rely on Claude round 18's probe evidence (`s1`: 0 full scans; `perf16_commit_scans.py`: `scans=0`; `r1`: 1 pass over the units collection) for the runtime behaviour and I verified the code paths that produce it.

---

## Q3 recheck (the question the handoff asked me to re-answer)

**Is `observe`'s prepare/commit split the right boundary for monitor, now that rows are revalidated with targeted reads under the lock and then written without re-validation? Yes. Confidence 90% — up from 88% at `0ee6994`.**

The boundary is where C1 wants it, and the revalidation is now provably targeted rather than a scan. The flow at `7d46e6e`:

1. **Prepare (outside the lock, readonly store).** `prepare_observation_ingest` validates the record, builds `by_ledger_id` from the readonly index, embeds the document (the paid `ollama_embed` call), and returns a `PreparedObservationIngest` carrying `existing_chroma_id`, one of `skipped_unchanged` / `upsert_update` / insert, and a `target_digest`. No write session, no lock.

2. **Revalidate under C1 (targeted reads).** `commit_observation_ingest`, running against the open write store with the lock held, calls `_prepared_observation_drifted(prepared, store=store)`:
   - **Update or skip** (`skipped_unchanged or upsert_update`): one `store.get_unit(prepared.existing_chroma_id)` — a single targeted read by chroma id. It raises drift if the row is now missing, superseded, re-pointed to a different `ledger_id`, or if `_observation_target_digest(row) != prepared.target_digest`. No scan.
   - **Insert** (`target_digest == "missing"`): `_active_units_for_ledger_id(store, lid)` → `store.active_units_for_ledger_id(lid)`, which on the production store is a `col.get(where={"ledger_id": lid}, include=["metadatas"])` — a targeted indexed lookup, not an iteration. It raises drift if any active row for that ledger id now exists (a concurrent insert).
   - A drift → `ObservationIngestDriftError`; nothing is written.

3. **Write without re-validation.** On a clean drift check, `_write_prepared_observation_ingest` applies the already-decided operation: `update_unit(chroma_id, …)` for an update, `add_unit(unit["id"], …)` for an insert, or marks `_skipped` for an unchanged row. It does **not** re-run validation or re-read the row — it trusts the drift check that just passed under the same lock. This is the correct boundary: the decision is made once under the lock, against a fresh targeted read, and then executed.

Why this is sound. The revalidation closes the prepare→commit gap exactly where it matters: the prepare-time decision was computed against a readonly snapshot that could in principle be stale by commit time, so the commit re-reads the specific row(s) the decision depends on, under the lock, before trusting them. It re-reads only what the operation touches (one id for update/skip; one ledger-id lookup for insert) rather than rescanning the collection — so it is O(1)/O(indexed-lookup), not O(store). Writing without a second validation is correct because, under total C1 coverage, no other writer can move the row between the drift check and the write within the same lock window. The same dependency as Q1 (C1 totality) still holds, and the guarded store makes that totality a runtime invariant rather than a convention.

`monitor.run_monitor` consumes this correctly, unchanged in intent from round 2: it prepares each observation against a readonly store with no lock, buffers the prepared ingests, and only when `live_cfg is not None and not dry_run` takes one `index_write_flock` + one `production_chroma_write_session` and commits the batch. One lock window; paid work entirely outside it. `propose_decision.ingest_approved_file` uses the same prepare-readonly / commit-locked shape for governed decisions.

**Verification that the targeted reads are legal under the deny-by-default guard.** Both revalidation reads — `get_unit` and `active_units_for_ledger_id` — are on the `_IndexWriteGuardedChromaStore._READS` allow-list, so `__getattr__` returns the inner bound method directly and the read does not trip the lock assertion. The subsequent `update_unit` / `add_unit` are **not** on the allow-list, so they route through `_guarded`, which calls `require_index_write_lock_held(chroma_dir=self._inner.chroma_dir)` before delegating. So the design is internally consistent: revalidate with allow-listed targeted reads, then mutate through the lock-asserting path. (During commit the lock is held regardless, so even the reads would pass the assertion; the allow-list simply means they do not need to.)

**Runtime corroboration (from Claude round 18, not re-run by me).** Probe `s1` reports 0 full scans on the commit path; `perf16_commit_scans.py` on the 109k store reports `scans=0`, 3 rows in 0.0 s and 20 rows in 0.3 s (against 40.7 s for 3 rows before the targeted-read rework). This is consistent with the code: the commit path performs targeted reads, not scans.

---

## The N12 fix (the only Q3-adjacent code change behind round 18's PASS)

Round 17 was a FAIL on N12: `chroma_readonly.unit_document_text` iterated every row of the units collection to find one document, and `doctor._check_empty_ledger_documents` runs that repair as a dry run on every `convmem doctor`, so the live corpus took ~13 minutes. At `7d46e6e`, `unit_document_text` is a bounded SQL lookup — a join across `embeddings`/`segments`/`collections`/`embedding_metadata`, filtered by collection name, `scope='METADATA'`, `embedding_id = ?`, `key='chroma:document'`, `LIMIT 1`. Round 18 times the dry-run repair at 7.5 s (20 decisions) and 35.3 s (213, the live count), down from ~13 minutes.

This is a readonly helper on the scan/prepare side; it does not touch C1, C2, the lock, or the write path. It was always a doctor-latency defect, not a correctness defect in the mechanism I review. It is closed. Round 18's follow-up **X5** notes the query still plans as a `SCAN em` and is ~3.5× main on a large corpus (35 s vs ~10 s at 213 decisions), with a suggested id-first rewrite; that is a non-blocking performance follow-up that may ride on this PR or follow with X2–X4, Ryan's call. It does not bear on the C1/C2 design.

---

## Disposition of round-2 conditions at `7d46e6e`

| Round-2 | Status at `7d46e6e` |
|---|---|
| **CO-1 (revised)** — keep the guarded-store read allow-list honest; confirm each listed method is read-only. | **Resolved in-branch.** The new insert-side lookup `active_units_for_ledger_id` is now on the `_READS` allow-list, and the docstring enumerates every allow-listed method with a one-line read justification. The two methods the Q3 revalidation relies on (`get_unit`, `active_units_for_ledger_id`) are both genuinely read-only (`get`/`where`-query reads; superseded-filtered). The standing obligation (re-check the list when store methods change) carries forward as hygiene, but the specific gap round 2 named is closed. |
| **CO-2 (carried)** — R2b-arc owner ack that `review-bundles/` (and now `artifacts/`) belong in `_SKIP_SCAN_PREFIXES`; keep the disclosure in the PR body. | **Carried.** Still a cross-arc guard edit from the Codex branch; `artifacts/` was added at this tip alongside `review-bundles/`. R2b-owner acknowledgement still wanted; keep it in the PR body. |
| **CO-3 (carried)** — PR body states Kiro review as PASS-with-conditions and cites the real full-suite numbers. | **Carried to PR time.** Round 18 reports tip 94 failed / 2988 passed / 66 skipped / 52 errors, **1 tip-only (Z1, the ext4 inode flake, not this branch)**, leak census 0. The PR body must state Kiro as PASS-with-conditions and cite these numbers (and name Z1 as pre-existing). |
| **CO-7** — scope the Track A auto-capture text to watch roots; note Crush DBs outside a watch root are not deferred (#393). | **Resolved in-branch.** Both `config/agent-protocol.md` and `config/kiro-steering-convmem.example.md` now say "captures … **under configured watch roots** automatically" and add "Crush databases outside a watch root are not deferred (#393)." Exactly the CO-7 correction. |
| **CO-6 (canary 2)** — measure per-row write-session churn in refine jobs and `_apply_retirements`; batch if material. | **Partially pre-empted; still carried to canary 2.** `_apply_approved_dedupe_impl` now loads the queue and resolves indices inside one `index_write_flock` + one write store, and `job_semantic_dedupe` buffers `pending_records` and writes them under a single lock window instead of per-pair. That removes two of the per-row churn sites. The measurement for the remaining per-row session opens (`job_backfill_domain`, `job_stale_source_flag`, `_apply_retirements`) and against X2's open cost still belongs in canary 2. |
| **CO-5 (carried, canary 2)** — decide whether a clean `rolled_back` releases on prefix change like a wedged quarantine. | **Carried, unchanged.** Still a canary-2 disposition item, by design. |

## New since `0ee6994` (strengthening, not required by round 2)

- **`reject_provider_under_write_scope()`** (`purge_locks.py`) raises if `index_write_lock_depth() > 0` or a production Chroma write session is open. It is called as the first statement of both paid provider entrypoints — `llm.ollama_embed` and `llm.summarize` — and `distill`. This converts the "no paid work under C1" boundary (Q2/Q3, and Astra's parallel Q3) from a convention enforced by call-site discipline into a fail-closed runtime assertion at the provider boundary itself, catching any caller on any path. This is strictly stronger than anything round 2 asked for and I note it as a positive.

---

## Conditions (round 3)

| ID | Condition | Blocks | Why |
|---|---|---|---|
| CO-2 (carried) | R2b-arc owner acknowledgement that `review-bundles/` and `artifacts/` belong in `_SKIP_SCAN_PREFIXES`; keep the disclosure in the PR body. | PR accuracy / arc-boundary cleanliness | Cross-arc guard change from the Codex branch. |
| CO-3 (carried) | PR body states Kiro review as **PASS with conditions**, cites round 18's full-suite numbers (94/2988/66/52, 1 tip-only), and names Z1 as a pre-existing ext4 flake. | PR accuracy before merge | Avoids a clean-pass overstatement; keeps the single tip-only failure disclosed. |
| CO-5 (carried, canary 2) | Decide whether a clean `rolled_back` releases on prefix change like a wedged quarantine. | Not merge; canary 2 | Benign case still held harder than the wedged case. |
| CO-6 (canary 2, reduced) | Measure the remaining per-row write-session churn (`job_backfill_domain`, `job_stale_source_flag`, `_apply_retirements`) against X2's open cost; batch if material. The dedupe paths are already batched at this tip. | Not merge; canary 2 | Correct but potentially slow at scale; two of the original churn sites are now batched. |

CO-1(revised) and CO-7 are **resolved in-branch** at this tip and drop off the merge list. CO-2 and CO-3 are PR-body disposition items. CO-5 and CO-6 fold into canary 2. None require a change to the C1/C2/Q3 mechanism.

## Non-blocking follow-ups I agree with (from round 18)

- **X5** (doctor dry-run repair still ~3.5× main on a large corpus; `SCAN em`): legitimate performance follow-up, may ride on this PR or follow separately. Not a mechanism concern.
- **Cosmetic:** coalesced duplicate ledger lines are not reported in the result's `skipped` count (carried from round 17's N10 note). Harmless.
- **Z1** (`test_recovery_refuses_replaced_artifact_inode`, ext4 inode-reuse flake): pre-existing, not this branch; Ryan's call whether its fix rides on this PR.

---

## Confidence summary

| Judgement | Confidence |
|---|---|
| Q3: prepare/commit split with targeted-read revalidation under C1, then write without re-validation, is the right boundary | 90% |
| N12 fix is a readonly-helper latency fix, no C1/C2 impact; closed | 92% |
| CO-1(revised) resolved in-branch (allow-list honest; new lookup listed and read-only) | 90% |
| CO-7 resolved in-branch (Track A text scoped to watch roots; #393 named) | 92% |
| `reject_provider_under_write_scope` strengthens the no-paid-work-under-lock boundary | 88% |
| No C1/C2 design contradiction introduced by correctives 12–15 | 90% |
| Overall: PASS with conditions | 89% |

## Verdict

**PASS with conditions.** The Q3 recheck confirms the design: under C1 the commit path revalidates with targeted reads — `get_unit` by chroma id for updates/skips, a `where`-query `active_units_for_ledger_id` for inserts — and then writes without re-validation, trusting the drift check that just passed under the lock. The reads are on the guarded store's read allow-list; the writes route through the lock-asserting guard. The N12 full-scan is replaced by a bounded SQL lookup, closing the `convmem doctor` latency regression without touching the mechanism. CO-1(revised) and CO-7 are resolved in-branch and drop off the merge list; `reject_provider_under_write_scope` adds a fail-closed provider-boundary assertion beyond what round 2 required. Merge the hermetic branch after the PR-body items **CO-2** (R2b ack + skip-prefix disclosure) and **CO-3** (state PASS-with-conditions, cite round 18's numbers, name Z1). **CO-5** and **CO-6** stay for canary 2 (CO-6 reduced — dedupe paths already batched). I found no defect in the C1/C2/Q3 mechanism at `7d46e6e`. Astra's parallel safety audit still gates the merge alongside this review.

---

## Forward announcement

I finished: Kiro round-3 design review of issue #286 Stage 2 at `7d46e6e` — Q3 recheck — verdict PASS with conditions.
Next step:  Astra (audit lane) re-audits the exact tip `7d46e6e`; then the PR draft carries CO-2 and CO-3 in its body; Ryan merges the hermetic branch. CO-5 and CO-6 fold into canary 2.
Next lane:  Astra (parallel audit), then Ryan (PR draft + merge). Cursor only if a later store-method change touches the guarded read allow-list.
See my work: `docs/inter-model/KIRO-2026-10-15-issue-286-stage2-fixes-design-review-r3.md` on branch `docs/2026-10-15-issue-286-stage2-fixes-design-review-r3`.

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Codex (#286) | Arc making Kiro/Codex JSONL transcript indexing incremental and crash-replayable. |
| C1 | One store-wide exclusive index write lock covering all summary/unit/export writes. |
| C2 | Source-scoped recovery: replay/rollback proves only this source's state, not foreign state at transaction start. |
| Q3 | The review question: is `observe`'s prepare/commit split the right boundary for monitor — now that rows are revalidated with targeted reads under the lock and written without re-validation? |
| prepare/commit split | `prepare_observation_ingest` (validate+embed off-lock, readonly store) → `commit_observation_ingest` (revalidate under C1 with targeted reads, then persist). |
| targeted-read revalidation | Under the lock, re-read only the row(s) the decision depends on: `get_unit(chroma_id)` for update/skip; `active_units_for_ledger_id(lid)` (a `where` query) for insert — not a collection scan. |
| `_prepared_observation_drifted` | The under-lock drift check that performs the targeted reads and raises `ObservationIngestDriftError` on a mismatch. |
| `_IndexWriteGuardedChromaStore` | Deny-by-default store wrapper: non-read methods assert the index write lock (bound to the store's `chroma_dir`); reads are an explicit allow-list (`_READS`). |
| N12 | Round-17 FAIL: `unit_document_text` scanned the whole units collection; `convmem doctor` ran it as a dry run (~13 min on the live corpus). Closed at this tip by a bounded SQL lookup. |
| `reject_provider_under_write_scope` | New fail-closed guard: `ollama_embed`/`summarize`/`distill` raise if a paid call is attempted while C1 or a Chroma write session is held. |
| X5 | Round-18 follow-up: doctor dry-run repair still ~3.5× main on a large corpus (`SCAN em`); id-first rewrite suggested. Non-blocking. |
| Z1 | Pre-existing ext4 inode-reuse test flake (`test_recovery_refuses_replaced_artifact_inode`); not this branch. The one tip-only full-suite failure. |
| CO-1..CO-7 | Conditions attached across rounds 1–3; at this tip CO-1(revised) and CO-7 are resolved, CO-2/CO-3 are PR-body items, CO-5/CO-6 are canary 2. |

**TL;DR:** PASS with conditions at `7d46e6e`. Q3 recheck confirms the design — under C1 the commit path revalidates with targeted reads (`get_unit` by chroma id for update/skip; a `where`-query `active_units_for_ledger_id` for insert), both on the guarded store's read allow-list, then writes through the lock-asserting guard without re-validation. The N12 full-scan is replaced by a bounded SQL lookup (doctor dry-run ~13 min → 35 s), with no C1/C2 impact. CO-1(revised) and CO-7 are resolved in-branch; a new `reject_provider_under_write_scope` fail-closed guard strengthens the no-paid-work-under-lock boundary. Remaining: CO-2 (R2b ack) and CO-3 (PR-body accuracy) at PR time; CO-5 and CO-6 (reduced — dedupe batched) at canary 2. No defect in the C1/C2/Q3 mechanism.

<!-- ref: ./KIRO-2026-10-14-issue-286-stage2-fixes-design-review-r2.md — round-2 review this supersedes; carries conditions CO-1..CO-7 -->
<!-- src: ./CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md — Claude round 18 verify (PASS at 7d46e6e) read for this review -->
