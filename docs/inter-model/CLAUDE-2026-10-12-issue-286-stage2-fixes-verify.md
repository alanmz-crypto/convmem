# Verify: Stage 2 wedge fixes, round 2 at `117d698`: the fixes work, a small corrective 2 remains

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `117d698`, Cursor
Composer's corrective 1. It answers round 1 (below) and the handoff
`docs/inter-model/CURSOR-2026-10-12-issue-286-stage2-fixes-handoff.md`.
**Method:**
- I read the diff `da7f9a0..117d698` and ran probe tests of my own; the
  appendix has their source.
- I ran the full suite hermetically at `8a7cdab` and at `117d698`, at the same
  time and on the same disk: `env -i`, a scratch `HOME`, no API keys, and
  `tests/test_index_loud_failures.py` skipped.
- Nothing live was touched. I compared mtimes and sizes across the live data
  root before and after, and no `index_write.lock` exists there.

## Verdict (round 2)

**Not ready for review yet. Corrective 2 is small, and none of it involves
paid calls.**

**Fixed since round 1:**
- **F1:** a replay that fails after foreign growth now rolls back
  (`rolled_back`) instead of wedging. This holds both before and after
  `_reconcile_export` has rewritten the export (probes p1 and p2).
- **F2:** the real wedge marker parses all the way through the CLI and the
  watcher (p3). The hold lifts when the prefix changes. On a committed Codex
  route, the watcher's prefix digest equals the coordinator's (p7).
- **F4:** two reviewed rollback tests pass again.
- **F3 and F3b:** test 5 is hermetic. The event filter is a module-level
  function, and its test fails at `8a7cdab`.
- **F5:** `monitor` takes the index lock only around each ingest write.
- **F5a–F5d:** fixed. The retry state now lives in the source's own
  incremental state directory.
- **F6:** delete events are queued again.
- **F8:** the removed comments and the journal-hash re-check are restored.
- **Full suite:** pending. Both runs were 68% done when I committed this; I add the result here when they finish. Cursor's own run reports 0 tests failing only at the tip.

**Still open:**
- two gaps in C3's safety net (G1, G2);
- a C2 deviation hidden behind a test whose name says the opposite (G3);
- a per-event cost added to the watcher (G4).

## Findings (round 2), most severe first

**G1 (medium): C3 counts only failures that `run()` returns, not errors it
raises.**
- **Where:** `maybe_route_incremental` (`incremental_jsonl.py` ~2640–2672)
  records retry state only after `coordinator.run()` returns a result that
  isn't committed. An `IncrementalJsonlError` raised out of `run()`
  propagates instead. Examples are raises from the rollback in
  `_restore_replay_before_images`:
  - the journal changed;
  - a version or source mismatch;
  - a failed file restore.

  The CLI then exits 1, and the watcher retries on every write, with no
  limit and no doctor signal. That is exactly the shape of the production
  wedge. Its two known causes are fixed now, but C3 is the backstop for
  unknown ones. I missed this in round 1.
- **Repro:**
  - p4: a run that raises `recovery_unproven` three times stays
    `recovery_unproven` and never becomes `live_route_refused`;
  - p4b: the watcher spawns once per event, 5 for 5.
- **Cost:** no paid calls in practice.
  - Most transform failures already come back as counted
    `transform_failed` refusals.
  - The only transform errors that are raised are the attempt-budget stop
    and provider refusals with HTTP 401, 402 or 403. Neither makes a billed
    call.
  - The other raises happen during replay or rollback, after the paid work
    is cached.
- **Fix:** in `maybe_route_incremental`:
  - wrap `coordinator.run()`;
  - catch an `IncrementalJsonlError` whose code is not `live_route_refused`;
  - record it with `exc.code`, using the coordinator's prefix digest or,
    failing that, the transaction's `prefix_sha256`;
  - on a repeat, raise the wedge refusal; otherwise re-raise the original
    error.

**G2 (medium): doctor's wedge WARN can never fire in production.**
- **Where:** `iter_wedged_incremental_states` reads
  `cfg["index"]["incremental_jsonl"]["state_dir"]`. The live config has the
  `incremental_jsonl` table but no `state_dir` key (I checked as booleans).
  So the coordinator uses the default
  `~/.local/share/convmem/incremental-jsonl`, and doctor finds 0 rows. The
  tests pass only because their configs set `state_dir`.
- **Repro:** p5.
- **Fix:**
  - resolve the directory with `incremental_jsonl_settings(cfg).state_dir`,
    as the coordinator does;
  - also WARN on any `transaction.json` in `APPLYING` or `PREPARING` older
    than 15 minutes. That surfaces G1-type wedges even when no retry state
    exists.

**G3 (medium, a C2 deviation): export tamper is dropped instead of refused,
and the test name says the opposite.**
- **What the code does:** `_restore_export` now `continue`s for every line
  owned by this source, whether it's allowed or not. That makes
  `_allowed_source_export_bytes` dead code: it opens a store session and the
  result is never used.
- **What the test asserts:** `test_export_tamper_still_refused` asserts that
  the tampered line is silently replaced. The handoff's C2 and test 6 said
  "refuse", and both were binding.
- **My call: accept dropping, and revise the spec.**
  - The store rollback already deletes this source's unknown rows with no
    tamper check, and the export is derived data.
  - Refusing in the export, after the store is already restored, leaves a
    half-rolled-back transaction that never recovers.
- **It must be honest and visible:**
  - delete `_allowed_source_export_bytes` and the dead branch;
  - count the source lines that are neither before-image lines nor current
    store rows. When there are any, print one line:
    `[incremental] rollback dropped N unexpected export lines for <source>`;
  - rename the test to what it checks, and assert that line;
  - the PR body names both relaxed invariants (foreign export bytes and
    tamper refusal) for Kiro's design review.

**G4 (low to medium): the watcher digests every file that's ready, even when
nothing is quarantined.**
- **Where:** `_process_ready_path` calls `source_prefix_digest_for_watch` on
  every path before it checks whether a refusal exists. Non-JSONL files are
  read whole.
- **Measured:** one parse of a synthetic 60 MiB Codex rollout took 0.26 s,
  with a 195 MiB RSS peak. The canary watcher ran at about 110 MB.
- **Fix:** compute the digest only when the breaker holds a quarantined
  `wedged_incremental_transaction_*` entry for that path.

**G5 (low; a decision, no code asked): a clean rollback quarantines the
session for good.**
- **Why:** after `rolled_back`, `maybe_route_incremental` raises
  `live_route_refused:rolled_back:…`. That isn't a wedge outcome, so the
  watcher holds the path permanently, whatever its prefix.
- **Effect:** the rollback branch of the C2 acceptance case ("roll back
  cleanly and then commit") needs `convmem watch --clear-quarantine`.
- **Recommendation:** it's burn-safe, and doctor lists it under
  `incremental_refusals`. Keep it for canary 2 and decide afterwards.

**G6 (low): the tests still don't cover the real paths.**
- Test 3 still builds the marker by hand and mocks the watcher's digest.
- **Fix:** add probes p3 and p7 from the appendix. After K1 and K2, add p4
  and p5 as passing tests.

**G7 (low): another arc's guard changed.**
- `review-bundles/` was added to the R2b writer-scan skip list. It's an
  untracked folder in Ryan's checkout.
- Fine in substance, but it changes another arc's guard, so name it in the
  PR body.

**G8 (housekeeping): main has moved.**
- `origin/main` is now `458b9f6` (#389, Safe Harbor backup binding), which
  also regenerates both writer inventories.
- Merge `origin/main` (no rebase), regenerate the inventories, and re-pin.

**A note, no change asked:** both lock paths now go through one function.
`index_write_flock_for_export` passes only the export path, so the two would
diverge only if `processed_log` and `units_export` lived in different
directories. In production they share a parent (I checked as a boolean).

## Test results (round 2)

| Run | Result |
|---|---|
| Full suite at `8a7cdab` and `117d698` | pending (68% when committed) |
| Probes p1, p2, p3, p7 | pass |
| Probes p4, p5 | fail (G1, G2) |
| Probes p4b, p6 | pass; they document current behavior (G1, G5) |
| Digest cost, synthetic 60 MiB Codex rollout | 0.26 s, 195 MiB RSS peak per parse (G4) |

## Corrective 2 for Cursor

- **K1 (G1):** count raised `IncrementalJsonlError`s in
  `maybe_route_incremental` as described. Then p4 passes.
- **K2 (G2):** doctor resolves `state_dir` the way the coordinator does, and
  WARNs on stale `APPLYING` or `PREPARING` transactions. Then p5 passes.
- **K3 (G3):** remove the dead allow-set, add the dropped-lines diagnostic,
  and rename and fix the test.
- **K4 (G4):** digest lazily, only for paths with a wedge hold, and test that
  no digest is computed when nothing is held.
- **K5 (G6):** add p3, p4, p5 and p7 from the appendix.
- **K6 (G8):** merge `origin/main`, regenerate and re-pin, and rerun the full
  suite hermetically at the merged main tip and at your tip. Report every
  test that fails only at your tip; the target is 0.
- **PR body:** the two relaxed invariants (G3 and the foreign-export
  relaxation), the G5 note and G7.

**After corrective 2:** I do a short re-verify, then Copilot audits safety
and isolation, then Kiro does the design review of C1 and C2, then Ryan
opens the PR and merges.

---

# Round 1: `da7f9a0`, FAIL (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-12
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `da7f9a0` (Cursor
Composer), against the handoff
`docs/inter-model/CURSOR-2026-10-12-issue-286-stage2-fixes-handoff.md`.
**Method:** I read the diff and ran tests hermetically: `env -i`, a scratch
`HOME` and no API keys. Nothing live was touched. Live
`processed.json`, `knowledge_units.jsonl` and `synthesis_failures.jsonl`
were unchanged by these runs, and no `index_write.lock` exists in the live
locks directory.

### Verdict

**FAIL. Return to Cursor for corrective 1 (C1–C6 below).**
- **What's right:** the lock design (C1), the watcher's intake filter (C4a)
  and the deferral logic (C4b) are sound. The replay-forward case from the
  canary now commits.
- **What blocks it, two defects:**
  1. A wedged transaction that has to *roll back* is still wedged.
  2. The bounded-retry refusal never reaches the watcher in production.

### Findings, most severe first

**F1 (high): the rollback path still pins isolation to the
transaction-start state.**
- **Where:** `incremental_jsonl.py:2109–2122`
  `_restore_replay_before_images`. It still calls
  `_verify_non_source_collections(rollback["non_source_collections"])`, the
  digest saved when the transaction began. It also runs outside
  `index_write_flock`: the rollback's store writes happen in `_roll_forward`,
  not inside `_commit_generation`.
- **Repro (hermetic, my test):**
  1. Take Cursor's test 1.
  2. Make the replay raise an `IncrementalJsonlError` after the foreign
     growth.
  3. The rollback raises `non_source_isolation_changed` at
     `incremental_jsonl.py:1499`, called from `:2119`, instead of returning
     `rolled_back`.
- **Effect:** any wedged transaction whose replay has to roll back stays
  wedged. That covers a roll-forward refusal, a rewritten source, or any
  replay error.

**F2 (high): the C3 refusal never parses in the watcher, and would never
release if it did.**
- **The parse:** `maybe_route_incremental` builds the detail
  `wedged_incremental_transaction:<code>:transaction=<id>:source=<path>:wedged
  incremental transaction; see doctor`. The CLI keeps it whole, because its
  last field isn't a 64-hex digest, and prints
  `live_route_refused:<that>`. `_parse_refusal_line` requires the outcome
  to match `[a-z0-9_]+(:[a-z0-9_]+)*`. The `=`, `/`, `.`, `-`, the spaces
  and the `;` fail that pattern, so `parse_live_route_refused` returns
  `None`. I checked this with the real format. The watcher therefore treats
  the refusal as a plain error and keeps retrying.
- **Why the test passes:** test 3 builds a synthetic marker
  (`format_live_route_refused("wedged_incremental_transaction:rollback_export_foreign_changed",
  prefix)`), so it never exercises the production string.
- **The release:** even with parsing fixed,
  `CircuitBreakerState.has_refusal_quarantine_for_path` matches any
  quarantined entry for that path, whatever its digest. Only `clear()`
  releases it. The spec says hold the path "until its prefix changes". As
  written, an active session would stay quarantined forever.

**F3 (medium): test 5 is not hermetic.**
- **Why:** `config.CONFIG_PATH` is fixed at import time, so the test's
  `monkeypatch.setenv("HOME", ...)` doesn't redirect `load_config()`.
- **Hermetically:** the test fails with "Config not found".
- **In a normal shell:** it reads the live config. The temp rollout is not
  under the live watch roots (I checked, printing booleans only), so
  nothing is deferred. The first `index --file` then calls the real
  `run_index` against the live config, before `ingest.index` is faked.
- I could not reproduce Cursor's "5/5". I found no trace of a live write.
  Set `CONVMEM_CONFIG`, or patch `config.CONFIG_PATH`, and fake
  `ingest.index` before the first invoke.

**F3b (medium): test 4 tests a copy of the handler, not the watcher.**
- `test_watcher_intake_event_types` defines its own `Handler` class inside
  the test and asserts against that copy. It never touches `watch.py`, so
  it passes at `8a7cdab`; the handoff required it to fail there.
- From reading it, the C4a code in `run_watch` looks right, but nothing
  tests it. Move the filter into a module-level function in `watch.py`
  and test that function.

**F4 (high, confirmed by existing tests): `_restore_export` refuses this
transaction's own lines, and the tamper test is missing.**
- The new check allows only *before-image* source lines. The spec also
  allows lines this transaction wrote. If `_reconcile_export` ran before the
  failure (for example, a failure in `_reconcile_dedupe`), a later rollback
  sees after-image lines and refuses them. That is a new wedge path the
  base code didn't have.
- Handoff test 6 ("tamper still refused") was not written.
- **Confirmed regression:** two reviewed rollback tests now fail with
  `rollback_export_foreign_changed: source export line is not rollback
  authority`:
  - `test_incremental_jsonl_bootstrap_safety.py::test_export_rollback_streams_foreign_bytes_and_restores_exact_order`;
  - `test_incremental_jsonl_canary_p2_runtime_readiness.py::test_r4_documented_sequence_prepare_through_t6`.

**F5 (medium): `convmem monitor` holds the store-wide lock during network
and embedding work.**
- `monitor_command` wraps all of `run_monitor`, including the HTTPS header
  fetches and the Ollama embeddings, in `index_write_flock`. Every writer,
  including the watcher, waits for the whole monitor run.
- Take the lock only around the store and export writes.

**F5a (medium): the new `load_config()` calls tie the CLI to the default
config file.**
- `index --file` (for the deferral check), `add`, `forget` and `monitor` now
  call `load_config()` with the path fixed at import.
- **Hermetically**, 31 tests fail with exit 1 ("Config not found"):
  - 26 in `test_incremental_jsonl_codex_corrective_5.py::test_c5b_every_route_outcome_round_trips_through_cli`;
  - 4 in `test_add_severity.py`;
  - test 5.
- **In a normal shell**, those tests read the live config instead.
- **Fix:** the deferral check should not hard-fail (no config means no
  deferral). Use the same config the command already uses.

**F5b (medium): dedupe persistence now needs `index.processed_log`.**
- The lock path is derived from `processed_log`, so a `cfg` without it
  raises `KeyError` at `purge_locks.py:73`.
- This breaks 4 tests in `test_ingest_dedupe.py` and
  `test_incremental_jsonl_bootstrap_safety.py::test_transaction_bound_dedupe_is_deterministic_and_idempotent`.

**F5c (medium): a refusal now writes state.**
- `maybe_route_incremental` writes `incremental_retry/<hash>.json` under the
  data root on every non-committed outcome.
- This breaks the reviewed invariant that a refusal leaves no data behind:
  `test_incremental_jsonl_live_boundary.py::test_selected_refusal_is_visible_without_legacy_fallback`
  asserts `not (tmp_path / "data").exists()`.
- Keep the retry state out of the data root, or skip it for refusals, and
  get the invariant change reviewed.

**F5d (low): the reviewed-file hash pins were not updated.**
- `test_incremental_jsonl_canary_baseline.py`,
  `test_incremental_jsonl_canary_p2_corrective.py` and
  `test_incremental_jsonl_canary_p2_runtime_readiness.py::test_c0_baseline_hashes_unchanged`
  pin `watch.py` and other files, and they now fail.
- Re-pin them on purpose and name the files in the report, so the
  reviewers see which reviewed files changed.

**F6 (low): deleted events are no longer queued.**
- The C4a filter drops `FileDeletedEvent`. My spec omitted it, so the gap is
  mine. Repository-knowledge reconcile no longer hears tracked-file
  deletions.
- Queue `deleted` events as before.

**F7 (low): the lock's identity comes from two places.**
- `index_write_lock_path(cfg)` uses the parent of `processed_log`;
  `index_write_lock_path_for_export` uses the parent of `units_export`. They
  are the same in production, but a config that splits them gets two locks,
  while the thread-local depth counter treats them as one.
- `index_write_flock` asserts lock order even when the lock is already held
  (the `_for_export` variant doesn't).

**F8 (low): unrelated removals.**
- Three explanatory comments were deleted in `ingest.py` and `convmem.py`.
- The post-apply re-check of the rollback-journal hash in
  `_commit_generation` was removed. The handoff said to keep the other
  authority checks unchanged.

### Test results

All runs are hermetic: `env -i`, a scratch `HOME` and no API keys. The
regression set is 54 test files covering add, doctor, export, incremental,
ingest, dedupe, locks, watch and the protocol, plus the new file.
`test_index_loud_failures.py` is excluded: it writes live state until
`eaae6e9` lands.

| Run | Result |
|---|---|
| Cursor's 5 new tests at `8a7cdab` | 3 fail as expected; test 5 errors on the missing config; **test 4 passes** (F3b) |
| Cursor's 5 new tests at `da7f9a0` | 4 pass; **test 5 fails** (F3) |
| Regression set at `8a7cdab` | 657 passed, 12 failed, 27 errors (all pre-existing in the hermetic environment) |
| Regression set at `da7f9a0` | 620 passed, 54 failed, 27 errors |
| **Failing only at the tip** | **42**: F4 (2), F5a (31, with test 5), F5b (5), F5c (1), F5d (3) |
| Failing only at main | 0 |
| My F1 repro (a replay error after foreign growth) | fails at the tip with `non_source_isolation_changed` |
| My F2 check (the real refusal line put through the watcher's parser) | `None` |
| Protocol tests (`test_bounded_autonomy_protocol.py`, `test_team_charter_protocol.py`) | pass |


### Corrective 1 for Cursor

- **C1:** `_restore_replay_before_images` and every rollback path run under
  `index_write_flock`. They verify isolation against a digest taken at the
  start of *this* rollback, under the lock, not the journal's digest. Add
  my repro as a test: a replay error after foreign growth must give
  `rolled_back`.
- **C2:** emit the wedge refusal as a parseable marker, for example
  `live_route_refused:wedged_incremental_transaction_<code>:<prefix_sha256>`,
  and put the transaction id and source on a separate diagnostic line.
  Release the refusal quarantine when the path's prefix digest changes.
  Test this end to end with the real CLI output, and test the release on a
  prefix change.
- **C3:** make test 5 hermetic (`CONVMEM_CONFIG` or `config.CONFIG_PATH`),
  with `ingest.index` faked before any invoke.
- **C3b:** move the C4a event filter into a module-level `watch.py` function
  that `run_watch`'s handler calls, and test it, so the test fails at
  `8a7cdab`.
- **C4:** `_restore_export` accepts before-image lines plus this source's
  current store rows as `_reconcile_export` would write them. Add test 6
  (tamper still refused) and an after-image rollback test.
- **C5:** narrow `monitor`'s lock to the store and export writes.
- **C5a:** fix F5a, F5b and F5c, and re-pin F5d on purpose. **Run the full
  suite hermetically** (`env -i`, scratch `HOME`, `CONVMEM_CONFIG` unset)
  and report every test that fails at the tip but not at `8a7cdab`. The
  target is 0.
- **C6:** queue deleted events again. Use one lock-path function. Make
  re-entry skip the order assert. Restore the removed comments and the
  journal-hash re-check.

## Appendix: round-2 probe tests

Hermetic; they ran in a detached worktree at `117d698`. Copy the ones K5 names into the suite.

<details><summary><code>tests/test_zz_claude_verify2.py</code></summary>

```python
"""Claude verify probes for issue #286 corrective 1 (117d698). Scratch only."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import json
import os
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

import convmem
import incremental_jsonl
import watch
from adapters.kiro_session_jsonl import parse_complete_prefix
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    write_source,
)
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
)
from tests.test_incremental_jsonl_live_boundary import _bootstrap_binding
from watch import CircuitBreakerState, IndexSubprocessError
from watch_circuit_breaker import parse_live_route_refused


def _enable(isolated, source: Path):
    enable_incremental(isolated)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    cfg["index"]["incremental_jsonl"].update(live_sources=[str(source)], embed_dimension=8)
    return ProductionBoundary(cfg, source, config_path=isolated.layout["user_config"]), cfg


def _wedge_then_replay(tmp_path, monkeypatch, replay_point: str):
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    source = write_source(isolated.root, 4)
    boundary, cfg = _enable(isolated, source)
    digest = parse_complete_prefix(str(source)).prefix_sha256
    common = dict(
        cfg=cfg,
        bootstrap_existing=True,
        expected_prefix_sha256=digest,
        max_bootstrap_chunks=4,
        chunk_size=2,
        **_bootstrap_binding(),
    )

    def first_crash(point: str) -> None:
        if point == "after_summary_upsert":
            raise RuntimeError("initial partial apply")

    first = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, processed={"old-hash": {"path": str(source)}},
        fault=first_crash, **common,
    )
    with first._session() as session:
        session.store.add_summary("legacy-summary", "old", [0.1] * 8, {"source_path": str(source)})
        session.store.add_unit("legacy-unit", "old", [0.1] * 8, {"source_path": str(source)})
    with pytest.raises(RuntimeError, match="initial partial apply"):
        first.run()
    # Another source indexes between attempts: store row and export line.
    with first._session() as session:
        session.store.add_summary("foreign-summary", "foreign", [0.1] * 8, {"source_path": "/other"})
    export_path = Path(cfg["index"]["units_export"])
    export_path.parent.mkdir(parents=True, exist_ok=True)
    foreign_line = json.dumps({"id": "foreign-unit", "source_path": "/other"}) + "\n"
    with export_path.open("a", encoding="utf-8") as handle:
        handle.write(foreign_line)

    def replay_fault(point: str) -> None:
        if point == replay_point:
            raise incremental_jsonl.IncrementalJsonlError("synthetic_replay_fault", "forced")

    replay = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, fault=replay_fault, **common
    )
    return replay, export_path, foreign_line, source


def test_p1_rollback_after_foreign_growth(tmp_path, monkeypatch) -> None:
    replay, export_path, foreign_line, _src = _wedge_then_replay(
        tmp_path, monkeypatch, "after_summary_upsert"
    )
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert not replay.paths["transaction"].exists()
    assert foreign_line.encode() in export_path.read_bytes()


def test_p2_rollback_after_export_already_rewritten(tmp_path, monkeypatch) -> None:
    # F4 scenario: _reconcile_export ran, then the replay fails before dedupe.
    replay, export_path, foreign_line, _src = _wedge_then_replay(
        tmp_path, monkeypatch, "before_dedupe_reconcile"
    )
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert foreign_line.encode() in export_path.read_bytes()


def _codex_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    return source, cfg


def _route(cfg, source):
    return incremental_jsonl.maybe_route_incremental(
        cfg=cfg, idx=cfg["index"], path=str(source), path_key=str(source),
        file_hash="h", processed={}, models=cfg["models"], tool="codex",
        units_export=Path(cfg["index"]["units_export"]), chunk_size=4, overlap=0,
        min_confidence=0.0, force_reindex=False, supersede_on_reindex=False,
        verbose=False, detected_format="jsonl_codex_rollout",
    )


def test_p3_real_wedge_marker_through_cli_parses(tmp_path, monkeypatch) -> None:
    source, cfg = _codex_env(tmp_path, monkeypatch)
    digest = "c" * 64

    def failing_run(self):
        self.last_failure_code = "rollback_export_foreign_changed"
        self.last_evidence["prefix_sha256"] = digest
        tx = self.paths["transaction"]
        tx.parent.mkdir(parents=True, exist_ok=True)
        tx.write_text(json.dumps({"transaction_id": "a" * 32}), encoding="utf-8")
        return self._refusal("rolled_back")

    monkeypatch.setattr(incremental_jsonl.IncrementalJsonlCoordinator, "run", failing_run)
    with pytest.raises(incremental_jsonl.IncrementalJsonlError):
        _route(cfg, source)
    with pytest.raises(incremental_jsonl.IncrementalJsonlError) as second:
        _route(cfg, source)
    assert second.value.code == "live_route_refused"

    def raising_index(**_kwargs):
        raise second.value

    import ingest
    monkeypatch.setattr(ingest, "index", raising_index)
    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    result = CliRunner().invoke(convmem.app, ["index", "--file", str(source), "--now"])
    stderr = getattr(result, "stderr", "") or result.output
    assert result.exit_code == 91, (result.exit_code, stderr)
    parsed = parse_live_route_refused(stderr)
    assert parsed == (
        "wedged_incremental_transaction_rollback_export_foreign_changed", digest
    ), stderr
    assert "a" * 32 in stderr and str(source) in stderr


def test_p4_raised_rollback_error_is_never_counted(tmp_path, monkeypatch) -> None:
    """C3 backstop: an error raised out of run() (e.g. by the rollback) repeats forever."""
    source, cfg = _codex_env(tmp_path, monkeypatch)

    def raising_run(self):
        raise incremental_jsonl.IncrementalJsonlError("recovery_unproven", "rollback failed")

    monkeypatch.setattr(incremental_jsonl.IncrementalJsonlCoordinator, "run", raising_run)
    codes = []
    for _ in range(3):
        with pytest.raises(incremental_jsonl.IncrementalJsonlError) as exc:
            _route(cfg, source)
        codes.append(exc.value.code)
    # Expected by C3: the second identical failure becomes live_route_refused (exit 91).
    assert codes[1] == "live_route_refused", codes


def test_p4b_watcher_retries_plain_errors_forever(tmp_path, monkeypatch) -> None:
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    spawns = 0

    def fake_flush(_path, **_kwargs):
        nonlocal spawns
        spawns += 1
        raise IndexSubprocessError("recovery_unproven", returncode=1, stderr="Error: recovery_unproven\n")

    monkeypatch.setattr(watch, "flush_path", fake_flush)
    monkeypatch.setattr(watch, "source_prefix_digest_for_watch", lambda _p: "f" * 64)
    for _ in range(5):
        watch._process_ready_path("/x/rollout.jsonl", cfg={}, breaker=breaker, verbose=False)
    assert spawns == 5  # never bounded


def test_p5_doctor_wedge_check_with_default_state_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    from config import DEFAULT_INCREMENTAL_JSONL_STATE_DIR
    from incremental_retry_state import iter_wedged_incremental_states

    state_root = Path(os.path.expanduser(DEFAULT_INCREMENTAL_JSONL_STATE_DIR))
    (state_root / "src1").mkdir(parents=True)
    (state_root / "src1" / "retry_state.json").write_text(
        json.dumps({"source": "/s", "transaction_id": "t", "error_code": "e",
                    "prefix_digest": "d", "consecutive": 2}),
        encoding="utf-8",
    )
    cfg = {"index": {"incremental_jsonl": {"enabled": True, "embed_dimension": 8}}}
    # Live config has an incremental_jsonl table and no state_dir key.
    assert iter_wedged_incremental_states(cfg), "doctor misses the default state dir"


def test_p6_rolled_back_refusal_holds_forever(tmp_path) -> None:
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    breaker.record_refusal("/x/r.jsonl", outcome="rolled_back", prefix_digest="a" * 64)
    assert breaker.should_skip_refusal_quarantine("/x/r.jsonl", "b" * 64)



def test_p7_watcher_digest_matches_coordinator_digest(tmp_path, monkeypatch) -> None:
    from tests.test_incremental_jsonl_codex_rollout_route import _write_user_config
    from adapters.detect import detect_format

    source, cfg = _codex_env(tmp_path, monkeypatch)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    install_fakes(monkeypatch)
    assert detect_format(str(source)) == "jsonl_codex_rollout"
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    coord = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, cfg=cfg, enabled=True, chunk_size=4, overlap=0,
        min_confidence=0.6, embed_dimension=8, processed={},
    )
    result = coord.run()
    assert result.outcome == "committed"
    coordinator_digest = coord.last_evidence.get("prefix_sha256")
    watcher_digest = watch.source_prefix_digest_for_watch(str(source))
    assert coordinator_digest and watcher_digest == coordinator_digest, (
        watcher_digest, coordinator_digest)
```

</details>
