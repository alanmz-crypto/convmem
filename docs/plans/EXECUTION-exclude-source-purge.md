# Execution Plan — Exclude Source Purge

```
Planning Status

Phase:        Execution Planning — awaiting HITL before Execute
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Cursor (Tier A implementation); Kiro (design/sign-off)
Authority:    Architecture gates 1–10 proposed 2026-07-14; awaiting Ryan acceptance
```

**Architecture SSoT:** [`ARCHITECTURE-exclude-source-purge.md`](ARCHITECTURE-exclude-source-purge.md)
**Branch:** `plan/2026-07-14-exclude-source-purge`
**Worktree:** `~/.local/share/convmem/worktrees/plan-2026-07-14-exclude-source-purge`

---

## Gate decisions (proposed — awaiting HITL)

| # | Choice |
|---|--------|
| 1 | --purge = hard removal, not tombstoning |
| 2 | Three sinks: Chroma units, Chroma summaries, knowledge_units.jsonl |
| 3 | Per-source advisory flock; fresh exclusion check before each derived-write batch |
| 4 | Separate export lock for JSONL; defined lock ordering (source > export > processed) |
| 5 | Exact canonical path equality; query Chroma with both raw and resolved variants |
| 6 | Marker-first crash recovery; partial purge stays excluded, nonzero exit, retry-safe |
| 7 | --undo re-enables ingest only; cannot resurrect purged rows |
| 8 | Dry-run preview with counts; confirmation default No; --yes for automation; never print payloads |
| 9 | Malformed JSONL lines fail closed; no undo artifacts with purged content |
| 10 | Deterministic tests for both race interleavings + all enumerated scenarios |

---

## Tasks

| ID | Deliverable | In scope | Depends on | Gates |
|----|-------------|----------|------------|-------|
| T1 | Source lock module | `source_flock(canonical_path)` context manager; lock path derivation from SHA-256 of canonical path; lock directory creation; ordering assertion helper | — | pytest |
| T2 | Export lock module | `export_flock()` context manager; lock path from config; ordering assertion | T1 | pytest |
| T3 | JSONL purge function | `purge_source_from_jsonl(export_path, canonical_path) -> int`; atomic tmp+rename; exact-path match; fail-closed on malformed lines; returns lines removed | T2 | pytest |
| T4 | Chroma purge function | `purge_source_from_chroma(store, canonical_path) -> dict`; deletes from both collections via raw+canonical query; returns `{units_deleted, summaries_deleted}` | — | pytest |
| T5 | Purge orchestrator | `purge_source(path, config, dry_run, yes) -> PurgeResult`; acquires source lock → marks exclusion → Chroma purge → export purge; returns counts + exit status; preview mode | T1–T4 | integration |
| T6 | CLI integration | Wire `--purge` and `--yes` into `exclude_command` in `convmem.py`; confirmation prompt; output formatting; exit codes | T5 | CLI test |
| T7 | Ingest lock integration | Modify ingest batch-write path to acquire source flock + re-check exclusion before Chroma upsert and JSONL append; modify export append to acquire export flock | T1, T2 | pytest + existing race tests still pass |
| T8 | Inter-model index integration | Same lock pattern for `inter_model_index.py` batch write path | T7 | pytest |
| T9 | Acceptance test suite | All named tests below; deterministic race tests using threading barriers | T5–T8 | pytest |
| T10 | Commit + push | Explicit refspec; CI green | T1–T9 | remote |

---

## Named Tests Required

| Test ID | Requirement | Maps to |
|---------|-------------|---------|
| N1 | Purge-then-ingest interleaving: ingest starts, purge completes, ingest batch-write finds path excluded and aborts — no orphan Chroma rows | T7, T9 |
| N2 | Ingest-then-purge interleaving: ingest batch-write completes, purge runs — all three sinks reach zero | T5, T9 |
| N3 | Unrelated export append preserved: purge of source A does not corrupt lines belonging to source B in knowledge_units.jsonl | T3, T9 |
| N4 | Exact-path boundary: paths differing only in trailing component (e.g., `/a/b.jsonl` vs `/a/b.jsonl.bak`) are not confused | T3, T4, T9 |
| N5 | Partial failure + retry idempotency: purge crashes after Chroma delete but before JSONL rewrite; retry converges to zero across all sinks | T5, T9 |
| N6 | Dry-run / decline: preview mode queries sinks and displays counts without any mutation; declining leaves all data intact | T5, T6, T9 |
| N7 | Inter-model doc indexing: purge removes units created via `inter_model_index.py` path (source_type=inter_model_doc) | T4, T8, T9 |
| N8 | All three sinks reach zero: after purge, Chroma query for source_path returns empty; JSONL grep for source_path returns zero lines | T5, T9 |
| N9 | Lock ordering violation detection: attempting to acquire source lock while holding export lock raises/asserts (guard against reverse acquisition in future code) | T1, T2, T9 |
| N10 | Malformed JSONL line: purge aborts rewrite, returns nonzero, original file unchanged | T3, T9 |
| N11 | --yes skips confirmation: purge proceeds without interactive prompt | T6, T9 |
| N12 | --undo after purge: re-enables ingest path but derived sinks remain empty until explicit re-index | T6, T9 |
| N13 | Legacy path variant: Chroma rows stored with non-canonical path are found and deleted by canonical purge | T4, T9 |
| N14 | Concurrent purge of same source: second purge blocks on source lock, then succeeds (finds zero rows) — idempotent | T5, T9 |

---

## Implementation Sequence

```
T1 (source lock) ─┐
                   ├─→ T3 (JSONL purge) ─┐
T2 (export lock) ──┘                      │
                                           ├─→ T5 (orchestrator) → T6 (CLI) → T9 (acceptance)
T4 (Chroma purge) ────────────────────────┘                                         │
                                                                                     │
T7 (ingest lock integration) ─────────────────────────────────────────────────→ T9  │
T8 (inter-model integration) ─────────────────────────────────────────────────→ T9  │
                                                                                     │
                                                                              T10 (push)
```

---

## Constraints (preserve)

1. **No lock across LLM/embed.** Source flock is acquired only for the batch-write critical section (Chroma upsert + JSONL append + processed commit). Parse and inference run unlocked.
2. **Lock ordering is absolute.** source > export > processed. The test suite must include an ordering-violation detector (N9).
3. **Existing tests must pass.** `test_processed_exclude_race.py` and `test_chroma_superseded.py` must continue passing without modification (behavioral compat).
4. **No new dependencies.** Use `fcntl.flock` (already in `ingest.py`), `pathlib`, `hashlib`. No third-party lock libraries.
5. **Purge never creates files containing purged content.** No undo JSONL, no backup copy of deleted rows, no temp file with source data. The only durable artifact is the exclusion marker in processed.json.

---

## Evidence (Execute)

- pytest passing for N1–N14
- `convmem exclude /tmp/test-source.jsonl --purge --yes` on a seeded test corpus → exit 0, all sinks zero
- Lock ordering assertion fires on deliberate violation in test
- Existing `test_processed_exclude_race.py` passes without modification
- Existing `test_chroma_superseded.py` passes without modification
- Manual demo: `convmem exclude PATH --purge` (no --yes) shows preview, declines, no mutation

---

## Execute entry

- First code task: **T1** (source lock module) after Ryan says `execute`.
- Follow [`EXECUTE-TASK.md`](../planning/EXECUTE-TASK.md) if present.
- Implementation branch: `feat/2026-MM-DD-exclude-source-purge` (created at execute time, not now).

---

## Exit Criteria (Execution Planning)

- [x] Architecture gates proposed with trade-off analysis
- [x] Lock ordering defined and documented
- [x] Crash/failure matrix for every boundary
- [x] Named tests mapped to tasks
- [x] Implementation sequence with dependencies
- [x] Constraints that preserve existing behavior
- [ ] No code until Ryan HITL / `execute`

Cursor must stop here. Await HITL.
