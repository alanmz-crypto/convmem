# Execution Plan — Exclude Source Purge

```
Planning Status

Phase:        Execution Planning — awaiting HITL before Execute
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Cursor (Tier A implementation); Kiro (design/sign-off)
Authority:    Architecture gates 1–12 proposed 2026-07-14 (amended); awaiting Ryan acceptance
```

**Architecture SSoT:** [`ARCHITECTURE-exclude-source-purge.md`](ARCHITECTURE-exclude-source-purge.md)
**Branch:** `plan/2026-07-14-exclude-source-purge`
**Worktree:** `~/.local/share/convmem/worktrees/plan-2026-07-14-exclude-source-purge`

---

## Gate decisions (proposed — awaiting HITL)

| # | Choice |
|---|--------|
| 1 | --purge = logical removal from active derived stores (not tombstone, not forensic erasure) |
| 2 | Three sinks: Chroma units, Chroma summaries, knowledge_units.jsonl. Postcondition verifies zero. |
| 3 | Per-source advisory flock; fresh exclusion check before each derived-write batch; no lock during LLM/embed (tested) |
| 4 | Export lock derived from configured units_export path; all six JSONL writers use it |
| 5 | Exact canonical path via shared path-candidate builder; no cwd canonicalization of empty/non-filesystem values |
| 6 | Marker-first crash recovery; expanded failure injection at every step; partial purge stays excluded, nonzero |
| 7 | --undo re-enables ingest only; cannot resurrect purged rows |
| 8 | Read-only preview (separate function); confirmation/--yes in thin CLI only; never print payloads |
| 9 | Malformed JSONL lines fail closed; no undo artifacts with purged content |
| 10 | Deterministic tests: both interleavings, all failure injection points, lock ordering, no-lock-during-LLM, alternate-data-root, missing-file, postcondition |
| 11 | Superseded-count cache invalidated after hard unit deletion |
| 12 | Source lock identity derived from configured data root (not hardcoded) |

---


## Tasks

| ID | Deliverable | In scope | Depends on | Gates |
|----|-------------|----------|------------|-------|
| T1 | Source lock module | `source_flock(cfg, canonical_path)` context manager; lock path from SHA-256 of path under data-root `locks/source/`; lock dir creation; ordering assertion helper; config-derived identity (not hardcoded) | — | pytest |
| T2 | Export lock module | `export_flock(cfg)` context manager; lock path = sidecar of configured `units_export`; ordering assertion | T1 | pytest |
| T3 | Path-candidate builder | `build_path_candidates(target) -> list[str]`; `line_matches_purge(rec, candidates) -> bool`; skips empty/non-filesystem/`ledger:*` values; no cwd canonicalization | — | pytest |
| T4 | JSONL purge function | `purge_source_from_jsonl(export_path, candidates) -> int`; acquires export lock internally; atomic tmp+rename; exact-path match via path-candidate builder; fail-closed on malformed lines; returns lines removed | T2, T3 | pytest |
| T5 | Chroma purge function | `purge_source_from_chroma(store, candidates) -> dict`; deletes from both collections via candidate list; calls `invalidate_superseded_cache`; returns `{units_deleted, summaries_deleted}` | T3 | pytest |
| T6 | Preview function | `preview_purge(cfg, canonical_path) -> PurgePreview`; read-only; opens Chroma read-only; counts from JSONL via path candidates; no locks; no mutations | T3, T5 | pytest |
| T7 | Purge orchestrator | `execute_purge(cfg, canonical_path, reason) -> PurgeResult`; acquires source lock → marks exclusion (handles missing-file key) → Chroma purge → JSONL purge → postcondition check → returns exit status | T1–T6 | integration |
| T8 | CLI integration | Wire `--purge` and `--yes` into `exclude_command`; calls preview then execute; confirmation prompt in CLI only; output formatting; exit codes; handles missing-file warning | T6, T7 | CLI test |
| T9 | Ingest lock integration | Modify ingest batch-write to: acquire source flock + re-check exclusion before Chroma upsert; acquire export flock before JSONL append; verify no lock held during parse/LLM/embed | T1, T2 | pytest + existing tests pass |
| T10 | Inter-model index integration | Same source flock + export flock pattern for `inter_model_index.py` batch write | T9 | pytest |
| T11 | Observe.py export lock | All `observe.py` JSONL writers (`ingest_observation` append, `_upsert_jsonl_line` rewrite) acquire export flock | T2 | pytest |
| T12 | Deduplicate export lock | `_deduplicate_units_export` acquires export flock | T2 | pytest |
| T13 | Acceptance test suite | All named tests N1–N19; deterministic race tests using threading barriers; failure injection | T7–T12 | pytest |
| T14 | Commit + push | Explicit refspec; CI green | T1–T13 | remote |

---

## Named Tests Required

| Test ID | Requirement | Maps to |
|---------|-------------|---------|
| N1 | Purge-then-ingest interleaving: ingest starts, purge completes, ingest batch-write finds path excluded and aborts — no orphan Chroma rows | T9, T13 |
| N2 | Ingest-then-purge interleaving: ingest batch-write completes, purge runs — all three sinks reach zero (postcondition passes) | T7, T13 |
| N3 | Unrelated export append preserved: purge rewrite of source A does not corrupt source B lines; concurrent append for source B survives via export lock serialization | T4, T13 |
| N4 | Exact-path boundary: similar paths (`/a/b.jsonl` vs `/a/b.jsonl.bak`, `/a/b.jsonl` vs `/a/b.jsonl2`) not confused | T3, T5, T13 |
| N5 | Partial failure + retry idempotency: purge crashes after Chroma delete but before JSONL rewrite; retry converges to zero (postcondition passes) | T7, T13 |
| N6 | Dry-run / decline: preview queries sinks and displays counts without any mutation; declining leaves all data intact | T6, T8, T13 |
| N7 | Inter-model doc indexing: purge removes units created via `inter_model_index.py` (source_type=inter_model_doc) | T5, T10, T13 |
| N8 | All three sinks reach zero: after purge, Chroma query returns empty; JSONL has zero matching lines; postcondition exit 0 | T7, T13 |
| N9 | Lock ordering violation: acquiring source lock while holding export lock raises/asserts | T1, T2, T13 |
| N10 | Malformed JSONL line: purge aborts rewrite, original file unchanged, nonzero exit | T4, T13 |
| N11 | --yes skips confirmation: purge proceeds without interactive prompt | T8, T13 |
| N12 | --undo after purge: exclusion cleared, sinks still empty, re-index required for data | T8, T13 |
| N13 | Legacy path variant: Chroma rows stored with non-canonical path found and deleted by canonical purge | T5, T13 |
| N14 | Concurrent purge of same source: second purge blocks, then succeeds (zero rows, exit 0) — idempotent | T7, T13 |
| N15 | Alternate data root: temp config with non-default paths; ingest and purge compute identical source lock path; no live paths touched | T1, T13 |
| N16 | Missing-file exclusion: purge a path whose file has been deleted; synthetic marker created; --list shows it; --undo clears it; watch_skip_reason returns "excluded" | T7, T8, T13 |
| N17 | No lock during LLM/embed: instrument lock acquire/release; assert no source or export lock held between parse-start and batch-write-start | T9, T13 |
| N18a–h | Failure injection at each of 8 boundaries (F1–F8 in crash matrix): simulated crash → exclusion intact (where applicable) → retry converges | T7, T13 |
| N19 | Superseded cache invalidation: after purge deletes units (some of which were superseded=True), `count_units(include_superseded=False)` returns correct count without stale cache | T5, T13 |

---


## Implementation Sequence

```
T1 (source lock) ─┐
                   ├─→ T4 (JSONL purge) ─────┐
T2 (export lock) ──┘                          │
                                               │
T3 (path candidates) ─┬─→ T5 (Chroma purge) ─┼─→ T6 (preview) ─┐
                       │                       │                  │
                       └───────────────────────┘                  │
                                                                  ├─→ T7 (orchestrator) → T8 (CLI) ─┐
                                                                  │                                  │
T9  (ingest lock) ────────────────────────────────────────────────┤                                  │
T10 (inter-model lock) ───────────────────────────────────────────┤                                  │
T11 (observe export lock) ────────────────────────────────────────┤                                  │
T12 (deduplicate export lock) ────────────────────────────────────┘                                  │
                                                                                                     │
                                                                                              T13 (acceptance)
                                                                                                     │
                                                                                              T14 (push)
```

---

## Constraints (preserve)

1. **No lock across LLM/embed.** Source and export flocks acquired only for batch-write critical section. Parse and inference run unlocked. Tested by N17.
2. **Lock ordering is absolute.** source > export > processed. Tested by N9.
3. **Existing tests must pass.** `test_processed_exclude_race.py` and `test_chroma_superseded.py` unchanged.
4. **No new dependencies.** `fcntl.flock`, `pathlib`, `hashlib` only.
5. **Purge never creates files containing purged content.** No undo JSONL, no backup copy of deleted rows.
6. **All six JSONL writers use one export lock.** Derived from configured `units_export` path.
7. **Source lock identity from config.** Not hardcoded. Tested with alternate data root (N15).
8. **Postcondition required for exit 0.** Under source lock, all three sinks must be zero.
9. **Preview is read-only.** Separate function from mutation orchestrator. No locks, no mutations.
10. **Behavioral demos use temp config/corpus only.** Never the live `~/.local/share/convmem/` data (Amendment §12).

---

## Evidence (Execute)

- pytest passing for N1–N19 (including N18a–h failure injection)
- Behavioral demo using temporary config + Chroma + processed + export:
  - `convmem exclude /tmp/test-source.jsonl --purge --yes` → exit 0, postcondition passes
  - `convmem exclude /tmp/test-source.jsonl --purge` (no --yes) → preview, decline, no mutation
  - `convmem exclude /tmp/deleted-source.jsonl --purge --yes` → missing-file path, synthetic key, exit 0
- Lock ordering assertion fires on deliberate violation (N9)
- No-lock-during-LLM instrumentation passes (N17)
- Alternate-data-root lock identity matches (N15)
- Existing test suite passes without modification
- Superseded cache correct after purge (N19)

---

## Execute entry

- First code task: **T1** (source lock module) + **T3** (path candidates) in parallel, after Ryan says `execute`.
- Implementation branch: `feat/2026-MM-DD-exclude-source-purge` (created at execute time, not now).

---

## Exit Criteria (Execution Planning)

- [x] Architecture gates 1–12 proposed with trade-off analysis
- [x] Lock ordering defined; three locks identified with derivation rules
- [x] Crash/failure matrix expanded with injection at every boundary (F1–F10)
- [x] Named tests N1–N19 mapped to tasks
- [x] JSONL writer inventory (all 6) identified and locked
- [x] Lock identity derived from config, not hardcoded
- [x] Missing-file exclusion key designed
- [x] Guarantee corrected (postcondition, source fence, no false atomicity claim)
- [x] Logical-vs-forensic distinction explicit
- [x] Preview/mutation separation specified
- [x] Architecture contradiction (source-lock-covers-export) resolved
- [x] Behavioral demos restricted to temp config/corpus
- [ ] No code until Ryan HITL / `execute`

Cursor must stop here. Await HITL.
