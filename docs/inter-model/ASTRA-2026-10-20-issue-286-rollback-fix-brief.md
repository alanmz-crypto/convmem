# [Arc Codex #286] Cursor brief: preserve valid processed state during rollback

**Author: Codex investigative lane. Recipient: Kiro for review, then Cursor only after Ryan's Execute grant. Date: 2026-10-20 UTC.** Proposed correction against main `686d50e`; no production code changed. This is not a deployment, repair or provider-spend grant. [Investigation and exact R-975 repair](ASTRA-2026-10-20-issue-286-rollback-empty-before-image.md).

## Outcome and scope

A CLI contender can carry a processed dictionary read before another run finished, wait for the incremental source lock, then record that stale dictionary as rollback authority. Later rollback can erase a valid entry. The restore also bypasses the processed lock and can lose unrelated writers' changes. A regression test currently expects an unowned same-source edit to be silently deleted.

Make capture use current persisted truth; refuse internally inconsistent authority; merge rollback changes under the processed lock without overwriting unowned state. Keep checkpoint-before-processed ordering and provider-free write critical sections. Preserve pending evidence on every uncertainty. The smallest safe correction includes capture, recovery preflight, locked merge, and targeted tests. A fresh-read-only patch is insufficient.

Implementation candidates: `incremental_jsonl.py`, the existing processed helpers in `ingest.py` if a narrowly reusable helper is needed, and focused incremental/processed-state tests. Keep persisted schemas unchanged if the current checkpoint/transaction/prepared evidence proves ownership; if it cannot, refuse. A new persisted authority field/version requires an explicit reviewed design decision. Do not quietly rewrite existing rollback files to make them pass.

Excluded work: R-975/R-914 live repair, bootstrap/reindex, checkpoint migration, provider/config changes, runtime promotion, watcher/quarantine operations, global writer-fence implementation, unrelated corpus recovery. Do not alter the historical donor or rollback authority. Do not open a PR under this investigative grant.

## Required behavior

### A. Capture from disk at the mutation boundary

- `_snapshot_before_images()` must not use `processed_override`, directly or indirectly. Treat the override as a caller cache, never recovery authority. Remove its authority use for exclusion checks as well, or otherwise prove those checks use fresh state.
- Read the source slice under the existing stable processed sidecar lock, **after acquiring the relevant source lock**, immediately before journaling/apply. Release the processed lock before Chroma/export/provider work. Avoid a read helper that creates a second, different lock namespace.
- Filter using one documented canonical source-ownership rule; detect ambiguous historical aliases rather than losing them. Preserve original hash keys in the captured mapping. A hash-keyed entry with a canonical `path` is normal.
- For an existing incremental checkpoint, require the exact checkpoint `processed_hash` (or documented prefix fallback), correct path, non-excluded entry and matching lineage. Require the captured projection to agree with that checkpoint. A prior checkpoint plus missing/mismatched follower is a refusal before APPLYING, not an empty rollback snapshot.
- A genuinely new source with no checkpoint/rows/processed entry may have `{}`. Checkpointless bootstrap retains its existing legacy-entry semantics. Do not blanket-ban empty preimages or require incremental lineage on a legacy bootstrap donor.

### B. Validate authority before any restore mutation

- Add structural and semantic validation: processed preimage must be a mapping of valid entries owned by this source; inspect the embedded prior checkpoint, not only the current checkpoint; verify its expected key/lineage and captured row projection. Missing/wrong source entries or the R-975 empty-with-checkpoint shape must fail closed.
- Perform this check before any Chroma deletion/upsert, export write, state/prepared restore, dedupe rewrite or cleanup. Retain transaction, rollback, snapshot and prepared evidence byte-identically on a preflight refusal.
- Do not “repair” bad authority from current disk by rewriting its bound SHA. Do not reconstruct absent legacy counts from row counts when dedupe semantics could differ.
- Preflight current source state against before-state and positively proven transaction-owned changes. Same-source data written by another transaction/legacy route, foreign key ownership, exclusion/purge, or unexplained projection/export drift is a conflict. If corrupt prepared material prevents ownership proof, refuse rather than broaden what may be deleted.
- Preserve the existing v1/v2 recovery gate. A new v2 transaction must get this protection; do not remove the gate to make the old incident replay under main.

### C. Restore processed state by locked merge, with conflict checks

- Use `mutate_processed()` (or an equivalently governed existing primitive): lock, reload, compare source slice, update only authorized source entries, atomic-save, unlock. Never call unlocked whole-file `save_processed()` on a previously loaded snapshot.
- An unchanged before-slice is an idempotent no-op. A changed slice is eligible only when exact ownership by this transaction is proven from valid transaction/checkpoint/prepared evidence. A later matching path alone is not ownership. Do not infer transaction ownership merely from a plausible lineage string.
- Never delete or overwrite a current exclusion/purge marker. Never overwrite a hash key now owned by a different source. Never erase a later same-source generation or copy stale foreign keys back into disk. The default for ambiguity is refusal.
- Repeat the source-slice check inside the final merge even after preflight. If a processed-only writer changed it in the meantime, leave its state intact and retain recovery authority. Report partial recovery honestly if earlier surfaces were already restored; do not call `_cleanup()` or return `rolled_back` as if the whole recovery succeeded.
- Acquire the shared `source_flock` **before C1** around rollback, as commit/purge do. Do not confuse that lock with `SourceAdvisoryLock`. Check nested/reentrant acquisition and all entry paths before adding locks.
- Do not hold `processed.json.lock` through Chroma/export work to paper over ownership. Soft exclusion and processed publication have separate timing; preflight plus final CAS does not create a cross-surface atomic transaction. Full writer fencing remains a separately reviewed boundary.

## Hermetic acceptance tests

All tests use an isolated temporary HOME/config/data tree, fake transforms/embeddings, network denied with a connection tripwire, and synthetic source content. Do not point tests at the incident's live source or invoke real providers. Use barriers/events for races, not sleeps. Every refusal case checks exact bytes/hashes on all affected scratch surfaces and retained authority; success checks exact scoped changes.

1. **Stale empty caller dictionary through the real route:** B loads `{}` before the source lock; A commits checkpoint + processed entry; B resumes with its old dictionary and captures an append. Assert the journal contains A's actual persisted entry, matching the embedded checkpoint. Force the rollback branch and verify A's entry survives. Exercise `maybe_route_incremental`, not just a manually constructed coordinator with `processed=None`.
2. **Stale nonempty caller:** repeat with B holding generation N-1 and disk/checkpoint at N. The journal must capture N. This prevents a fix limited to treating `{}` as false.
3. **R-975 synthetic shape:** valid bound rollback SHA, prior checkpoint/rows, empty processed preimage, current valid entry. Recovery must refuse before the first write and retain all journal/snapshot bytes. Repeat with nonempty wrong key, wrong lineage, wrong path and wrong mapping type. Hash-valid is not semantically valid.
4. **Legitimate empty and legacy bootstrap:** brand-new source rollback with genuinely empty before-state still works. Legacy checkpointless bootstrap with a hash-keyed entry lacking incremental lineage still works under its existing grant semantics. A content-hash key must not be confused with a path key.
5. **Aliases and collisions:** exact canonical path under an arbitrary hash is captured; relative/symlink/`..` spellings are handled by the selected ownership policy or explicitly refused without loss. A preimage hash now belonging to another source is preserved and causes refusal.
6. **Concurrent foreign processed writer:** pause restoration at its read/merge boundary and contend with a real `mutate_processed()` writer. Independent insert/update/delete must survive whichever lock order wins. Verify unrelated-map equality, not only one key. Assert the stable sidecar is held by the restore path.
7. **Later same-source publication and exclusions:** introduce a legitimate later generation or exclusion before replay; assert preflight refusal before any restore mutation. Inject a processed-only update after preflight; assert the final CAS refuses without erasing it, retains authority, and reports any partial recovery. Test purge acquiring source then C1, and soft exclusion that only uses the processed mutator.
8. **Owned post-publication rollback and crash boundaries:** force crashes before checkpoint, after checkpoint but before processed publish, after publish before cleanup, and during restore. Recover only when before-state and transaction-owned state are provable. Retrying a successful scoped restore is idempotent; a crash never converts an unknown state into deletion authority. Include corrupt prepared artifacts: uncertainty must preserve evidence.
9. **Other rollback surfaces:** put an unowned later same-source Chroma row/export line/prepared artifact into scratch after capture. Recovery must refuse unless ownership can be positively proven. This prevents a processed-only fix from advertising broader recovery correctness it does not supply.
10. **Routing and lock order:** run the focused paths for admitted Codex v2 and Kiro production-boundary equivalents inside isolation, plus bootstrap replay. Verify no reverse `C1 → source` acquisition, no nested-source deadlock, no provider call under write scopes, and no global processed lock held during Chroma/export work.

Existing tests to adapt:

- `tests/test_incremental_jsonl_state.py::test_restore_rewinds_processed_checkpoint_and_state` directly injects `processed['tampered']` and asserts rollback deletes it. Replace the unowned-edit expectation with refusal; add a separate positively transaction-owned restore test. Do not keep this assertion by bypassing the safety gate in production replay.
- Existing bootstrap/repeated-replay tests in `tests/test_incremental_jsonl_live_boundary.py` must continue to preserve the original authority. Test route callers that provide stale dictionaries; many direct coordinator fixtures do not reproduce that condition.
- Inspect the production writer inventory requirements after any code change and regenerate/review as required by the repo; no inventory update or production test was performed in this investigation.

The investigator's 18 method-level reproductions are evidence of the current defects, not passing acceptance tests for a fix. Cursor should first demonstrate the new regression tests fail on `686d50e`, then pass on the correction, with zero attempted provider connections and no live-path writes. Run the focused suites and required repository checks; use the existing independent review lanes for sign-off.

## Separate R-975 repair and review decisions

The [report §7](ASTRA-2026-10-20-issue-286-rollback-empty-before-image.md#7-r-975-exact-repair-specification--not-executed) specifies the exact one-entry metadata repair, donor hash, checkpoint/source/projection checks, idempotence, scoped reversal and spend boundary. Do not silently include it in code execution. R-914's matching projection and missing processed entry warrant investigation, but no donor/rollback attribution has been established.

Kiro decisions needed: accept the conservative refusal policy for old inconsistent/ambiguous journals; accept the narrow locked-merge scope and explicit cross-surface limitation; decide whether to prepare a separately rehearsed R-975 repair packet. Ryan owns Execute, repair/spend/restart grants and merge.

I finished: [Arc Codex #286] proposed Cursor correction scope and hermetic acceptance criteria.
Next step: Kiro reviews, then Ryan may grant Cursor implementation.
Next lane: Kiro → Ryan → Cursor.
See my work: this brief and the linked evidence report.

**TL;DR:** [Arc Codex #286] Fix fresh capture, semantic recovery validation and locked conditional merge together. Preserve unknown later state and recovery evidence; reject stale authority before writes. R-975 repair and watcher spend remain separate grants.

<!-- src: ./ASTRA-2026-10-20-issue-286-rollback-empty-before-image.md, ../../incremental_jsonl.py, ../../ingest.py — defect evidence and bounded correction -->
<!-- ref: ../../tests/test_incremental_jsonl_state.py, ../../tests/test_incremental_jsonl_live_boundary.py, ../plans/STATUS-codex-jsonl-production-integration.md — acceptance tests and next lane -->
