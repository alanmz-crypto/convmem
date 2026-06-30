# Milestone F — Always-on index refinement

**Status:** Greenlit (Kiro sign-off) — **F0 first**, then **F1**  
**Orchestration:** Sonnet  
**Review:** Kiro  
**Implement:** Builder  
**Read/plan:** Cursor (does not write ledger)

All decisions in this document are **final**. Do not reopen architecture questions from Milestones A–E.

---

## Purpose

Use always-on compute to **refine** the index over time — not just cron `index`. Today ingest is append-and-skip (`processed.json` hash); ~1470 legacy units lack `domain`; twin Chroma UUIDs can share one `ledger_id`. F closes that gap incrementally without blocking interactive `ask`.

**Single writer:** One machine owns `~/.local/share/convmem/chroma/`. `watch.lock` / `refine.lock` prevent duplicate daemons. Do not rsync the corpus to another host while services run (`dec_convmem_single_writer_chroma`).

---

## Phasing

| Phase | Deliverable | Notes |
|-------|-------------|-------|
| **F0** | `convmem watch` | inotify → `index --file`; validates always-on deployment **before** F1 |
| **F1** | `convmem refine` | Job queue + daemon; jobs below |
| **F2a** | Store API + citation dedupe | See [`F2a-SCOPING.md`](F2a-SCOPING.md) — Builder brief |
| **F2b** | `convmem monitor` | ✅ — see [`F2b-MONITOR-POLICY.md`](F2b-MONITOR-POLICY.md) |
| **F2c** | Crush adapter | Done — [`F2c-CRUSH-ADAPTER.md`](F2c-CRUSH-ADAPTER.md) |
| **v1.1** | `domain_drift_detect` | **Not F1** — monthly mis-classification spot-check |

---

## F0 — `watch` ✅ signed off

Verified: code review, 37/37 tests, live smoke (`--debounce 2 --path <tmpdir> --no-lock`).

| Criterion | Status |
|-----------|--------|
| inotify + debounce + `index --file` | ✅ |
| `[watch].debounce_seconds = 30` | ✅ |
| PID lock (`watch.lock`, stale/live PID) | ✅ |
| `is_indexable()` via `get_parser` | ✅ |
| CLI `convmem watch` | ✅ |
| 9 watch tests | ✅ |
| systemd example + inotify sysctl notes | ✅ |
| `watchdog` in requirements | ✅ |

```bash
pip install watchdog
convmem watch
```

**Known F0 follow-ups (non-blocking):** lock unit tests deferred to F1 (`refine.lock` shares pattern); Kiro sqlite parent-dir watch coalesced by debounce.

---

## F1 — Job order (strict)

Run jobs in this order when enabling defaults. Later jobs depend on earlier cleanup.

| # | Job | LLM | Notes |
|---|-----|-----|-------|
| 1 | `chroma_dedupe` | No | Tombstone twin UUIDs (same `ledger_id`); idempotent |
| 2 | `backfill_domain` | Yes (cheap) | Metadata-only: `domain` + `updated_at` only |
| 3 | `ledger_link` | Maybe | Cluster by site + summary; needs domains |
| 4 | `semantic_dedupe` | Yes | Pairs → `dedupe_queue.jsonl`; **no auto-merge** |
| 5 | `confidence_audit` | No | Histogram to `refine_stats.json`; **gates redistill** |
| 6 | `redistill` | Yes (expensive) | Last; only after audit reviewed + stats key present |

**Additional F1 helpers (no separate milestone):**

- `stale_source_flag` — if source file missing, mark `source_available: false`; do not queue redistill

**Explicitly not F1:** `domain_drift_detect` (v1.1)

---

## Tombstone implementation (locked)

Duplicate / orphan units are **not deleted** in F1.

- Set Chroma metadata: `superseded: true`, `superseded_by: <canonical_uuid>`
- **Single filter point:** `chroma_store.units_metadata(include_superseded=False)` — default `False`
- Every read path inherits via this method; no per-query filter duplication
- **Backward compatibility (Kiro):** New parameter must default `include_superseded=False`. All existing callers pass no args today → **zero call-site changes required**. Builder must verify all call sites before ship.
- **`--prune` (physical delete):** Deferred; requires explicit Kiro decision before exposing

### `chroma_dedupe` behavior

- For each `ledger_id` with multiple UUIDs: keep one canonical row (newest / highest confidence — document rule in code)
- Tombstone orphans with `superseded_by` pointing at canonical UUID
- Idempotent: re-run produces zero new tombstones

### Tombstone filter spec addendum (F1 — required before ship)

Chroma has no native “exclude by metadata” on vector query. Filtering must be **centralized in `chroma_store.py`**, not duplicated in `query.py` / `ask.py` / `ledger.py`.

**Helper (internal):**

```python
def is_superseded(meta: dict) -> bool:
    return meta.get("superseded") is True
```

**Per-method contract:**

| Method | `include_superseded` default | Behavior |
|--------|------------------------------|----------|
| `units_metadata()` | `False` | Return metadatas; exclude tombstones unless `True`. Used by `build_ledger_index()`, stats, refine jobs. |
| `query_units(embedding, top_k, …)` | `False` | Post-filter superseded rows from Chroma results. If filtering drops below `top_k`, over-fetch (e.g. `top_k * 3`) then filter — same pattern as domain filter in `query.py`. |
| `count_units()` | `False` | Count non-superseded only; `convmem stats` reflects visible corpus. |
| `get_unit(unit_id)` | *(no param)* | **Always return** the row if the id exists, including tombstones. Required for `verify`, `related`, refine undo, and explicit id lookup. |

**Call-site rules:**

- **Zero changes** to existing callers that use defaults (`units_metadata()`, `count_units()`, `query_units` via `query.py`).
- **Refine jobs** (`chroma_dedupe`, rollback) call `units_metadata(include_superseded=True)` when they must see twins/tombstones.
- **`query.py`** continues to call `store.query_units`; filtering lives in the store wrapper, not in `query_units()` free function.
- **`ledger.build_ledger_index()`** uses `units_metadata()` → tombstones excluded from evidence graph and `--evidence` rerank by default (canonical row remains).

**Metadata fields (locked):**

- `superseded: true` on tombstone row
- `superseded_by: <canonical_chroma_uuid>` on tombstone row
- Canonical row: no `superseded` field (or `false`)

**Tests required:**

- Tombstoned unit absent from `query_units` / `count_units` / `units_metadata()` default
- Same unit returned by `get_unit(tombstone_uuid)`
- `chroma_dedupe` with `include_superseded=True` sees twins

---

## Rollback (locked)

Every **mutating** job writes a before-snapshot **before** any write:

```
refine_undo/<job>/<timestamp>.jsonl
```

- One JSON line per touched unit (full metadata prior to change)
- Must include `superseded_by` when tombstoning (for `chroma_dedupe` undo)
- Tombstone rollback = metadata restore, not delete/recreate

---

## `confidence_audit` gate (locked)

- `confidence_audit` writes histogram to `refine_stats.json` (no Chroma writes)
- **`redistill` hard gate:** `sys.exit(1)` if `"confidence_audit"` key absent from `refine_stats.json`
- Message: `redistill requires confidence_audit to have run first. Run: convmem refine --once --job confidence_audit`
- **No `--force` override in v1**
- **Do not enable `redistill` in default `[refine] jobs=`** until audit has run once and histogram reviewed

---

## Job policies

### `backfill_domain`

- Input: units with empty/missing `domain` (~1470 legacy)
- LLM classify from `title` + `summary` only — **not** full re-distill
- Writes **only** `domain` and `updated_at`
- **Do not touch `processed.json`**

### `ledger_link`

- Link wp-sec vs manual anchors (same site + finding)
- Writes `relates_to` or decision stub per existing exchange schema
- **Do not touch `processed.json`**

### `semantic_dedupe`

- Embedding similarity > threshold (config, e.g. 0.92) → queue candidate pair
- **F1-lite:** queues on embedding similarity only (no LLM verdict pass yet)
- Uses `get_units_with_embeddings()` on `ChromaStore` (F2a)
- Kiro approves: `convmem refine --approve-dedupe <id>` (implement in F1)
- **No auto-merge in v1** — no `--auto-merge-above` until calibrated post-Kiro batches
- Pause job if `queue_max_depth` exceeded (config)

### `redistill`

- Re-run `distill()` on source chunk when available
- **`processed.json`:** only this job may touch it — **per-unit hash**, never bulk clear
- Gated on `confidence_audit` as above

---

## Config sketch

```toml
[refine]
enabled = true
batch_size = 10
interval_seconds = 300
idle_only = true
jobs = ["chroma_dedupe", "backfill_domain", "ledger_link", "semantic_dedupe"]
# Do NOT include redistill until confidence_audit reviewed
untagged_priority = true
queue_max_depth = 100

[refine.cost]
backfill_domain_calls_per_hour = 60
redistill_calls_per_hour = 15
semantic_dedupe_calls_per_hour = 20
```

---

## CLI (target)

```bash
convmem watch                          # F0 daemon
convmem refine                         # F1 daemon loop
convmem refine --once --job chroma_dedupe --limit 20
convmem refine --once --job confidence_audit
convmem refine --stats                 # JSON: per-job counts, llm_calls, errors
convmem refine --approve-dedupe <id>   # after Kiro review of queue
```

---

## Success metrics (F1)

Track in `refine_stats.json`:

| Metric | Target |
|--------|--------|
| Untagged units (`convmem stats`) | <5% after backfill pass |
| Duplicate citations in `ask --evidence` | Measurable drop vs pre-F1 baseline |
| `dedupe_queue.jsonl` drain | Kiro reviews within agreed window |
| Refine errors/hour | <1% of batches |
| LLM calls/hour | Never exceed per-job caps (hard stop) |

---

## Acceptance criteria (Builder)

- [x] F0: signed off (see F0 section above)
- [x] Tombstone filter spec addendum implemented in `chroma_store.py`
- [x] `units_metadata()` binds authoritative Chroma id (fixes legacy metadata.id mismatch)
- [x] `chroma_dedupe` idempotent on live index (2nd pass `tombstoned: 0`)
- [x] `refine --stats` emits JSON via `refine_stats.json`
- [x] `redistill` exits 1 without prior `confidence_audit`
- [ ] `refine --once --job backfill_domain --limit 10` on live corpus (<60s) — run manually
- [x] Kiro sign-off on F1 (2026-06-18)

---

## Do not do (F0/F1)

- Touch `processed.json` in any job **except** `redistill` (per-unit hash only)
- Auto-merge semantic duplicates
- Implement `--prune` or `--force` in F1
- Enable `redistill` in default job list until `confidence_audit` has run and been reviewed
- Second Chroma writer or shared mount without lock documentation
- New repo or exchange JSONL schema changes for producers
- Implement `domain_drift_detect` (v1.1)
- Supersede Kiro-authored verifications (F2 concern)

---

## Context — prior milestones (signed off)

| Milestone | Summary |
|-----------|---------|
| A | Observer path — `ledger.py`, `observe.py`, exchange JSONL |
| B | `convmem related`, `build_ledger_index()` |
| C | Stable ids, `add --upsert`, `ingest-*.sh`, `run.sh --upsert` |
| E | `evidence.py`, `ask --evidence` |
| D | OpenClaw — deferred |

**Logged non-blockers (separate from F):** post-rerank `ledger_id` dedupe in `ask.py` for duplicate citations.

---

## Agent roles

| Agent | F0/F1 role |
|-------|------------|
| **Builder** | Implements watch + refine |
| **Kiro** | Sign-off, dedupe queue approval, no `--prune` until explicit |
| **Sonnet** | Orchestration (this plan) |
| **Cursor** | Verify PRs against this doc; read-only on ledger |
| **Tools** | Unchanged — wp-sec / Lighthouse → `add --upsert` |

**First site:** `staging2.willowyhollow.com`

---

## Files (expected)

| File | Phase |
|------|-------|
| `watch.py` | F0 |
| `refine.py` | F1 |
| `convmem.py` | `watch`, `refine` subcommands |
| `chroma_store.py` | `units_metadata(include_superseded=…)`, optional `update_unit` for upsert paths |
| `config.example.toml` | `[refine]`, `[refine.cost]` |
| `tests/test_refine.py`, `tests/test_watch.py` | F0/F1 |
| `systemd/convmem-watch.service.example` | F0 ops |

---

*Last updated: 2026-06-17 — Kiro greenlit F0 → F1.*
