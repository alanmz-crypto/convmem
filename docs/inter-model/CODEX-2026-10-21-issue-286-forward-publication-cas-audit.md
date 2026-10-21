# [Arc Codex #286] Exact-tip independent re-audit of forward publication

## Verdict

**PASS — the prior merge-blocking Finding 1 is closed for the audited scope.**

The rollback fix now keeps the incremental roll-forward source fence through
the final `processed.json` publication and journal cleanup. Legacy, manual
`index --file`, and Track A final publications use the same source fence. A
same-source writer therefore cannot publish between the recovery checkpoint and
the recovery processed publication and then be purged as stale.

## Audit scope and provenance

- **Target:** `fix/2026-10-21-issue-286-forward-publication-cas` at
  `e6ce3c46aaa250d69129f519eba97bc2be874265` (short label `e6ce3c4`).
- **Previous audited tip:** `ec7b8a55bb6a21c61089d69c025f1116e5b17239`.
- **Auditor:** OpenAI Codex, independent read-only audit lane.
- **Audit worktree:** `/home/lauer/.cache/astra-rollback-audit-r2`.
- **Report branch:** `docs/2026-10-20-issue-286-forward-publication-cas-audit`.
- **Constraints honored:** no edits to the fix worktree during this audit, no
  merge or PR, no provider calls, and no live ConvMem state writes.

The implementation commit changes only the incremental coordinator, processed
publication callers, canary identity pins, and the issue-286 regression test.

## Finding 1 closure — forward publication ownership fence

**Status: PASS.**

### Corrected behavior

1. `IncrementalJsonlCoordinator._commit_generation` acquires
   `source_flock` before the apply/checkpoint sequence and now keeps it through
   `_publish_processed` and `_cleanup`
   (`incremental_jsonl.py:2707-2866`). The index-write lock is still released
   before the processed sidecar mutation, so the existing provider/write-lock
   rules are preserved.
2. `ingest.commit_processed_index_entry_fenced` wraps the existing atomic
   processed sidecar mutation in the same `source_flock`
   (`ingest.py:432-459`). The lower-level helper remains available for callers
   that already hold the source fence, including the incremental coordinator.
3. All three generic `_index_one_file` final publication branches now use the
   fenced helper: inter-model (`ingest.py:1547-1554`), repository knowledge
   (`ingest.py:1592-1599`), and the normal chunk path
   (`ingest.py:1651-1658`). This closes the legacy/manual/Track A route identified
   in the prior audit.

The resulting interleaving is safe: if recovery writer A holds the source fence,
writer B's final publication waits; A publishes and cleans up, then B publishes
afterward as the later writer. B's processed row is not deleted by A's stale-row
purge.

### Regression evidence

`test_roll_forward_source_fence_covers_final_processed_publication`
(`tests/test_issue_286_rollback_fresh_before_image.py:844-908`) starts a
same-source writer at the recovery publication boundary. The test proves that
the writer cannot acquire the fence during recovery publication, then proves its
later processed entry survives after recovery completes.

The existing lock-order and non-nested-source-lock tests also remain green.

## Other audit questions

### Refusal and rollback authority — PASS

The correction does not alter the fail-closed rollback validation, processed
before-image capture, compare-and-swap-style restore checks, or
`recovery_partial` authority-preservation behavior from the previous audited
tip. Rollback/refusal paths remain provider-free and continue to release locks
through their existing `finally` scopes.

### Lock order — PASS

The new scope is an extension of the existing source-before-index-write scope;
it does not acquire `source_flock` while holding the index-write lock and does
not add nested source-lock acquisition. The focused lock-order tests passed.

### Paid-call safety — PASS for the correction

The new fence and processed sidecar helper contain no summarize, distill, embed,
network, or provider dispatch. The audit made no provider or network calls. The
pre-existing no-journal recovery branch that may rebuild a frontier remains
unchanged and is outside this correction.

### Production inertness — PASS

The feature remains default-off and no production configuration, watcher, live
transaction, Chroma store, or processed ledger was written by the implementation
or audit. The two pending transaction states observed before the correction are
not changed by this publication-fence code.

## Verification record

The independent exact-tip audit worktree ran:

```
pytest -q -p no:cacheprovider \
  tests/test_issue_286_rollback_fresh_before_image.py \
  tests/test_incremental_jsonl_state.py \
  tests/test_incremental_jsonl_canary_baseline.py \
  tests/test_issue_286_stage2_corrective7_q8.py \
  tests/test_issue_286_stage2_wedge_probes.py
```

Result: **116 passed in 191.95s (0:03:11)**.

Additional checks:

- `git diff --check ec7b8a55..e6ce3c4`: passed.
- All processed-publication call sites were re-enumerated; the three legacy
  branches use the fenced helper and the incremental branch is inside the
  existing source fence.
- Targeted Pylint reported **9.98/10** with the repository's pre-existing
  warnings and no new warning from this correction. The normal Pylint cache path
  is read-only in the audit environment; `--persistent=no` reproduced the same
  baseline warnings.
- No provider, network, live ConvMem, merge, or PR operation was performed.

The full repository suite and a live watcher run remain outside this scoped
re-audit; they are not required to clear the specific Finding 1 gate.

## Handoff

The exact-tip issue-286 safety audit is PASS. The next lane can perform the
required Kiro/Ryan review and PR disposition; this audit lane does not merge or
activate production behavior.

I finished: [Arc Codex #286] exact-tip independent re-audit of `e6ce3c4`
Next step: Kiro/Ryan review and PR disposition for the pushed fix branch
Next lane: Kiro for implementation review; Ryan for PR creation and merge gate
See my work: `docs/inter-model/CODEX-2026-10-21-issue-286-forward-publication-cas-audit.md`

<!-- src: ../../incremental_jsonl.py, ../../ingest.py, ../../purge_locks.py — target blob e6ce3c4 audited read-only -->
