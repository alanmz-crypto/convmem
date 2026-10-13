# Verify: Stage 2 wedge fixes at `da7f9a0`, FAIL with correctives

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

## Verdict

**FAIL. Return to Cursor for corrective 1 (C1–C6 below).**
- **What's right:** the lock design (C1), the watcher's intake filter (C4a)
  and the deferral logic (C4b) are sound. The replay-forward case from the
  canary now commits.
- **What blocks it, two defects:**
  1. A wedged transaction that has to *roll back* is still wedged.
  2. The bounded-retry refusal never reaches the watcher in production.

## Findings, most severe first

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

## Test results

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


## Corrective 1 for Cursor

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
