# [Arc Codex #286] Implementation Handoff: CI fixes for the forward publication fence

**Date:** 2026-10-21
**Author:** Claude Code (independent review lane)
**For:** Codex Luna, max effort (`codex -m gpt-5.6-luna -c 'model_reasoning_effort="xhigh"'`; if the CLI rejects `xhigh`, use `"high"`)
**Authorization:** Ryan, 2026-10-21 (in chat: "If the fixes are small you can choose luna max to make them in a handoff")

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `fix/2026-10-21-issue-286-forward-publication-cas` (commit on top; do not rebase or force-push) |
| **Tip SHA** | `e6ce3c46aaa250d69129f519eba97bc2be874265` |
| **Push status** | branch pushed; this handoff is on `docs/2026-10-21-issue-286-fence-review-luna-fixes` |
| **PR** | not opened |
| **Ryan GATE** | none for the fixes; PR/merge stays Ryan's |

## Review verdict (Claude, exact tip `e6ce3c4`): PASS-WITH-CHANGES

The safety logic is correct. I checked these points myself:

- **Fence coverage.** Every processed forward-publication route is fenced: the normal incremental commit, crash-recovery roll-forward (`replay_forward`, which uses the same `_commit_generation`), and all three `_index_one_file` branches.
- **Other writers.** Every other processed-sidecar writer either writes exclusions (`exclude_processed_path`, `source_purge`) or is the rollback restore, which already runs under `source_flock`.
- **Lock order.** The order is the same everywhere: coordinator advisory lock (a separate file) → `source_flock` → `index_write_flock` → `_processed_lock`. Nothing nests `source_flock`. No caller of `_index_one_file` holds `source_flock` or C1.
- **Lock scope.** The fence adds only local file I/O: the processed write and unlinks. No provider, network or Chroma work.

The branch **would fail CI on three gates**. All three fixes are mechanical.

## What to build (required)

1. **Pylint regression gate (new in `e6ce3c4`).** In `tests/test_issue_286_rollback_fresh_before_image.py`:
   - line 884 `except BaseException as exc:` → add `# pylint: disable=broad-exception-caught`. The existing `noqa` only silences Ruff.
   - line 906 `assert writer_errors == []` → `assert not writer_errors`.
2. **Shadow writer inventory line drift.** In `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json`, update `production_chroma_write_session_call_sites` as follows:
   - `ingest.py:671→701`, `1257→1287`, `1296→1326` (new in `e6ce3c4`: the 30-line helper);
   - `incremental_jsonl.py:947→940` (already stale at `ec7b8a5`).

   Confirm the mapping with `tests/test_shadow_writer_coverage_scan.py::test_static_scan_matches_inventory_routing`. There is no generator; edit only these coordinates.
3. **R2b v2 inventory (stale since earlier branch commits; `origin/main` passes).** Do this after step 2, because the shadow inventory feeds the R2b authority identity. Regenerate with:
   `python3 -c "import sys; sys.path.insert(0,'.'); from eval_corpus.r2b_v2.coverage.inventory import write_v2_inventory_file; print(write_v2_inventory_file())"`
   Check `docs/plans/SCOPED-PROOF-WRITER-INVENTORY.json` the same way `d8242bb` did. Its tests pass at `e6ce3c4`, so leave it unchanged unless a test says otherwise.
4. **Repository-knowledge manifest, last.** In `config/repository-knowledge/openclaw-watch-scope-v1.json`, refresh the `ingest.py` sha256 (it is `5d1d7dfa…` at `e6ce3c4`). Refresh every other include hash that steps 1–3 changed, the same way `6dd3160` did. Guard: `tests/test_repository_knowledge_committed_manifest.py`.

## Optional (recommended, small)

- **Recovery-path regression.** The new test is named "roll_forward" but exercises the normal commit (`result.mode == "incremental"`). Add a parametrized variant that first crashes with `worker_run(..., fault="before_checkpoint_publish")` / `"after_checkpoint_publish"`, then asserts `result.mode == "replay_forward"` with the same late-writer interception. My probe of exactly this passed on `e6ce3c4` and failed on `ec7b8a5`.
- **Legacy routing regression.** If the three `ingest.py` call sites are reverted to the unfenced helper, only the canary hash pin fails. Add a test that spies on `ingest.commit_processed_index_entry` and asserts `purge_locks.source_lock_depth() == 1` in the generic `_index_one_file` branch (stub `_process_file_chunks` and `maybe_route_incremental`).

## What NOT to build

- No production-code change to `ingest.py` or `incremental_jsonl.py`. If you change them, the canary pins and every inventory must be regenerated again.
- No PR, merge, rebase or force-push; no live Chroma, providers or production stores.

## Acceptance criteria

- [ ] On a clean commit, in its own worktree, all of these pass: `tests/test_config.py` (run first), the Codex 5-file matrix, `tests/test_r2b_v2_implementation_revision.py`, `tests/test_r2b_v2_corrective_viii.py`, `tests/test_shadow_writer_coverage_scan.py`, `tests/test_repository_knowledge_committed_manifest.py`, `tests/test_incremental_jsonl_canary_baseline.py`.
- [ ] The whole-repo pylint gate passes: `pylint $(git ls-files "*.py") --output-format=json > /tmp/p.json; python scripts/pylint_regression_gate.py ci --report /tmp/p.json --pylint-status $? --branch-baseline ci/pylint-baseline.json --base-ref a5405ad`.
- [ ] `git merge-base --is-ancestor origin/main <tip>` holds; pushed with an explicit refspec.

## Evidence (Claude run, 2026-10-21, disk-backed worktrees)

The 26-file focused matrix ran on three trees:

| Tree | Result |
|---|---|
| new tip | 330 passed, 6 failed (the 5 R2b tests + the manifest guard) |
| `ec7b8a5` | 5 failed (the same R2b tests) |
| `origin/main` | the same guards pass, 19/19 |

- **New regression:** 25/25 passes under load. On `ec7b8a5` it fails at the intended assertion.
- **Probes:** 6/6 pass on the new tip and fail on the old tip. They cover recovery replay, a cross-process writer, no blocking of other sources, the C1 ordering guard, and the generic branch holding the lock.
- **Static checks:** canary hashes recomputed and matching; undefined-name pylint clean; `git diff --check` clean; `merge-tree` against main clean.
- **Changed-line coverage (26-file matrix):** every changed line runs except `ingest.py:1547` (inter-model publication) and `ingest.py:1592` (repository-knowledge publication). A probe drove both through the real `_index_one_file`, with only the format-specific indexer stubbed; the stub takes and releases the source lock the way the real helpers do. Both publish with `source_lock_depth() == 1` and return `processed`, with no deadlock. Optional test: cover these two branches in the suite as well.
- **Not run:** the full suite through the Safe Harbor launcher.

**Doc drift (info):** STATUS Update Log (2026-09-10) records the design choice to release the source lock before the processed publication. This fix reverses it on purpose; the arc brief should say so when it is next updated.

<!-- ref: ./CODEX-2026-10-21-issue-286-claude-review-handoff.md — review request this answers (on docs/2026-10-21-issue-286-claude-review) -->
