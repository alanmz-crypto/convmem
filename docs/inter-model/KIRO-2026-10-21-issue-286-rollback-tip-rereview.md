# [Arc Codex #286] Kiro — tip re-review of the rollback fix (ec7b8a5)

**Author: Kiro (design review / sign-off lane). Date: 2026-10-21 UTC. Arc: Codex.**
Read-only review from the prod worktree. No production code, tests, or config were
written or run. Verdict verified against the **blob at `ec7b8a5`**, not the working tree.

- **Branch reviewed:** `fix/2026-10-20-rollback-fresh-before-image`, tip
  `ec7b8a55bb6a21c61089d69c025f1116e5b17239` (pushed).
- **Lineage verified independently:** `origin/main` (`a5405ada…`) *is* an ancestor of
  `ec7b8a5` (`git merge-base --is-ancestor` → yes). The handoff's lineage claim holds.
- **Prior review:** `docs/inter-model/KIRO-2026-10-20-issue-286-rollback-fix-review.md`
  (commit `5e3378d`), verdict PASS-WITH-CHANGES, required changes C-1…C-8, plus the
  C-5 refuse-and-preserve ruling.
- **Code verified against** the `ec7b8a5` blob of `incremental_jsonl.py` and
  `ingest.py`/`purge_locks.py` lock helpers, and the `ec7b8a5` blob of
  `tests/test_issue_286_rollback_fresh_before_image.py`.

> **Review-hygiene note (important for anyone re-checking this).** The prod worktree
> HEAD is `77a5e89` (`main` tip), which is *newer* than `ec7b8a5` and does **not**
> contain this fix. Reading the files via a plain editor/LSP read shows the unfixed
> `main` state. I verified every claim below against `git show ec7b8a5:<file>`. If you
> re-review, check out the tip or read the blob — do not trust a working-tree read.

---

## Verdict: PASS

The C-5 correction is implemented correctly and the full C-1…C-6 machinery I required in
the prior review is present at the tip, not just the narrow C-5 slice the handoff
summarized. The fix fails closed, preserves recovery authority on refusal, and does not
engage on current production state. The four residuals the handoff raised are all
correctly characterized as accept / nit / cosmetic — none blocks landing. I am issuing a
clean PASS rather than PASS-WITH-CHANGES because the decidable gaps from the prior review
are closed in code and pinned by tests; the remaining items are defense-in-depth and
provenance-cosmetic, appropriate for a follow-up, not a condition of merge.

---

## What I verified independently at `ec7b8a5`

| Claim | Verified in the `ec7b8a5` blob | Status |
|---|---|---|
| `origin/main` is an ancestor of the tip | `git merge-base --is-ancestor a5405ad ec7b8a5` → yes | CONFIRMED |
| New shared predicate `_same_source_unowned_processed_keys` | present; same-source keys in `processed.json` absent from the rollback preimage and from transaction ownership | CONFIRMED |
| `_preflight_rollback_restore` uses the predicate | yes — calls it after `validate_rollback` + `validate_rollback_processed_semantics`, refuses `recovery_unproven` on unowned | CONFIRMED |
| `_roll_forward_refusal` runs `validate_rollback_processed_semantics` first (fail-closed, raises on invalid), then returns `"recovery_partial"` on unowned | yes — the validate call precedes the predicate check at the top of the method | CONFIRMED |
| `_roll_forward_refusal` has a single live caller (`_roll_forward`, pending-transaction recovery) | `grep` shows one call site at the roll-forward dispatch | CONFIRMED |
| `_roll_forward` maps `recovery_partial` → `_refusal("recovery_partial", mode="rollback")` with **no replay restore, no commit** | yes — explicit `if roll_refusal == "recovery_partial": return self._refusal(...)` before the replay branch | CONFIRMED |
| `_replay_rollback_authority` remaps a `recovery_partial` raised *during* restore to a refusal, not `rolled_back` | yes — try/except on `_restore_replay_before_images` | CONFIRMED |
| `_refusal` preserves authority (no `_cleanup`, no journal/snapshot deletion, no retry-state clear) | `_refusal` is a pure result constructor; the only `_cleanup` is after a *successful* authority restore | CONFIRMED |
| Capture is now fresh + locked (`_capture_processed_preimage_locked` under `_processed_lock`), refuses stale-vs-checkpoint | yes — this closes the stale-`processed_override` root cause | CONFIRMED |
| Restore write (`_restore_processed`) is a locked CAS via `mutate_processed`, refuses unowned/foreign/excluded with `recovery_processed_conflict` → remapped to `recovery_partial` | CONFIRMED |
| R-975 shape (empty preimage + prior checkpoint) refuses with `rollback_processed_authority_invalid` | `validate_rollback_processed_semantics`: embedded checkpoint present + empty preimage → raise | CONFIRMED |
| Lock order source → C1: `_restore_replay_before_images` wraps `source_flock` → preflight → `index_write_flock` | CONFIRMED — matches commit/purge order |
| No live transaction is affected today | no `rollback.json` under convmem state dirs; the 2 pending live txns have no rollback journal, so the new path is inert | CONFIRMED (filesystem check) |

The implementation delivered the capture-side correction (C-1), the positive-predicate
empty-preimage policy (C-2), the ownership-from-transaction definition (C-3, via
`prefix_sha256`), the no-new-schema refusal path (C-4 — ownership proven from existing
transaction evidence, no new persisted field), the final-CAS refuse-and-preserve contract
(C-5), and the executable lock-order / non-nesting tests (C-6). C-7/C-8 are packet-scope
items outside this code PR and unchanged by it.

---

## Residuals — my ruling on each

1. **Lockless preimage read at preflight (`_same_source_unowned_processed_keys` calls
   `load_processed` without the processed lock).** **ACCEPT.** This runs inside
   `source_flock`, so a *same-source* writer is already excluded. A cross-source lockless
   writer landing in the preflight→commit window is superseded by the final locked CAS in
   `_restore_processed`/`mutate_processed`, which re-checks under `_processed_lock` and
   refuses (`recovery_processed_conflict` → `recovery_partial`). This is exactly the
   window my prior C-5 ruling placed at preflight and accepted. No change required.

2. **`_same_source_unowned_processed_keys` returns `set()` (fail-open) when
   `processed_preimage` is not a dict (the handoff's "L1884").** **NIT — follow-up, not a
   blocker.** Unreachable at both call sites today: in `_roll_forward_refusal` and in
   `_preflight_rollback_restore` the predicate is called *after*
   `validate_rollback_processed_semantics`, which raises `recovery_unproven`
   ("processed_preimage invalid") on a non-dict preimage. So the fail-open default is
   dead-code-defended. I agree with Claude it would be cleaner to `raise` than to return
   `set()`, so a later lockless caller can't silently fail open — but it changes no
   behavior at the tip.

3. **`test_roll_forward_commits_with_transaction_owned_processed_keys_only` proves owned
   keys don't trip the check only indirectly.** **NIT.** The owned-key branch *is*
   exercised — it is why `first.run()` returns `rolled_back` rather than
   `recovery_partial` — but the assertion is indirect, and the `committed` second run is a
   fresh run, not a roll-forward. Behavior is covered; assertion directness is weak.
   A follow-up could assert the owned slice is restored head-on.

4. **Cosmetic: canary baseline comment chain ends at `854d5882…` but the pinned value is
   `f2b3bfac…`; stray blank lines.** **COSMETIC.** The canary test pins the
   `BASELINE_HASHES` dict value (`f2b3bfac…`), which is correct and up to date; only the
   human-readable provenance comment's last line is out of sync. Worth a one-line
   follow-up to keep the provenance trail honest; it changes no test outcome.

None of the four is a merge blocker.

---

## What I did NOT verify (limits of this review)

- I did not run tests, build, linter, or any live-state write (read-only grant). I rely on
  Claude's reported evidence at `ec7b8a5` (slice 521 passed / 0 skipped, pylint 10.00 on
  touched files, manifest guard PASS, byte-stable artifacts, zero provider calls, the
  tampered-rollback bypass closed) and verified the *mechanism* that makes those results
  meaningful. I confirmed the test names and key assertions exist in the `ec7b8a5` blob.
- I did not re-run the census or any projection/Chroma/restic check; I relied on the
  handoff's production-impact statement and confirmed only that no `rollback.json` exists
  in convmem state dirs, so the new path is inert on the 2 pending live transactions.
- I verified diff coverage structurally (both predicate call sites are validation-guarded)
  rather than from a coverage report.

---

## Forward announcement

I finished: Kiro tip re-review of the Arc Codex #286 rollback fix at `ec7b8a5`.
Next step:  Ryan's merge decision (squash OK); optional follow-up PR for the three nits.
Next lane:  Ryan (merge). Follow-up nits → Cursor if Ryan wants them.
See my work: `docs/inter-model/KIRO-2026-10-21-issue-286-rollback-tip-rereview.md` on
             branch `docs/2026-10-20-2026-10-21-issue-286-rollback-tip-rereview`.

## TL;DR

- **Verdict: PASS** on `fix/2026-10-20-rollback-fresh-before-image` tip `ec7b8a5`.
  Lineage confirmed (`origin/main` is an ancestor). The C-5 refuse-and-preserve contract
  is implemented correctly, and the full C-1…C-6 machinery from my prior review is present.
- **Fail-closed and inert on prod:** `_roll_forward_refusal` validates first then returns
  `recovery_partial` with no restore/commit; `_refusal` preserves the journal/snapshot
  (zero provider calls on refusal); no `rollback.json` exists for the 2 pending live txns,
  so the new path does not engage today.
- **Four residuals are accept / nit / nit / cosmetic — none blocks merge.** The fail-open
  predicate default is dead-code-defended by `validate_rollback_processed_semantics` at
  both call sites; the lockless preflight read is superseded by the locked final CAS.
- **Review-hygiene flag:** the prod worktree HEAD (`77a5e89`) is newer than the tip and
  lacks the fix — verify against the `ec7b8a5` blob, not the working tree.

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Codex #286 | Incremental Kiro/Codex JSONL ingestion arc; see `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| C-1…C-8 | The eight required changes from my prior review (`KIRO-2026-10-20-…-rollback-fix-review.md`) |
| C-5 | The final-CAS partial-recovery contract: on a late conflict, refuse and preserve authority — never fake `rolled_back`, never re-transform |
| `recovery_partial` | Refusal outcome meaning "could not fully restore; authority preserved for a zero-call replay" |
| rollback journal | The before-image (rows/export/processed/checkpoint) a rollback persists to restore on failure |
| processed preimage | The pre-mutation slice of `processed.json` for this source captured in the journal |
| `prefix_sha256` | The transaction's owned processed key — the basis for "transaction-owned" (C-3) |
| C1 / `index_write_flock` | Store-wide index write lock; reentrant/depth-counted |
| `source_flock` | Per-source advisory lock; non-reentrant; acquired before C1 |
| fail-open | A default that permits an action on malformed input (here: the `set()` return — dead-code-defended) |
| canary baseline | `test_incremental_jsonl_canary_baseline.py` pins a SHA of `incremental_jsonl.py` to catch unreviewed drift |

<!-- src: ./KIRO-2026-10-20-issue-286-rollback-fix-review.md — prior review, C-1..C-8 and the C-5 ruling -->
<!-- src: ../../incremental_jsonl.py, ../../ingest.py, ../../purge_locks.py — code verified read-only at blob ec7b8a5 -->
<!-- src: ../../tests/test_issue_286_rollback_fresh_before_image.py — test names/assertions verified at blob ec7b8a5 -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex current state and next lane -->
