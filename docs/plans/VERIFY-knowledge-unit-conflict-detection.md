# VERIFY — Knowledge-Unit Conflict Detection

**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Architecture:** [`ARCHITECTURE-knowledge-unit-conflict-detection.md`](ARCHITECTURE-knowledge-unit-conflict-detection.md)  
**Execution:** [`EXECUTION-knowledge-unit-conflict-detection.md`](EXECUTION-knowledge-unit-conflict-detection.md)

## Mechanical checks (fill after Execute)

| Check | PASS |
|-------|------|
| Hash v1 full semantic fields; per-field sensitivity (N7) | pytest |
| N1 duplicate event_id | pytest |
| N2 illegal lifecycle transition | pytest |
| N3 truncated/malformed final JSONL fail-closed | pytest |
| N4 CONFLICT_CLEARED | pytest |
| N5 idempotent legacy import | pytest |
| N6 proposal_id survives ledger_unit_metadata | pytest |
| N12 proposal_id on decisions-approved.jsonl row / durable proposal-keyed linkage | pytest |
| N8–N10 write-sequence / uncertain apply recovery (lookup by proposal_id) | pytest |
| N11 writer bypass closed | see inventory |
| Barrier race + crash recovery (arch) | pytest |
| Lock from data root (alternate chroma_dir) | smoke |
| Ordinary non-governed index unlocked | smoke |

## Writer inventory (fill pass/fail)

| Path | Governed semantic replace blocked / gated? |
|------|--------------------------------------------|
| `propose_decision` approve → protocol | |
| `ingest_approved_ledger` | |
| `monitor.py` upserts | |
| `ingest.py` `add_unit` / upsert | |
| `inter_model_index.py` `add_unit` | |
| `convmem add --file --upsert` | |

## Evidence

- Tip SHA: _
- pytest summary: _
- Schema deploy timestamp path: _

```text
Mechanical PASS: YYYY-MM-DD — tip <sha>
```
