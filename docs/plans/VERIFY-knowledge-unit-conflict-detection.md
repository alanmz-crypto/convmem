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
| Gate 5 hashless warn/block + schema-deploy timestamp | PASS (`tests/test_hash_schema_gate.py`) |

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

- Tip SHA: `f56739a` (f56739ac7e3ddc8a26988265bb2bedb69620fc41)
- pytest summary: `50 passed in 1.11s` (acceptance slice)
- Schema deploy timestamp path: data-root `hash_schema_deploy.json` (recorded once via `ensure_schema_deploy_recorded`; `hash_schema_version=1`)
- Migration report path: data-root `hash_schema_migration_report.json` (one-shot at first deploy)
- Gate 5 graduation: warn until zero hashless targeted unresolved **or** 14d after deploy; then block (`hash_schema_gate.py`; `tests/test_hash_schema_gate.py`)

```text
Mechanical PASS: 2026-07-12 — tip f56739a
```
