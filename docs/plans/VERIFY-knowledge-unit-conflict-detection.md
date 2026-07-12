# VERIFY — Knowledge-Unit Conflict Detection

**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Architecture:** [`ARCHITECTURE-knowledge-unit-conflict-detection.md`](ARCHITECTURE-knowledge-unit-conflict-detection.md)  
**Execution:** [`EXECUTION-knowledge-unit-conflict-detection.md`](EXECUTION-knowledge-unit-conflict-detection.md)

## Mechanical checks (fill after Execute)

| Check | PASS |
|-------|------|
| Hash v1 full semantic fields; per-field sensitivity (N7) | PASS (`tests/test_ledger_content_hash.py`) |
| N1 duplicate event_id | PASS |
| N2 illegal lifecycle transition | PASS |
| N3 truncated/malformed final JSONL fail-closed | PASS |
| N4 CONFLICT_CLEARED | PASS |
| N5 idempotent legacy import | PASS |
| N6 proposal_id survives ledger_unit_metadata | PASS (metadata emits `proposal_id` + `content_hash`) |
| N12 proposal_id on decisions-approved.jsonl row / durable proposal-keyed linkage | PASS |
| N8–N10 write-sequence / uncertain apply recovery (lookup by proposal_id) | PASS (`tests/test_governed_recovery_and_writers.py`) |
| N11 writer bypass closed | PASS — see inventory |
| Barrier race + crash recovery (arch) | PASS (nested flock fixed; N10 leaves `APPROVAL_STARTED`) |
| Lock from data root (alternate chroma_dir) | PASS (`test_lock_is_scoped_to_data_root`) |
| Ordinary non-governed index unlocked | PASS (chat/inter-model units non-`dec_` unaffected) |

## Writer inventory (fill pass/fail)

| Path | Governed semantic replace blocked / gated? |
|------|--------------------------------------------|
| `propose_decision` approve → protocol | PASS — single flock; validate then APPROVAL_STARTED → approved JSONL → Chroma → APPROVED |
| `ingest_approved_ledger` | PASS — sets `_governed_protocol`; requires `proposal_id` on protocol rows |
| `monitor.py` upserts | PASS — via `observe.ingest_observation` upsert gate |
| `ingest.py` `add_unit` / upsert | PASS — `ChromaStore.add_unit` blocks `dec_*` **replace** without `proposal_id` |
| `inter_model_index.py` `add_unit` | PASS — same `add_unit` replace gate |
| `convmem add --file --upsert` | PASS — via `observe` upsert gate |
| `convmem record --recover` | PASS — recovery matrix (approve / retry_chroma / repair_marker / review) |

## Evidence

- Tip SHA:  (706db2804c66c248082bc57160d2cfde48b7fe89)
- pytest summary: `39 passed in 0.83s`
- Schema deploy timestamp path: `hash_schema_version=1` on every `PROPOSED` event (`propose` + legacy import)

```text
Mechanical PASS: 2026-07-12 — tip 706db28
```
