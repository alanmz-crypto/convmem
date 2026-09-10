# VERIFY — Kiro JSONL Incremental Production Integration

**Arc:** Codex

**Date:** 2026-09-10

**Lane:** Cursor Execute T0–T6

**Branch:** `feat/2026-09-10-codex-jsonl-production-integration`

**Implementation commit:** `5341bb11e274ed1950db11a6b8bc45d5047ef9b6`

**VERIFY document commit:** `4dfe42eb484808bbbdb2fbe974713fc18ba51e84`

**Kiro review tip:** `git fetch origin feat/2026-09-10-codex-jsonl-production-integration && git rev-parse origin/feat/2026-09-10-codex-jsonl-production-integration`

**PR:** not opened

---

## Disposition

Hermetic T0–T6 implementation evidence is complete on the feature branch.
The feature remains **disabled by default**. This is not production PASS, not
activation, and not authorization to open a PR.

Kiro must independently reproduce the commands below at the exact fetched tip.

## What this evidence is

| Class | Status |
|---|---|
| Default-off production-code evidence | PASS in this Execute |
| Hermetic real-Chroma integration evidence | PASS (temporary isolated roots only) |
| Inherited scratch / live-source canary evidence | Scratch isolation + engine regressions PASS; scratch Chroma `-I` workers not reproduced on this VM (incident below) |
| Live source / production corpus / providers / watcher / activation / golden eval | **Not run** |

## Exact commands and counts

Working directory: repository root. Interpreter: `/usr/bin/python3` 3.12.
Chroma and pytest live in the host user site
(`/home/ubuntu/.local/lib/python3.12/site-packages`). Crash workers use
`python -I` plus `CONVMEM_INCREMENTAL_SITE` so that isolated processes can
import Chroma without `PYTHONPATH` (ignored under `-I`).

### 1. New isolation / config / state tests

```bash
python3 -m pytest -q --tb=line \
  tests/test_incremental_jsonl_isolation.py \
  tests/test_incremental_jsonl_config.py \
  tests/test_incremental_jsonl_state.py
```

Observed: **75 passed** in 123.32s (5 isolation + 9 config + 61 state).
State includes **44** both-side crash tests (`22` durable transitions ×
`before_`/`after_`).

### 2. Focused compatibility regressions

```bash
python3 -m pytest -q --tb=line \
  tests/test_kiro_session_jsonl.py tests/test_config.py \
  tests/test_shadow_writer_coverage_scan.py \
  tests/test_shadow_writer_gate_c3.py \
  tests/test_r2b_v2_implementation_revision.py \
  tests/test_r2b_v2_coverage.py \
  tests/test_source_purge_locks.py \
  tests/test_exclude_source_purge.py \
  tests/test_processed_exclude_race.py \
  tests/test_scratch_jsonl_isolation.py \
  tests/test_scratch_jsonl_incremental.py
```

Observed: **155 passed** (8 + 49 + 46 + 52), plus 8 subtests on exclusion.

Watch and safe-reindex on this VM have no default
`~/.config/convmem/config.toml`. They were run with a **temporary** config
under `/tmp/convmem-jsonl-verify-watch/config.toml` via `CONVMEM_CONFIG`.
That path is not the production config location. Live
`~/.config/convmem/config.toml` was not created or edited.

```bash
CONVMEM_CONFIG=/tmp/convmem-jsonl-verify-watch/config.toml python3 -m pytest -q --tb=line \
  tests/test_watch.py tests/test_watch_skip.py \
  tests/test_watch_subprocess_memcap.py tests/test_safe_file_reindex.py
```

Observed: **48 passed**.

### 3. Static checks

```bash
python3 -m compileall -q adapters/kiro_session_jsonl.py chroma_store.py \
  config.py incremental_jsonl.py incremental_jsonl_isolation.py ingest.py \
  eval_corpus/r2b_v2/coverage/inventory.py \
  tests/incremental_jsonl_helpers.py \
  tests/incremental_jsonl_isolation_worker.py \
  tests/test_incremental_jsonl_config.py \
  tests/test_incremental_jsonl_isolation.py \
  tests/test_incremental_jsonl_state.py \
  tests/test_shadow_writer_gate_c3.py
```

Observed: exit 0.

```bash
PYLINTHOME=/tmp/pylint-jsonl python3 -m pylint \
  adapters/kiro_session_jsonl.py chroma_store.py config.py \
  incremental_jsonl.py incremental_jsonl_isolation.py ingest.py \
  tests/incremental_jsonl_helpers.py \
  tests/incremental_jsonl_isolation_worker.py \
  tests/test_incremental_jsonl_config.py \
  tests/test_incremental_jsonl_isolation.py \
  tests/test_incremental_jsonl_state.py
```

Observed: **9.86/10**. Remaining findings are duplicate-code (fakes and
keyword forwarding) and the existing ingest↔coordinator import cycle
(`ingest` imports `maybe_route_incremental` lazily).

```bash
git diff --check
```

Observed: clean.

## Durable transitions

Single inventory in `incremental_jsonl.DURABLE_TRANSITIONS` (22 names).
Tests generate `before_<name>` and `after_<name>` for each. Coverage fails
if the tuple and the parametrize set disagree.

```text
source_snapshot_prepare
source_snapshot_publish
source_revalidate
transaction_prepare
transaction_phase_publish
prepared_output_prepare
prepared_output_publish
rollback_prepare
rollback_publish
summary_upsert
unit_upsert
summaries_prune
units_prune
checkpoint_prepare
checkpoint_publish
export_reconcile
dedupe_reconcile
processed_publish
transaction_cleanup
snapshot_cleanup
lock_acquire
lock_release
```

Crash worker exit code **86**. Replay outcomes observed:
`committed`, `unchanged` (and allowed `rolled_back` / `source_moved` /
`bootstrap_required`). After `after_prepared_output_publish`, a fresh
process completed with **zero** summarize/distill/summary-embed/unit-embed
calls.

## Call counters (hermetic fakes)

| Case | Result |
|---|---|
| Disabled / missing table | coordinator not constructed; zero calls |
| Initial 4-message index | summarize > 0 |
| Unchanged replay | `outcome=unchanged`, counters.total == 0 |
| Append after 20 messages (chunk 8 / overlap 2) | 0 < summarize < baseline |
| 1000-message baseline then one append (chunk 20 / overlap 2) | baseline summarize > 40; append summarize < 4; reused_artifacts ≥ baseline − 3 |
| Force / supersede | `incremental_force_unsupported`, zero writes |
| Processed-without-checkpoint | `bootstrap_required`, zero calls |
| Prefix mutation without rebuild permission | `rebuild_required:validated_prefix_mutated`, zero calls |

## Authority equality (A5)

`test_incremental_equals_clean_rebuild` compares both Chroma collections
and checkpoint identity fields **without** dropping IDs, documents,
embeddings, metadata, or provenance.

Ingest now mints RFC 4122 UUID4 assertion IDs from a SHA-256 of the chunk
locator and unit payload so a clean rebuild of the same prefix reproduces
the same provenance envelope. Provenance mint still assigns UUID4; callers
still cannot supply an assertion id.

## Isolation proof (A12)

- Fresh tokenized roots; HOME/XDG relocated; production roots rejected
  before construction.
- Probe worker: network `IsolationViolation`, watcher
  `IsolationViolation`, no inherited sentinel fds, no credentials, no
  `CONVMEM_*` production overrides.
- Isolation module AST: stdlib only (`site` is stdlib, used to locate the
  host third-party install for `-I` workers).
- Fake summarize/distill/embed only. Models in hermetic config are
  `deterministic-fake`.
- Crash workers: `python -I`, `close_fds=True`, new session, exit 86,
  kernel flock release on death.

## Writer inventories (A11)

Scanned `production_chroma_write_session` sites now include
`incremental_jsonl.py:506`. C3 session+open total **16**. R2b inventory
regenerated with `write_v2_inventory_file()` (revision
`0dc88ae39648e87c12c6d973aa6058fc6ab0ab23`, digest
`4773c4e1fd2c6f28b8dfd95e6a80fad0293ac2a9326e0b87b060844b04dac84a`).
Revision digests were not hand-edited.

## Limits disclosed for Kiro question 6

- Chroma still has no atomic two-collection transaction. The before-image
  journal can roll forward or restore; mixed-read visibility during apply
  is **not** claimed solved.
- The selected complete prefix is materialized. Transformed-output
  residency is bounded by units-in-flight; this is **not** a
  constant-memory parser or watcher RSS claim.

## Live-activation fail-closed note

`maybe_route_incremental` constructs the coordinator only when
`CONVMEM_INCREMENTAL_ROOT` is set (hermetic Execute). If the flag is true
outside that boundary, eligible Kiro files are skipped rather than writing
production state. A later activation grant must replace that refuse with
the real coordinator against live config. Default-off remains a true no-op
(`None`, no coordinator).

## Incidents

1. **`python -I` drops user site.** Incremental crash workers receive
   `CONVMEM_INCREMENTAL_SITE`. Unmodified scratch Chroma `-I` workers on
   this Cloud VM fail with `ModuleNotFoundError: chromadb` for the same
   reason. Those scratch tests were not edited. Original scratch VERIFY
   used a conda interpreter whose site-packages remain visible under `-I`.
2. **No default convmem config on this VM.** Watch/safe-reindex were run
   with a temporary `CONVMEM_CONFIG` under `/tmp`. Production
   `~/.config/convmem/config.toml` was not created or modified.
3. **`convmem` CLI is not installed here.** Execute already prohibits
   Track A `convmem index`.
4. **Pylint exit status 28** with score 9.86/10 (duplicate-code +
   cyclic-import). No new fail-closed defects.

## Work not run

- live Kiro transcripts, production Chroma, processed.json, exports,
  locks, attestations, census
- `convmem index` / `add` / `verify`
- watcher start/stop/reload
- local, network, or paid providers
- golden evaluation / unscoped repo-wide suite
- bootstrap, canary, activation, PR creation
- scratch `tests/test_scratch_jsonl_chroma.py` and live-source canary
  **subprocess** workers on this VM (see incident 1)

## Scope audit

Changed production/test/inventory surfaces match the Execute grant:
`config.py`, `config.example.toml`, `incremental_jsonl.py`,
`adapters/kiro_session_jsonl.py`, `ingest.py`, `chroma_store.py`
(snapshot/restore only), isolation helpers, focused tests, C3/R2b
inventories, and T6 documents. `watch.py` is unchanged.

## Artifact logs

- `/opt/cursor/artifacts/incremental-jsonl-t0-t4-pytest.log`
- `/opt/cursor/artifacts/incremental-jsonl-t5-focused-pytest.log`
- `/opt/cursor/artifacts/incremental-jsonl-static-checks.log`
