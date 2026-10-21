# [Arc Codex #286] Independent safety audit of the rollback fix

## Verdict

**FAIL — merge-blocking finding 1.**

The fix substantially improves rollback safety: before-images are captured under
the processed sidecar lock, rollback restores use compare-and-swap-style checks,
and refusal paths preserve recovery authority. However, a successful roll-forward
still publishes `processed.json` after releasing the source and index-write locks.
That publication has no ownership check and can delete a concurrent same-source
update before deleting the recovery journal. The fix is therefore not safe to
merge as the final protection for issue 286.

## Audit scope and provenance

- **Target:** `fix/2026-10-20-rollback-fresh-before-image` at
  `ec7b8a55bb6a21c61089d69c025f1116e5b17239`.
- **Base:** `origin/main` at `a5405ada2b3f2ed64a6cae2d9d02a1b1906648cd`,
  confirmed as an ancestor of the target.
- **Auditor:** OpenAI Codex, independent read-only audit lane.
- **Audit branch:** `docs/2026-10-21-issue-286-rollback-fix-audit`.
- **Audit worktree:** `/home/lauer/.cache/astra-rollback-audit`.
- **Constraints honored:** no edits to the fix branch, no merge or PR, no
  provider calls, and no live ConvMem state writes.

The target diff contains the production changes in
`src/convmem/incremental_jsonl.py` and `src/convmem/ingest.py`, together with
the issue-286 regression and stage-2 tests. The prior Kiro tip re-review marked
the target PASS in `docs/2026-10-21-issue-286-rollback-tip-rereview.md`; this
audit independently rechecked that conclusion against the publication path.

## Finding 1 — roll-forward publication has no final ownership fence

**Severity: High; merge-blocking.**

### Evidence

`IncrementalJsonlCoordinator._commit_generation` holds `source_flock` and the
re-entrant index-write lock while it revalidates the live prefix, captures the
processed before-image, applies stores, and writes the checkpoint
(`incremental_jsonl.py:2706-2853`). Its `finally` releases those locks at
`incremental_jsonl.py:2855`. The method then calls `_publish_processed` at
`incremental_jsonl.py:2856-2859` and `_cleanup` at
`incremental_jsonl.py:2860-2861`, both outside those locks.

`_publish_processed` calls `ingest.commit_processed_index_entry`
(`incremental_jsonl.py:2594-2618`; `ingest.py:395-429`). That helper serializes
the file with the processed sidecar lock, but it writes its key and purges all
other same-path keys. It does not compare the current same-source rows with the
roll-forward transaction's before-image or owned prefix.

The competing writer is reachable in production-facing paths. For an unselected
source, `maybe_route_incremental` returns to the legacy ingest route
(`incremental_jsonl.py:3603-3620`); `convmem index --file` reaches that route via
`convmem.py:323-329`. The generic ingest final publishes at
`ingest.py:1517-1523`, `1561-1567`, and `1619-1625` also occur outside the
earlier source-lock scope. This includes the manual/index-file and Track A
publication surfaces identified in the audit request.

### Reachable loss scenario

1. Recovery writer A completes its checkpoint and releases `source_flock` and
   the index-write lock.
2. Same-source writer B completes a legitimate update and publishes B's
   processed entry.
3. A publishes its older roll-forward entry. The normal stale-row purge treats
   B's entry as stale because no ownership or generation comparison is made.
4. A deletes the transaction and rollback journal.

The processed sidecar lock only serializes the two final mutations; it does not
make A's generation authoritative over B's later publication. The reverse
ordering can likewise leave the checkpoint and processed projection out of sync,
depending on which final publication wins. This is the same class of lost-update
that the rollback-side CAS protects, but the protection is not applied to the
successful roll-forward path.

### Required correction

Add one publication fence shared by recovery and every legacy/manual/Track A
writer. The safest shape is to hold `source_flock` through the final processed
publication and journal cleanup, and to make all same-source processed
publications participate in that fence. If that cannot be made universal, the
roll-forward publication needs a final ownership CAS against its captured
before-image/transaction prefix; on conflict it must refuse, retain rollback
authority, and avoid cleanup. Add a deterministic regression that inserts a
same-source writer between recovery's checkpoint and final processed publication
and asserts that the later update is retained or recovery refuses with authority
intact.

## Question-by-question results

### 2. Refusal paths, authority, and lock release — PASS

The new rollback refusal path validates structure and processed semantics before
restoring. `_preflight_rollback_restore` checks foreign keys, same-source
unowned keys, Chroma extras, and export extras before mutation
(`incremental_jsonl.py:1898-1964`). `_restore_processed` repeats ownership checks
inside `mutate_processed` (`incremental_jsonl.py:2092-2128`). A late processed
conflict is mapped to `recovery_partial` while preserving the transaction and
rollback authority (`incremental_jsonl.py:2247-2307`). `_roll_forward` returns a
pure refusal for that state (`incremental_jsonl.py:3076-3079`), so it does not
silently clean up a failed recovery.

The successful `rolled_back` result intentionally consumes the authority after a
verified restore; that is a completed recovery, not an accidental refusal-side
deletion. Lock release is protected by the surrounding `finally` blocks. I found
no new path that consumes a rollback journal or transaction while returning the
`recovery_partial` refusal.

### 3. Lock order — PASS

The new replay path takes `source_flock` before the index-write lock
(`incremental_jsonl.py:2951-2953`). `purge_locks.assert_lock_ordering_ok`
rejects the inverse order (`purge_locks.py:71-95`), and the source lock remains
non-reentrant while the index-write lock is depth-counted. The focused tests
cover both the source-before-C1 order and the absence of nested source-lock
acquisition.

### 4. Paid-call safety — PASS for the new rollback/refusal/replay path

Rollback validation, preflight, before-image replay, and `recovery_partial`
refusal do not call summarize, distill, or embed. This audit made no provider or
network calls. The existing no-journal recovery branch for a transaction with no
prepared keys can still rebuild a frontier and reach provider functions
(`incremental_jsonl.py:3105-3116`; provider-bearing ingest code at
`ingest.py:835-1104`); that behavior is outside the new rollback replay path and
is not changed by this finding.

### 5. Live pending transactions and the removed R-975 bypass — PASS with scope

The read-only live-state inspection found exactly two pending transactions and no
`rollback.json` files:

- one `APPLYING` transaction with one prepared key and a rollback-authority hash;
- one `transform_failed` transaction with zero prepared keys and no rollback
  authority.

The new processed-semantics validation runs only when a rollback journal exists,
so these two states are not newly intercepted by the fix. Removing the old empty
preimage bypass intentionally fails closed for an inconsistent rollback journal
that claims a prior checkpoint but cannot provide its processed before-image. It
may require repair or a fresh run for such an old journal, but it does not create
a new lock wedge in the two observed no-journal states.

### 6. Watcher, doctor, Track A, and canary surfaces — PASS for exercised checks;
full-suite verification remains outstanding

The targeted regression, state, canary, and stage-2 suites passed:

```
115 passed in 3:09
```

The focused canary baseline passed separately:

```
2 passed in 0.66s
```

The target is descended from `origin/main`, and `git diff --check
a5405ad..ec7b8a5` passed. The checked CLI and route definitions remain present,
and the exercised tests include the incremental routing and rollback probes. I
did not run the complete repository suite or a live watcher; this report does
not claim those broader checks.

## Verification record

Command run in the isolated target worktree:

```
pytest -q tests/test_issue_286_rollback_fresh_before_image.py \
  tests/test_incremental_jsonl_state.py \
  tests/test_incremental_jsonl_canary_baseline.py \
  tests/test_issue_286_stage2_corrective7_q8.py \
  tests/test_issue_286_stage2_wedge_probes.py
```

Result: `115 passed in 189.61s (0:03:09)`.

Additional checks:

- `pytest -q tests/test_incremental_jsonl_canary_baseline.py`: `2 passed`.
- `git merge-base --is-ancestor a5405ad ec7b8a5`: passed.
- `git diff --check a5405ad..ec7b8a5`: passed.
- No code, live state, provider, or external service was modified by this audit.

## Handoff

The target should not advance to merge while Finding 1 remains open. After the
publication fence/CAS correction lands, rerun this audit against the exact new
tip, including the deterministic late-writer race test and the focused suite.

I finished: [Arc Codex #286] independent safety audit of rollback fix tip `ec7b8a55bb6a21c61089d69c025f1116e5b17239`
Next step: resolve Finding 1 (forward processed-publication ownership fence), then rerun the independent audit on the new exact tip
Next lane: Cursor for the bounded code correction; Kiro and Ryan for re-review and the merge gate
See my work: `docs/inter-model/CODEX-2026-10-21-issue-286-rollback-fix-audit.md`

<!-- src: ../../incremental_jsonl.py, ../../ingest.py, ../../purge_locks.py — target blob ec7b8a55 audited read-only -->
