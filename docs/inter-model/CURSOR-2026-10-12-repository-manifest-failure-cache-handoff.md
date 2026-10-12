# Implementation Handoff: stop the invalid-manifest watcher leak, and keep the manifest valid

**Arc: Codex (#286), Stage 2 prerequisite.** This crosses into OpenClaw Watch
Coverage, which owns repository knowledge. Ryan authorized the cross-arc work
on 2026-10-12.
**Date:** 2026-10-12
**Author:** Claude (Opus 5.5), from the Stage 2 leak diagnosis
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-10-12. He authorized fix options 2 (the durable
code fix) and 3 (data and CI guard) from the Stage 2 run log. He also
granted option 1, removing `watch.repository_knowledge_manifests` from the
live config, and Claude has already done that.

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `fix/2026-10-12-repository-manifest-failure-cache`, created from `origin/main` |
| **Tip SHA** | base `origin/main` `8a7cdab` |
| **Push status** | handoff pushed on `docs/2026-10-12-repository-manifest-failure-cache-handoff` |
| **PR** | not opened |
| **Ryan GATE** | none for hermetic implementation. Ryan alone merges. Putting the manifest back in the live config is a separate Ryan grant, after the merge. |
| **Track A ingest** | your Cursor transcript, at handoff |

## What to build

**Why:** on 2026-10-12, the Stage 2 watcher canary had to be stopped at
T0 + 16 min.
- The watcher's own heap reached 4.07 GiB with no index work, growing about
  144 MB/min. Before Oct 5 it held steady at about 0.46 GiB.
- The cause: the repository-knowledge manifest
  `config/repository-knowledge/openclaw-watch-scope-v1.json` is **invalid**
  on `main`, because it lacks **63 tracked paths**. An invalid manifest is
  then re-validated **on every filesystem event**, and each failure leaks.
- Evidence: the Stage 2 run log
  (`docs/inter-model/CLAUDE-2026-10-12-issue-286-codex-stage2-run.md` on
  `docs/2026-10-11-issue-286-codex-stage1-run`), sections "Root cause found"
  and "Hermetic diagnosis".

**The defect, at `8a7cdab`:**

1. On every event, `adapters/detect.py:78` `detect_format` calls
   `classify_detect_state`, which calls `decide_path`
   (`repository_knowledge_scope.py:744`). That calls `_cached_manifest`
   (`:706–724`) for each configured manifest.
2. `_cached_manifest` caches a valid `LoadedManifest`. It also stores a
   **failure** in `_loaded_by_path` (`:164`), but only an
   `isinstance(cached, LoadedManifest)` value is ever reused. A stored
   exception is ignored, so every call runs `load_and_validate_manifest`
   (`:559`) again: it reads 306 KB, parses the JSON, runs `git ls-files`
   and the cleanliness check, and builds the classification table.
3. The stored exception's `__traceback__` references the frame that holds
   that data, and the frame references the exception. Only a full GC frees
   that cycle.

   `tracemalloc`, live-faithful, minute 3:

   | Allocation | Growth |
   |---|---|
   | Parsed JSON | +103 MiB |
   | Raw text (137 copies) | +40 MiB |
   | `git ls-files` lists | +22 MiB |
   | Classification rows | +19 MiB |

   The hermetic reproduction gave +84 MB/min, against flat with a valid
   manifest.
4. The manifest went stale silently, because no test checks the committed
   manifest against the tracked tree. #339 (`a92a74e`) was the last manual
   reclassification.

## Integration points

1. `repository_knowledge_scope.py:706–724` (`_cached_manifest`). This is the
   failure-cache fix.
2. `repository_knowledge_scope.py:164` (`_loaded_by_path`). Its value type
   may change to carry the failure key.
3. `config/repository-knowledge/openclaw-watch-scope-v1.json`. This is the
   data fix.
4. A new test module, for example
   `tests/test_repository_knowledge_committed_manifest.py`. This is the CI
   guard.

## Specification

**C1, failure caching (binding).**
- Cache a failed load keyed by the same freshness key a success uses: the
  manifest's sha256 and the coverage root's git HEAD. Re-raise the cached
  failure while both are unchanged.
- Re-validate only when the manifest bytes change or HEAD moves.
- Store the failure **without** its traceback, for example by saving the
  code and detail, or `exc.with_traceback(None)`. No frame can then be
  retained.
- `decide_path` keeps its current behavior on a failing manifest: it still
  blocks paths under that root, with the same code and detail.

**C2, data (binding).**
- **Classify all 63 unclassified tracked paths**, following the #339
  pattern. A path that is neither admitted nor an exclusion target is
  `unrelated`, to match its neighbours, so the indexed set doesn't change.
  Only a path that clearly belongs in an existing include or exclude
  family gets that class, with a reason.
- **Then fix whatever `load_and_validate_manifest` reports next.** Claude's
  read-only check of `main` found **14 include entries whose pinned sha256
  no longer matches the file**. All 14 are listed in the appendix.
- Refresh the hashes the way #339 did ("refresh admitted-file hashes").
  Keep each entry's other fields.
- The **end state**: `load_and_validate_manifest` passes on the branch tip,
  including the files this branch adds.

**C3, CI guard (binding).**
- A hermetic test that loads the committed manifest from the repo checkout
  and asserts that `load_and_validate_manifest` passes. That means every
  tracked path is classified, nothing extra, and the include hashes match.
- Its failure message must name the first unclassified or stale path, and
  say how to fix it.
- It runs in normal CI. Skip it only where git isn't available. On a dirty
  tree, a clear skip message is acceptable, because CI is clean.

**C4, optional (take only if cheap).**
- Even with a valid manifest, each event hashes 306 KB and spawns
  `git rev-parse` (`git_head`). A stat pre-check (`st_mtime_ns` and
  `st_size`) before re-hashing would cut that cost, and so would reading
  HEAD without a subprocess.
- Don't change the freshness semantics.

## Output contract

- `decide_path` and `classify_detect_state` keep the same signatures and
  the same `PathDecision` values.
- `load_and_validate_manifest` behaves the same.
- The manifest keeps its schema; only rows and hashes change.

## What NOT to build

- No change to repository-knowledge admission policy, classification
  semantics, retrieval or indexing.
- No change to the watcher loop, the debounce, or the Codex or #308 code.
- **No live config change.** The manifest stays out of the live config
  until Ryan grants putting it back, after this merges.
- No live indexing, no watcher start and no provider calls. Tests are
  hermetic.
- Don't re-include or re-exclude files beyond what classifying the 63 paths
  needs.

## Test expectations

All hermetic. Tests 1–3 must fail at `8a7cdab`:

1. With an invalid manifest, N `decide_path` calls with an unchanged
   manifest and HEAD run `load_and_validate_manifest` **exactly once**.
   Spy on it or count calls.
2. With an invalid manifest, repeated `decide_path` calls don't grow traced
   memory. For example, after 500 calls `tracemalloc` growth stays under a
   small bound, or no stored failure has a `__traceback__`.
3. The committed manifest validates against the repo checkout (C3).
4. After the manifest bytes change or HEAD moves, the next call
   re-validates, and recovers when the manifest is now valid.
5. A failing manifest still blocks paths under its root, with the same code
   and detail as before.

## Acceptance criteria

- [ ] C1–C3 are implemented, each test is mapped by name in the
      handoff-back, and C4 is reported as taken or skipped.
- [ ] A clean, **disk-backed** checkout with a fresh CI config gives the
      full-suite summary line. The only failure allowed is the known #320
      golden eval.
- [ ] The exact Pylint regression-gate command, with `--base-ref` set to the
      merge base, plus its final line.
- [ ] The R2B v2 and shadow inventories and the canary pins, regenerated or
      refreshed if any of them pin the changed files. Use the generators,
      never hand-edits, and list each one.
- [ ] Pushed with an explicit refspec. No force-push and no rebase; if `main`
      moves, merge it.
- [ ] The handoff-back covers the tip, `git show --stat` for each commit,
      and the test mapping.

## Branch convention

Run `convmem work start fix repository-manifest-failure-cache --worktree`.
Then push every commit with `git push origin "${B}:refs/heads/${B}"`.

## Next after implementation

1. Claude verifies the tip, including a hermetic leak re-run: the invalid
   manifest plus events must now stay flat.
2. A targeted Copilot audit (failure-cache correctness, no retained frames,
   CI guard) and the Kiro review, both on the exact tip.
3. Ryan's PR decision.
4. After the merge, a separate Ryan grant puts
   `watch.repository_knowledge_manifests` back in the live config and
   promotes `runtime-main`.

## Appendix: worklist at `8a7cdab` (Claude, read-only)

Computed from `git ls-tree -r 8a7cdab` against the committed manifest. There
are 1548 tracked paths and 1485 classification rows: 63 paths are missing,
and 0 rows are extra. Recompute on your branch tip, because your own new
files need rows too.

**Unclassified tracked paths (63):**

- `bootstrap_safety.py`
- `bootstrap_supersession.py`
- `docs/inter-model/CLAUDE-2026-09-27-pr-steward-reminder-decision-handoff.md`
- `docs/inter-model/CLAUDE-2026-10-11-issue-286-codex-stage1-packet.md`
- `docs/inter-model/CODEX-2026-10-05-issue-286-live-activation-handoff.md`
- `docs/inter-model/CURSOR-2026-10-10-issue-286-codex-rollout-admission-execute-handoff.md`
- `docs/inter-model/CURSOR-2026-10-11-issue-286-codex-rollout-admission-corrective-4-handoff.md`
- `docs/inter-model/SOL-2026-10-09-issue-286-bootstrap-review-packet.md`
- `docs/inter-model/SOL-2026-10-09-issue-286-bootstrap-safety-corrective-execute.md`
- `docs/plans/ARCHITECTURE-safe-harbor.md`
- `docs/plans/DESIGN-issue-286-codex-rollout-admission.md`
- `docs/plans/DESIGN-issue-286-live-activation.md`
- `docs/plans/EVIDENCE-watch-oom-exposure-index-e2e-20261010T032215Z-5980fdce.json`
- `docs/plans/EVIDENCE-watch-oom-exposure-index-e2e-20261010T210439Z-31f4ffc5.json`
- `docs/plans/EVIDENCE-watch-oom-exposure-index-e2e-20261010T233510Z-9e8ad3b2.json`
- `docs/plans/EVIDENCE-watch-oom-exposure-index-e2e-20261011T004945Z-e0bd34c6.json`
- `docs/plans/EVIDENCE-watch-oom-exposure-index-e2e.json`
- `docs/plans/EXECUTION-safe-harbor.md`
- `docs/plans/STATUS-safe-harbor.md`
- `docs/plans/VERIFY-safe-harbor.md`
- `hermetic_open_guards.py`
- `hermetic_path_guard.py`
- `incremental_jsonl_codex_admission.py`
- `incremental_jsonl_production.py`
- `inter_model_rejections.py`
- `live_diagnosis.py`
- `scripts/bootstrap-incremental-jsonl.py`
- `tests/test_incremental_jsonl_bootstrap_command.py`
- `tests/test_incremental_jsonl_bootstrap_safety.py`
- `tests/test_incremental_jsonl_bootstrap_supersession.py`
- `tests/test_incremental_jsonl_codex_admission.py`
- `tests/test_incremental_jsonl_codex_admission_predicate_extra.py`
- `tests/test_incremental_jsonl_codex_corrective_4.py`
- `tests/test_incremental_jsonl_codex_corrective_5.py`
- `tests/test_incremental_jsonl_codex_rollout_route.py`
- `tests/test_incremental_jsonl_codex_route_corrective.py`
- `tests/test_incremental_jsonl_codex_watch_corrective.py`
- `tests/test_incremental_jsonl_live_boundary.py`
- `tests/test_issue_308_inter_model_rejection.py`
- `tests/test_jsonl_prefix_streaming_digest.py`
- `tests/test_live_diagnosis.py`
- `tests/test_safe_harbor_t1.py`
- `tests/test_watch_oom_cgroup_runner.py`
- `tests/test_watch_oom_exposure_index_e2e.py`
- `tests/test_watch_oom_live_diagnosis_d1.py`
- `tests/test_watch_oom_live_diagnosis_d1_canaries.py`
- `tests/test_watch_oom_live_diagnosis_d1_isolation.py`
- `tests/watch_oom_cgroup_common.py`
- `tests/watch_oom_cgroup_probe.py`
- `tests/watch_oom_cgroup_runner.py`
- `tests/watch_oom_cgroup_supervisor.py`
- `tests/watch_oom_exposure_index_e2e_support.py`
- `tests/watch_oom_exposure_index_e2e_worker.py`
- `tests/watch_oom_live_diagnosis_bwrap.py`
- `tests/watch_oom_live_diagnosis_dual_boundary.py`
- `tests/watch_oom_live_diagnosis_inner_supervisor.py`
- `tests/watch_oom_live_diagnosis_net_probe.py`
- `tests/watch_oom_live_diagnosis_parent.py`
- `tests/watch_oom_live_diagnosis_support.py`
- `tests/watch_oom_live_diagnosis_worker.py`
- `tests/watch_oom_mount_probe.py`
- `watch_circuit_breaker.py`
- `watch_source_paths.py`

**Include entries whose pinned sha256 differs from the file at `8a7cdab`
(14):**

- `AGENTS.md`
- `chroma_store.py`
- `config.py`
- `config/agent-protocol.md`
- `convmem.py`
- `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md`
- `docs/plans/EXECUTION-openclaw-convmem-integration.md`
- `docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md`
- `docs/plans/STATUS-openclaw-convmem-integration.md`
- `ingest.py`
- `inter_model_index.py`
- `source_reconciler.py`
- `tests/test_inter_model_doc.py`
- `watch.py`
