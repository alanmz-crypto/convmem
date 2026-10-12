# Implementation Handoff: stop the #308 inter-model rejection retry loop

**Arc: Codex (#286), Stage 2 prerequisite.** (Issue #308.)
**Date:** 2026-10-12
**Author:** Claude (Opus 5.5), from Codex's read-only design analysis
(2026-10-12)
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-10-12. Ryan granted "#308 fix: turn Codex's
design into a Cursor handoff" as a Stage 2 prerequisite of the Codex burn
work.

## Resume state

| Field | Value |
|-------|--------|
| **State** | `IN_PROGRESS`: corrective 4 (Copilot FAIL at `bbf09d1`, clear path) |
| **Branch** | `fix/2026-10-12-issue-308-inter-model-rejection` (create from `origin/main`) |
| **Tip SHA** | `bbf09d1` (merge base `138e3aa`) |
| **Push status** | handoff pushed on `docs/2026-10-12-issue-308-inter-model-rejection-handoff` |
| **PR** | not opened |
| **Ryan GATE** | none for hermetic implementation; Ryan alone merges |
| **Track A ingest** | your Cursor transcript, at handoff |

## What to build

**Why this exists:** some `docs/inter-model/*.md` files fail the inter-model
provenance-supersession guard. Each one is then re-attempted on every
watcher cycle, all day, with no content change. One doc had 282 spawn
attempts on 2026-09-18, and inter-model docs caused 3,315 spawns from
Sep 26 to Oct 5. There are no paid calls, but every attempt spawns a child
and repeats local embedding work before the guard rejects again.

This has to be fixed before the 24 h watcher canary (Stage 2), the step
that brings back automatic capture without the Codex burn.

**The defect** (confirmed by Codex and Claude at `05aa2c8`):

- The provenance guard raises `InterModelIndexError`
  (`inter_model_index.py:95–121`, message at `:119`).
- `_index_inter_model_file` (`ingest.py:716–756`) catches every exception
  and returns a failure.
- At `ingest.py:~1415–1433`, that failure becomes `"skipped"` before
  `commit_processed_index_entry` (`:1447`). `processed.json` therefore never
  records the file, and the next event retries the same bytes.
- A correction from Codex: on `main`, the watcher doesn't consume the
  reconciler's queued work. Retries come from filesystem events through
  `flush_path` (`watch.py:~438–508`). The reconciler still reports these
  docs as `new_eligible_source` (`source_reconciler.py:146–155`).

**The fix:** record a terminal rejection for that exact content. Skip that
`(canonical path, full-file SHA-256)` pair in the watcher and the reconciler
until the bytes change.

## Integration points

1. `inter_model_index.py:~118`: give the provenance-supersession guard a
   distinct typed outcome, for example a subclass
   `InterModelSupersessionRequired(InterModelIndexError)`. Every other
   failure keeps its current type.
2. `ingest.py:716–756` (`_index_inter_model_file`) and `:~1415–1433`: carry
   that typed outcome through. Record the rejection with the full
   `file_hash` the caller already computes (`ingest.py:~1331–1346`). Return
   `"skipped"` exactly as today.
3. `ingest.py:509` (`watch_skip_reason`, called at `watch.py:476`): skip with
   a distinct reason, such as `inter_model_rejected`, when the current path
   and hash match a recorded rejection. Do this before any child is spawned.
4. `source_reconciler.py:121` (`discover_legacy_source_drift`): don't report
   a path whose current hash matches its recorded rejection. Report it again
   as soon as the hash differs.

## Specification

- **Storage:** a dedicated sidecar next to `processed.json` (for example
  `inter_model_rejections.json`). **Not** in `processed.json`, and **not**
  in the watcher circuit breaker or refusal quarantine.
  - That quarantine is path-wide and terminal by design (Codex D3), whereas
    this record must release when the content changes.
  - Each record holds the canonical path, the full-file SHA-256, the
    rejection kind (`provenance_supersession_required`), a UTC timestamp,
    and the guard's section id.
  - Writes are atomic (temp file plus rename, under the existing writer
    lock if one applies).
- **Writer:** only the typed provenance-supersession outcome writes a
  record. Embedding failures, I/O errors, parse failures and any other
  exception must stay retryable, and must write nothing.
- **Readers:** `watch_skip_reason` and `discover_legacy_source_drift`. A
  match requires the same canonical path and the same current hash.
  - The same bytes at a different path are not suppressed.
  - A changed hash is eligible at once.
- **Failure mode:** a corrupt or unreadable sidecar **fails open**. It
  suppresses nothing, so retries resume, and it prints one visible
  diagnostic. It never crashes the watcher or the reconciler.
- **Clearing:** a record clears itself when the content changes. Also add a
  small explicit clear path for the case where an operator resolves
  supersession without changing the bytes, such as
  `convmem exclude --undo`-style tooling, or a documented one-line
  procedure. Keep it minimal.
- **Constants:** none new. Use the existing hash function and path
  canonicalization.

## What NOT to build

- No change to the provenance guard's policy, to supersession semantics, or
  to the Chroma and export projection.
- No change to watcher scheduling or debounce, to the native-crash and
  timeout thresholds, or to the Codex refusal quarantine
  (`watch_circuit_breaker.py`). Don't count this skip as a crash.
- No `processed.json` schema change, and no new config keys.
- No live index runs, watcher start, provider calls, or edits to live data.
  Tests are hermetic only.

## Test expectations

All hermetic. Each of the first four must fail on `main` `05aa2c8`:

1. A provenance-guard rejection records the exact path and hash, returns
   `skipped`, and leaves both `processed.json` and the existing Chroma
   projection unchanged.
2. `watch_skip_reason` skips the rejected path and hash before a child
   spawns. After the file changes, it allows the new hash.
3. Reconciliation no longer reports the rejected path and hash, and reports
   it again after the content changes.
4. Repeated events on unchanged bytes produce zero further index attempts.
5. An embedding error, or any other non-guard exception, records nothing
   and stays retryable.
6. The same bytes at a different path aren't suppressed, and one path's
   rejection doesn't suppress another path.
7. A corrupt sidecar fails open with one diagnostic. Concurrent writes and
   reads don't lose records.

## Acceptance criteria

- [ ] Integration points 1–4 are implemented, and each test above is mapped
      to its name in the handoff-back.
- [ ] From a clean, disk-backed checkout with a fresh CI config:
  - the full-suite summary line (only the known #320 golden-eval failure
    allowed);
  - the exact Pylint regression-gate command, with `--base-ref` set to the
    merge base, plus its final line.
- [ ] No committed reports and no leftover worktrees. Pushed with an
      explicit refspec; no force-push, no rebase. If `main` moves, merge it.
- [ ] The handoff-back covers the tip SHA, `git show --stat` for each
      commit, and the test mapping.

## Branch convention

Run `convmem work start fix issue-308-inter-model-rejection --worktree`.
Then push every commit with `git push origin "${B}:refs/heads/${B}"`.

## Next after implementation

Claude verifies the tip. Then the Copilot audit (targeted:
isolation/fail-open) and the Kiro review run on the exact tip, and Ryan makes
the PR decision. Only after that is merged does the Stage 2 watcher canary
get its grant.

## Verification of `b689df6` (Claude, 2026-10-12) — corrective 1 needed

**What's right:**

- The typed guard outcome, its re-raise, the rejection record and the
  `"skipped"` return are as specified. The watcher-side skip returns before
  the hash comparison, so watcher spawns are fixed.
- The sidecar fails open on corrupt data with one line, writes atomically,
  and serializes writes with `flock`.
- The earlier full-file hash in `watch_skip_reason` is **not** a
  regression. `main` already hashes every file that isn't excluded.

**Blocking. Each needs a test that fails at `b689df6`:**

| # | Finding | Fix |
|---|---|---|
| K1 | **Nine** CI regressions, not environmental. A clean disk-backed full suite gives 9 failed and 3034 passed, and every failure is a hash, pin or inventory check broken by this branch (`main` is green in CI): the canary `ingest.py` hash pinned in three tests (`test_incremental_jsonl_canary_baseline.py::test_t0_baseline_hashes_unchanged`, `test_incremental_jsonl_canary_p2_corrective.py::test_p2_c10_baseline_hashes_and_routes_unchanged` and `test_incremental_jsonl_canary_p2_runtime_readiness.py::test_c0_baseline_hashes_unchanged`), the R2B v2 inventory identity (2 tests in `test_r2b_v2_corrective_viii.py` and 3 in `test_r2b_v2_implementation_revision.py`), and the shadow scan. The shadow scan failure is `test_shadow_writer_coverage_scan.py::test_static_scan_matches_inventory_routing` (pins shifted: `ingest.py:642→661`, `1215→1239`, `1253→1277`; `inter_model_index.py:301→310`). | Refresh the `ingest.py` hash in all three canary baseline tests, each with a one-line comment as the existing entries have. Regenerate the shadow inventory and the R2B v2 inventory artifact with the generators, not by hand-editing. This is the corrective-4b pattern. |
| K2 | The reconciler suppresses only `new_eligible_source` (`recorded is None`). The realistic #308 case is a doc that was **already indexed at this path**, since the guard fires only when a projection exists. Its old processed entry gives `recorded != observed`, so `source_hash_mismatch` is still reported (`source_reconciler.py:~160–168`). | Apply the same path-and-hash rejection match before emitting `source_hash_mismatch`. Test: a doc indexed, then changed, then rejected gives no reconciler finding; after a further content change, the finding comes back. |

**Reviewer notes (not blocking; Copilot and Kiro to rule):**

- The sidecar shares the `processed.json.lock` flock. That's safe today:
  the rejection is recorded before the processed commit, and readers don't
  lock. But `flock` is per open file, so any future call nested inside a
  `processed.json` mutation would deadlock. Consider a separate lock file.
- The sidecar is a new write in the production data root, outside
  `production_writer_boundary`. Check it against the governed-writer and
  writer-coverage policy.

**Process:** the handoff-back called all 19 local failures environmental
without a clean disk-backed run, and four of them are real. The acceptance
run must use a clean, disk-backed checkout (not tmpfs or a sandbox) with a
fresh CI config.

## Verification of `1e76650` (Claude, 2026-10-12) — corrective 2 needed (small)

**Fixed since `b689df6`:**

- **K1.** All nine pin regressions are fixed.
  - The three canary tests import one shared `BASELINE_HASHES` table, so the
    one refreshed `ingest.py` hash covers all three.
  - The R2B v2 inventory changes only its revision identity
    (`code_revision` and `inventory_digest`), as expected.
  - The shadow call-site lists match the static scan.
- **K2.** The reconciler now skips `source_hash_mismatch` on a path-and-hash
  rejection match. The tip's test file run against the `b689df6` code gives
  `1 failed, 7 passed`. The failure is
  `test_reconciliation_suppresses_hash_mismatch_for_rejected_content`, so the
  test proves the fix.
- **Pylint gate PASS** on a clean disk-backed worktree, with base `05aa2c8`:
  "461 findings, 240 fingerprints; no new/increased vs baseline".

**Blocking:**

| # | Finding | Fix |
|---|---|---|
| K3 | The rewrite of `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json` lost two facts from its `sites` detail that `main` had right. No test reads `sites`, which is why it passed. (1) The `cg2_rehearsal.py:951` entry (class `cg2_rehearsal_scratch`, allowlisted direct, with the note "Legacy-only rehearsal creates and mutates only an isolated tmp_path Chroma root.") is gone, although `allowlisted_direct_sites` still lists `cg2_rehearsal.py:951`. (2) `ingest.py:1239` is the reindex-snapshot read (`_ReindexSnapshot`, "Snapshot only the rows a completed replacement may later prune"). `main` classed that site `reads_reindex_snapshot_under_writer_gate`, but the tip classes it `mutates_units`. | Restore the 951 entry exactly as on `main`, after the `cg2_rehearsal.py:199` entry. Set `ingest.py:1239`'s class to `reads_reindex_snapshot_under_writer_gate`. Keep the corrected line numbers (661, 1239, 1277 and 310). The R2B generator reads only the call-site lists, not `sites`, so the R2B artifact needs no regeneration. Confirm with the shadow and R2B tests. |
| K4 | `main` moved to `138e3aa` (#386, OpenClaw planning docs only; no file overlap). | Merge `origin/main` (no rebase). |

**Out of scope:** `sites` was already stale on `main`. Five allowlisted
sites have no `sites` entry there (`cg2_legacy_vector_attestation.py:930`,
`chroma_store.py:83` and `:108`, `chroma_write_store.py:666` and
`incremental_jsonl_canary.py:1234`). That gap pre-dates this branch and
isn't on the burn path, so it isn't part of #308.

**Nits (optional):**

- The two reconciler branches repeat the same import and lookup; one small
  helper would do.
- The new K2 test is missing the second blank line before it.

**Full suite (Claude, clean disk-backed worktree, fresh CI config, tip
`1e76650`):** "3044 passed, 9 skipped, 2 warnings, 252 subtests passed in
1890.90s", with **no failures**. That is the 3034 that passed at `b689df6`,
plus the nine fixed pins and the new K2 test. The 10 failures in Cursor's
run don't reproduce on a clean checkout, so they came from Cursor's run
environment and not from the branch.

Corrective 2 changes only JSON, plus a docs-only `main` merge. So the
targeted tests named in the K3 fix are enough; there is no need for another
full run. If Cursor takes the reconciler nit, the Pylint gate must also be
rerun.

## Verification of `74e193f` (Claude, 2026-10-12) — PASS, ready for review

Corrective 2 is two commits:
- the merge of `origin/main` at `138e3aa`, docs-only #386 (K4);
- `74e193f`, the K3 fix plus the reconciler helper.

- **K3 closed.** The shadow inventory's `sites` now equals `main`'s 33
  entries, ignoring line numbers. `ingest.py:1239` is
  `reads_reindex_snapshot_under_writer_gate`, and `cg2_rehearsal.py:951`
  is restored. The only other change from `main` is the corrected call-site
  line numbers.
- **R2B.** It was regenerated because `source_reconciler.py` changed. Only
  `code_revision` and `inventory_digest` differ (`3b6685af` to `e196ccd4`).
- **Reconciler helper.** `_skip_recorded_inter_model_rejection` is a pure
  refactor of the two duplicated lookups, and behavior is unchanged.
  Cosmetic only: there are four blank lines before the helper and one after
  it. This is non-blocking, and no linter in CI checks it.
- **Targeted tests,** clean disk-backed worktree, fresh CI config: 63
  files (#308, shadow, R2B v2, reconciler, canary, watch, inter-model and
  T3 residual), giving "461 passed, 6 skipped".
- **Pylint gate PASS:** base `138e3aa`, "463 findings, 240 fingerprints; no
  new/increased vs baseline". The two extra findings against `1e76650` are
  `cyclic-import` reports attributed to `writer_census.py`. The branch only
  moved an existing local import into a helper.
- **Full suite:** `1e76650` was clean (0 failures, above). Since then, only
  JSON and a behavior-neutral refactor have changed, and CI reruns the full
  suite on the PR.

**Next:** the headless Copilot audit (fail-open, writer narrowness,
suppression, isolation, lock, writer boundary) and the Kiro conformance
review, both at `74e193f`. Then Ryan's PR decision.

## Reviews of `74e193f` (2026-10-12) — Kiro PASS, Copilot FAIL; corrective 3

Both reviews ran headless, launched by Claude, on the exact tip.

- **Kiro: PASS.**
  - The change conforms to integration points 1–4, the Specification and
    "What NOT to build".
  - The retry loop is closed for both the never-recorded and the
    previously indexed case.
  - The shared lock is safe today. Advisory condition: use a separate lock
    file if a rejection is ever recorded while `_processed_lock` is held.
  - Writer-boundary registration isn't required, and the clear path is
    sufficient.
  - Kiro based its fail-open ruling on test 7, which uses `"{not json"`
    only.
- **Copilot: FAIL on item 1 (fail-open).** Items 2–6 are closed.
  - `load_inter_model_rejections` (`inter_model_rejections.py:53–70`)
    catches only `OSError` and `JSONDecodeError`.
  - A sidecar with invalid UTF-8 or a partial multibyte tail raises
    `UnicodeDecodeError`, and deep nesting (`[` × 200000) raises
    `RecursionError`.
  - Both escape `watch_skip_reason`, which `watch.py:476` calls for every
    path with no guard. They also escape `discover_legacy_source_drift`.
  - `record_provenance_supersession_rejection` loads the file first, so it
    can't heal the corruption.
  - Expected effect: every watcher index attempt fails, and startup
    reconciliation (`watch.py:~699`, which catches only `OSError` and
    `RuntimeError`) aborts.

**Claude's reproduction (hermetic, tip `74e193f`):**
`inter_model_rejection_matches` raises `UnicodeDecodeError` for
`b"\xff\xfe\x00"` and for a partial multibyte tail, and `RecursionError` for
`b"[" * 200000`. It returns `False` with one diagnostic for `b"{not json"`.
The finding stands. It is a spec violation ("never crashes the watcher or
the reconciler"), not a factual conflict between reviewers, so it's not a
Sol-High case.

**Corrective 3, binding:**

| # | Fix | Test (must fail at `74e193f`) |
|---|---|---|
| C3-1 | In `load_inter_model_rejections`, fail open on `ValueError` (which covers `UnicodeDecodeError` and `JSONDecodeError`) and on `RecursionError`, with the same one-line diagnostic. A record written onto a corrupt sidecar then replaces it instead of raising. | Parametrize the corrupt-sidecar test over invalid UTF-8, a partial multibyte tail and deep nesting. For each case, `watch_skip_reason` and `discover_legacy_source_drift` suppress nothing and don't raise, and `record_provenance_supersession_rejection` succeeds and leaves a readable sidecar. |

**Optional (Copilot advisories; take only if cheap):**

- Make the record write best-effort. An `OSError` from the sidecar write
  (ENOSPC or EROFS) prints one diagnostic and `_index_one_file` still
  returns `"skipped"`. Today `index()` aborts; it stays retryable either way.
- Pass `processed_log` from `cfg` at the `flush_path` call
  (`watch.py:476`), so the call doesn't fall back to `load_config()`.
  `watch.py` is pinned in the canary `BASELINE_HASHES`, so this also needs a
  pin refresh with a comment.

**Not in #308; follow-ups for Ryan:**

- **The restore classifier.** `complete_data_restore.STATE_SPECS` doesn't
  classify `inter_model_rejections.json`, so restore validation would report
  `BLOCKED_UNCLASSIFIED_STATE` once the file exists. The live data root
  already has the same gap on `main` with `source_reconciliation.json`.
  Recovery Authority owns `STATE_SPECS`, so both files belong in one
  follow-up there.
- **Unused cleanup functions.**
  `clear_inter_model_rejection_for_path` and
  `prune_stale_inter_model_rejections` have no production callers. Stale
  records are harmless, because a match needs the current hash.
- **Symlinks.** A symlinked `processed.json` would split the sidecar lock
  from the processed lock. The live `processed.json` is a regular file, so
  this doesn't apply.

**Acceptance for corrective 3:** run the #308, shadow, R2B v2 and canary
tests. Regenerate the R2B inventory, because `inter_model_rejections.py` is
in its authority manifest. Rerun the Pylint gate with `--base-ref` set to
the merge base. Push with an explicit refspec. After that, Claude verifies,
then a targeted Copilot re-check of item 1 and a Kiro delta confirmation run
on the new tip.

## Verification and reviews of `bbf09d1` (2026-10-12) — corrective 4

**Claude's checks:**
- **The new tests prove the fix.** With a one-line shim for the new test
  helper, the tip's #308 test file run against the `74e193f` code gives "3
  failed, 8 passed". The failures are the three `test_corrupt_sidecar_fails_open`
  cases.
- **Pylint gate PASS:** base `138e3aa`, "459 findings, 240 fingerprints".
- **R2B:** identity-only (`e196ccd4` to `d5f5e2d0`). The shadow inventory is
  unchanged.
- **`watch.py`:** `flush_path` already loads `cfg` and passes that same
  `processed_log`. `rejections_path` calls `expanduser()`, so a `~` path is
  safe.
- **Cosmetic:** the refreshed `watch.py` pin has no #308 comment.
- **Full suite** (clean disk-backed worktree, fresh CI config, tip
  `bbf09d1`): "3047 passed, 9 skipped, 2 warnings, 252 subtests passed in
  1827.14s", with **no failures**. That is the 3044 that passed at
  `1e76650`, plus the three new corrupt-sidecar cases. It covers the
  `watch.py` change. Corrective 4 touches only `inter_model_rejections.py`,
  its tests and the canary pin comment, so targeted tests are enough there.

**Kiro: PASS at `bbf09d1`.** The delta stays within corrective 3, and the
`74e193f` rulings stand.

**Copilot: FAIL at `bbf09d1`.**
- **Item 1 is closed.** Copilot ran 24 hermetic corrupt-sidecar cases.
  None raised, none suppressed anything, and a record healed the file.
- **The new failure** comes from the optional best-effort write:
  `save_inter_model_rejections` now swallows `OSError` for every caller.
  `clear_inter_model_rejection_for_path` therefore returns `True` when the
  write fails, while the record stays on disk and `watch_skip_reason` keeps
  returning `inter_model_rejected`. At `74e193f` this raised.
- **Diagnostics:** write failures share the read one-shot guard, so after
  any earlier read diagnostic they print nothing. The wording also says
  "unreadable".
- **Lock:** a failure opening the lock (EROFS) still raises out of the
  record path.

Claude confirmed this by reading the code: `clear` returns `found["ok"]`
whatever the save did. Kiro passed the tip but didn't examine the clear
path. As before, this is a checkable fact, not a reviewer conflict, so it
isn't a Sol-High case.

**Corrective 4, binding:**

| # | Fix | Test (must fail at `bbf09d1`) |
|---|---|---|
| C4-1 | Revert `save_inter_model_rejections` to raise on `OSError`, as at `74e193f`. Make only the **record** path best-effort: `record_provenance_supersession_rejection` catches `OSError` from the whole mutation, including opening the lock, and prints a write-specific line such as "`inter_model_rejections.json` could not be written; the doc will be retried: {exc}". That line uses its own one-shot guard, not the read guard. `clear_inter_model_rejection_for_path` and `prune_stale_inter_model_rejections` propagate `OSError` again. | Use `monkeypatch` to make `atomic_write_text` raise `OSError` (no chmod). (a) `clear_inter_model_rejection_for_path` raises, and the record still matches. (b) `record_provenance_supersession_rejection` doesn't raise, and prints the write line even after a read diagnostic was already printed. (c) The same holds when opening the lock raises `OSError`. (d) Through `_index_one_file`, a guard rejection with a failing write returns `"skipped"` and records nothing. |

**Also:** add a one-line #308 comment to the refreshed `watch.py` canary
pin.

**Acceptance:** run the #308, shadow, R2B v2 and canary tests. Regenerate
R2B. Run the Pylint gate with `--base-ref` set to the merge base. Push with
an explicit refspec. After that, Claude verifies, and then a targeted
Copilot re-check of this item and a Kiro delta confirmation run on the new
tip.
