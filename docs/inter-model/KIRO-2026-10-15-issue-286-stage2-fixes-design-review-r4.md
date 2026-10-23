# Design review (round 4): issue #286 Stage 2 wedge fixes, at `74c8ee7`

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Reviewer:** Kiro (design review lane — review only; no code, tests, scripts, or config)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at exactly `74c8ee7` (base `origin/main`).
**Weighting:** `git diff 7d46e6e 74c8ee7` (correctives 16 since my round-3 review at `7d46e6e`), focused on the one thing the handoff asked me to confirm: the **lock-order change** — the coordinator's per-source lock now wraps admission, with C1 placement unchanged.
**Prior review:** `KIRO-2026-10-15-issue-286-stage2-fixes-design-review-r3.md` at `607102f` (reviewed tip `7d46e6e`) — PASS with conditions CO-2, CO-3 (PR body) and CO-5, CO-6 (canary 2); CO-1(revised) and CO-7 resolved in-branch.
**Verify read:** Claude rounds 20 and 21 at the top of `CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md` (origin branch `docs/2026-10-12-issue-286-stage2-fixes-handoff`, `1a8fd7e`) — round 20 PASS on safety with one mechanical inventory condition at `928700b`; round 21 PASS at `74c8ee7` (inventory current, no tip-only failure, diff coverage clean).

## Verdict: PASS with conditions (unchanged conditions from round 3).

The lock-order change is correct. The live route now takes the coordinator's per-source advisory lock **before** the retry gate and holds it through `run()` and the failure accounting, exactly as corrective 16 specified. Inside `run()` the admission gate sits **after** the unchanged-prefix short-circuit and **before** paid transform (`_build_frontier`) or roll-forward. C1 (`index_write_flock`) placement is unchanged — still taken inside `_commit_generation`, nested within `source_flock`, after all paid work. There is **no deadlock risk with C1**: a single global acquisition order (source → C1 → export) is enforced fail-closed by `assert_lock_ordering_ok`, and provider calls occur under the per-source lock but **never** under C1 (now a fail-closed assertion via `reject_provider_under_write_scope`). My round-3 conditions were not mechanism conditions and are untouched by this corrective: **CO-2** and **CO-3** remain PR-body items; **CO-5** and **CO-6** remain canary-2 observations. I found no new defect in the C1/C2/Q3 mechanism at `74c8ee7`.

---

## What I read (at `74c8ee7`, verified against the working tree)

- Claude rounds 20 and 21 (top of `CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md` at `1a8fd7e`): round 20 traces the R3-F1 lock change end-to-end and PASSes on safety with a mechanical "regenerate the R2b inventory" condition at `928700b`; round 21 confirms the inventory is current at `74c8ee7`, no tip-only full-suite failure against main `458b9f6` (Z1 did not flake this run), static undefined-name check clean on all 13 changed files, and diff coverage finds no hidden broken branch.
- My round-3 review `KIRO-2026-10-15-issue-286-stage2-fixes-design-review-r3.md` (`607102f`), conditions CO-2, CO-3 (PR body) and CO-5, CO-6 (canary 2).
- `git diff 7d46e6e 74c8ee7` (8 files): `incremental_jsonl.py` (the lock-order change), `observe.py` (R3-F2 + R3-O1), `monitor.py` (R3-F3), `eval_corpus/r2b_v2/coverage/inventory.py` and two inventory JSONs, `tests/test_zz_codex_audit_r3.py` and a canary-baseline test.
- The live route in `incremental_jsonl.maybe_route_incremental` (lines 2764–2874) and `IncrementalJsonlCoordinator.run` (2513–2750), `_commit_generation` (2143–2256), `_build_frontier` (976–1033), `_acquire_source_lock`/`_release_source_lock` (2473–2488).
- The lock primitives in `purge_locks.py`: `assert_lock_ordering_ok` (71–98), `reject_provider_under_write_scope` (98–106), `source_flock` (167–178), `index_write_flock` (197–219), and the TLS depth helpers.
- `SourceAdvisoryLock` in `incremental_jsonl_isolation.py` (375–406) and the coordinator's `paths["lock"]` definition.
- The provider entrypoints `llm.ollama_embed`, `llm.summarize`, `distill` — all three call `reject_provider_under_write_scope()` as their first statement at this tip.

Confidence that I have the material the confirmation depends on: **92%**. I did not re-run the suite (review-only lane); I rely on Claude rounds 20–21 for runtime behaviour (the concurrency probe, diff coverage, the clean static check) and I verified the code paths and the lock topology directly.

---

## The lock-order change (the question the handoff asked me to confirm)

### 1. The per-source lock now wraps admission, through `run()` and failure accounting.

`maybe_route_incremental` constructs the coordinator, then — before anything that can pay — acquires the coordinator's per-source lock and holds it across the whole run:

```python
holds_source_lock = (
    callable(getattr(type(coordinator), "_acquire_source_lock", None))
    and callable(getattr(type(coordinator), "_release_source_lock", None))
)
if holds_source_lock:
    coordinator._acquire_source_lock()
try:
    coordinator._run_under_external_source_lock = True
    try:
        result = coordinator.run()
    finally:
        coordinator._run_under_external_source_lock = False
    ...  # retry-refusal accounting, retry-state clear, result.ingest_tuple()
finally:
    ...
    if holds_source_lock:
        coordinator._release_source_lock()
```

The lock is released only in the **outer** `finally`, which runs after `run()` and after every `_raise_incremental_retry_refusal(...)` / `clear_incremental_retry_state(...)` path. So the retry gate, the reservation, the transform, and the failure accounting all run inside the one source-lock window — exactly corrective 16's "serialize admission per source." This closes R3-F1 (concurrent entrants bypassing the attempt cap): a second caller on the same source now blocks on the lock, and when it enters `run()` it re-reads admission — a processed prefix is a no-op; a reached cap is a refusal.

`run()` cooperates via the `_run_under_external_source_lock` flag: its own `skip_lock = bool(getattr(self, "_run_under_external_source_lock", False))` suppresses the inner re-acquire, so the lock is taken exactly once (no self-contention on `state_dir/lock.flock`). When the route is driven without the external wrapper (a test double lacking the helpers), `run()` still takes the lock itself — the behaviour degrades safely, and `holds_source_lock` is the only skip, which Claude round 20 and I both read as the test-double branch (low; a test-side fix would be cleaner, not merge-blocking).

### 2. The gate sits after the unchanged-prefix short-circuit, before paid transform or roll-forward.

`_enforce_live_retry_admission_if_needed()` is called at two points in `run()`, both correctly placed:

- **Roll-forward path:** right before `return self._roll_forward(existing_tx)` for an existing transaction. A resumed transaction is admission-gated before it continues.
- **Fresh path:** immediately after the unchanged-prefix short-circuit. That short-circuit returns an `"unchanged"` result ("repair followers with zero transform calls") and `_cleanup`s the snapshot **before** the gate — correct, because a no-op prefix must not consume an attempt. Only once the prefix is confirmed to have real work does the gate run, and it runs **before** `_build_frontier` (the paid transform) and `_commit_generation` (the write/roll-forward). Every earlier `return self._refusal(...)` is a refusal with no paid work.

So no paid provider call and no roll-forward happens before the gate, and the unchanged case is never charged an attempt. This matches the handoff's description precisely.

### 3. C1 placement is unchanged.

C1 (`index_write_flock`) is still acquired inside `_commit_generation`, nested within `source_flock(self.cfg, self.path_key)`, after all paid work:

```python
with source_flock(self.cfg, self.path_key):
    with index_write_flock(self.cfg):   # C1
        ... _apply_prepared(prepared) ...   # writes already-prepared artifacts
        ... checkpoint / rollback / reconcile ...
```

The paid transform (`_build_frontier` → `build_chunk_artifact` → embed/summarize) runs earlier in `run()`, before `_commit_generation` is ever called, so no provider call occurs inside the C1 window. This is the same C1 boundary I reviewed in rounds 2 and 3; corrective 16 did not move it. The prepare/commit split and the targeted-read revalidation under C1 (Q3) are also untouched by this diff.

### 4. No deadlock with C1; provider calls under the source lock but never under C1.

This is the crux, and it is sound. Three distinct OS lock files are involved, each per-scope:

| Lock | File | Scope |
|---|---|---|
| Coordinator source lock (`SourceAdvisoryLock`) | `state_dir/<source_id>/lock.flock` | per-source |
| `source_flock` (purge_locks) | `locks/source/<sha256(path_key)>.lock` | per-source |
| C1 (`index_write_flock`) | `locks/index_write.lock` | store-wide (one file) |

The live route's acquisition sequence is strictly nested and consistently ordered:

1. Coordinator `SourceAdvisoryLock` (outermost, held across `run()`).
2. Paid transform in `_build_frontier` — **no C1 held**.
3. `source_flock` (TLS `source_depth`++), inside `_commit_generation`.
4. C1 `index_write_flock` (TLS `index_write_depth`++), nested inside `source_flock`.
5. (optionally) `export_flock` nested inside C1.

A single global order is **enforced fail-closed** by `assert_lock_ordering_ok`: acquiring `source` while holding `index_write` or `export` raises; acquiring `index_write` while holding `export` or an open Chroma writer session raises; acquiring `export` without `index_write` raises. In words: **source → index_write (C1) → export**, never the reverse. Because every acquirer in the system obeys this one order, no circular wait can form, so **no deadlock is possible**. A violation would surface as an immediate `RuntimeError`, not a hang. At step 4 the assertion sees `source_depth=1, export_depth=0, chroma_session=0` and passes — source-before-C1 is the sanctioned order.

The two per-source locks (`SourceAdvisoryLock` on `lock.flock` and `source_flock` on `source/<hash>.lock`) are **different inodes**, so the coordinator holding the first while `_commit_generation` takes the second is not a self-deadlock; the inner `source_flock` is released before the outer `SourceAdvisoryLock`, preserving strict nesting.

Provider calls occur under the per-source lock (they run inside the `SourceAdvisoryLock` window, in `_build_frontier`) but **never under C1**: `_build_frontier` executes before `_commit_generation`, and `reject_provider_under_write_scope()` — called as the first statement of `ollama_embed`, `summarize`, and `distill` — raises if `index_write_lock_depth() > 0` or a production Chroma session is open. So "no paid work under C1" is a fail-closed runtime invariant at the provider boundary, not merely a call-site convention. This is exactly the property the handoff asked me to confirm, and it holds at `74c8ee7`.

---

## The other two blockers closed in this diff (R3-F2, R3-F3) — no mechanism impact

Both are correctness fixes outside the C1/C2/Q3 mechanism; I confirm they do not move the prepare/commit boundary or C1:

- **R3-F3 (`monitor.py:626`):** `precomputed_embedding=current.embedding` → `current.embedding or None`. A re-prepared row that drifted into an update no longer reuses an empty `[]` embedding (which raised `IndexError` in Chroma `update`); it passes `None` so the embedding is computed, or refuses cleanly. Inside the monitor's existing single-lock commit window; boundary unchanged.
- **R3-F2 (`observe.py:848`):** the repair retry branch builds a fresh `_DocumentAccurateReadonlyStore(chroma_dir)` instead of the unimported `open_readonly_unit_store` — closes the `NameError`. A readonly reader on the repair path; no write-path or C1 impact.
- **R3-O1 (`observe.py:365–395`):** the ledger-cache invalidation is now wrapped in `finally`, so a post-write export failure still clears the stale cache. This hardens the write path but does not relocate C1 or add paid work under the lock; the `export_flock_path` nesting (index_write → export) is the sanctioned order.

These match corrective 16 and Claude round 20's reproduction-then-closure. None of them bears on the design question I was asked to re-answer.

---

## Disposition of round-3 conditions at `74c8ee7`

| Round-3 | Status at `74c8ee7` |
|---|---|
| **CO-2 (carried)** — R2b-arc owner ack that `review-bundles/` and `artifacts/` belong in `_SKIP_SCAN_PREFIXES`; keep the disclosure in the PR body. | **Carried, unchanged.** PR-body item; not touched by corrective 16. |
| **CO-3 (carried)** — PR body states Kiro review as PASS-with-conditions and cites the real full-suite numbers, naming Z1 as a pre-existing flake. | **Carried, updated numbers.** Cite Claude round 21: full suite under coverage 93 failed / 2998 passed / 66 skipped / 52 errors, **no tip-only failure** against main `458b9f6` (Z1 did not flake this run; it remains the known ext4 inode flake). |
| **CO-5 (carried, canary 2)** — decide whether a clean `rolled_back` releases on prefix change like a wedged quarantine. | **Carried, unchanged.** Canary-2 disposition item. |
| **CO-6 (canary 2, reduced)** — measure remaining per-row write-session churn; dedupe paths already batched. | **Carried, unchanged.** Canary-2 disposition item. |

None of these is a mechanism condition and none is affected by the lock-order change. CO-1(revised) and CO-7 remain resolved in-branch from round 3.

---

## Confidence summary

| Judgement | Confidence |
|---|---|
| Per-source lock wraps admission through `run()` and failure accounting (R3-F1 closed) | 93% |
| Gate placed after the unchanged-prefix short-circuit, before paid transform / roll-forward | 93% |
| C1 placement unchanged (still inside `_commit_generation`, nested in `source_flock`, after paid work) | 93% |
| No deadlock: single enforced order source → C1 → export; provider calls under source lock, never under C1 | 92% |
| R3-F2 / R3-F3 / R3-O1 closures have no C1/C2/Q3 mechanism impact | 92% |
| Round-3 conditions unchanged and unaffected by corrective 16 | 94% |
| Overall: PASS with conditions | 92% |

---

## Verdict

**PASS with conditions.** The lock-order change is correct and is a strict strengthening of the mechanism I reviewed at round 3. The coordinator's per-source advisory lock is acquired in `maybe_route_incremental` before the retry gate and held across `run()` and the failure accounting, serializing admission per source (R3-F1 closed). Inside `run()` the admission gate sits after the unchanged-prefix short-circuit and before paid transform or roll-forward, so a no-op prefix is never charged and no paid work precedes the gate. C1 placement is unchanged — inside `_commit_generation`, nested within `source_flock`, after all paid work. There is no deadlock risk with C1: a single global acquisition order (source → C1 → export) is enforced fail-closed by `assert_lock_ordering_ok`, and provider calls run under the per-source lock but never under C1, now guaranteed by the fail-closed `reject_provider_under_write_scope()` at every paid entrypoint. My round-3 conditions still stand: CO-2 and CO-3 at PR time (CO-3 citing round 21's suite numbers and naming Z1 as pre-existing), CO-5 and CO-6 at canary 2. I found no new defect in the C1/C2/Q3 mechanism at `74c8ee7`. Astra's parallel safety audit of the exact tip still gates the merge alongside this review.

---

## Forward announcement

I finished: Kiro round-4 design review of issue #286 Stage 2 at `74c8ee7` — lock-order confirmation — verdict PASS with conditions.
Next step:  Astra (audit lane) re-audits the exact tip `74c8ee7`; then the PR draft carries CO-2 and CO-3 (round-21 numbers) in its body; Ryan merges the hermetic branch. CO-5 and CO-6 fold into canary 2.
Next lane:  Astra (parallel audit), then Ryan (PR draft + merge).
See my work: `docs/inter-model/KIRO-2026-10-15-issue-286-stage2-fixes-design-review-r4.md` on branch `docs/2026-10-15-issue-286-stage2-fixes-design-review-r4`.

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Codex (#286) | Arc making Kiro/Codex JSONL transcript indexing incremental and crash-replayable. |
| C1 | One store-wide exclusive index write lock (`locks/index_write.lock`) covering all summary/unit/export writes. |
| C2 | Source-scoped recovery: replay/rollback proves only this source's state. |
| per-source lock | The coordinator's `SourceAdvisoryLock` on `state_dir/<source_id>/lock.flock` (and the related `source_flock` on `locks/source/<hash>.lock`); serializes work on one source. |
| R3-F1 | Round-3 audit blocker: concurrent entrants on one source bypassed the attempt cap because the gate ran before the per-source lock. Closed here by taking the lock before admission. |
| admission gate | `_enforce_live_retry_admission_if_needed()` — the retry/reservation check; now runs inside the per-source lock, after the unchanged short-circuit, before paid work. |
| unchanged-prefix short-circuit | `run()` returns `"unchanged"` with zero transform calls when the selected prefix is identical; it precedes the gate so a no-op is not charged an attempt. |
| `_build_frontier` | The paid transform (embed/summarize per chunk); runs under the per-source lock but before C1. |
| `_commit_generation` | The write phase; takes `source_flock` then nests C1 (`index_write_flock`), then writes already-prepared artifacts. No paid work inside. |
| `assert_lock_ordering_ok` | Fail-closed runtime guard enforcing the one global order source → C1 → export; prevents any reverse acquisition that could deadlock. |
| `reject_provider_under_write_scope` | Fail-closed guard at `ollama_embed`/`summarize`/`distill`: raises if a paid call is attempted while C1 or a Chroma write session is held. |
| R3-F2 / R3-F3 / R3-O1 | Audit findings closed in this diff (repair reader `NameError`; monitor empty-embedding `IndexError`; cache-clear on export failure). No mechanism impact. |
| Z1 | Pre-existing ext4 inode-reuse test flake (`test_recovery_refuses_replaced_artifact_inode`); not this branch. |
| CO-2..CO-6 | Round-3 conditions: CO-2/CO-3 PR-body items; CO-5/CO-6 canary-2 observations. Unchanged by corrective 16. |

**TL;DR:** PASS with conditions at `74c8ee7`. The lock-order change is correct — the coordinator's per-source lock now wraps admission (gate, reservation, transform, failure accounting) through `run()`, closing R3-F1; the gate sits after the unchanged-prefix short-circuit and before paid transform/roll-forward; C1 placement is unchanged. No deadlock with C1: a single order source → C1 → export is enforced fail-closed by `assert_lock_ordering_ok`, and provider calls run under the per-source lock but never under C1 (fail-closed via `reject_provider_under_write_scope`). R3-F2/F3/O1 are correctness fixes with no mechanism impact. My round-3 conditions still stand (CO-2/CO-3 PR body — CO-3 cites round-21 suite numbers and names Z1; CO-5/CO-6 canary 2). No new defect in the C1/C2/Q3 mechanism.

<!-- ref: ./KIRO-2026-10-15-issue-286-stage2-fixes-design-review-r3.md — round-3 review this supersedes; carries conditions CO-2/CO-3/CO-5/CO-6 -->
<!-- src: ./CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md — Claude rounds 20-21 verify (PASS at 74c8ee7) read for this review -->
