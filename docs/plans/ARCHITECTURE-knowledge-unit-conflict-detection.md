# Architecture — Knowledge-Unit Conflict Detection

**Date:** 2026-07-12  
**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Status:** Awaiting HITL on final gate set (architecture only — not executed)  
**Reviews folded in:** Claude Cloud (×2) + final determinism pass (lifecycle vs conflicts, rebase, create-if-absent, single event log, recovery matrix, flock/fsync, single-host wording)

## Problem

Chroma handles **write** contention (stable IDs + upsert). It does **not** catch conflicting **content** updates to the same ledger unit. Check-then-upsert without serialization is only a preflight.

## Goal (MVP)

**Serialized optimistic concurrency for governed ledger writes on one host** — propose → approve → ledger upsert, with a narrow local critical section. Not native Chroma CAS; not distributed locks; not an orchestration framework.

## Design

### Guarantee (precise)

Application-level, **single-host** serialization assuming: every semantic writer is known; governed writers take the lock or cannot replace; data dir is local; no independent second-machine writer. If those fail, the guarantee does not hold.

### 1. One authoritative event log

**Default:** a single append-only JSONL (e.g. `pending_decision_events.jsonl`). The initial event **is** the proposal:

```json
{
  "event_type": "PROPOSED",
  "event_id": "...",
  "proposal_id": "...",
  "recorded_at": "...",
  "proposal": {
    "target_ledger_id": null,
    "base_content_hash": null,
    "proposed_content_hash": "...",
    "hash_schema_version": 1,
    "summary": "...",
    "rationale": "...",
    "proposed_by": "...",
    "session_id": null
  }
}
```

Later events reference `proposal_id` only. **No two-file create** for one valid proposal.

Compat: if `pending_decisions.jsonl` must remain, the proposal row is the implicit initial event; the events file then holds only later transitions — still **one durable append** to create a proposal.

**Durability inside the lock:** append → flush → `fsync` before external/Chroma write. Event order = **JSONL append order** (not wall-clock). `recorded_at` is evidence only.

**Lock:** OS advisory lock (`flock` / `fcntl`) on a lockfile under `~/.local/share/convmem/`. Crash releases the lock. Not a sentinel-file “exists = locked” scheme.

### 2. Lifecycle vs conflicts (two derived properties)

```text
lifecycle_state:  PROPOSED | APPROVAL_STARTED | APPROVED | REJECTED | SUPERSEDED
active_conflicts:  stale_base | target_missing | target_tombstoned | pending_sibling
                   | create_target_exists | pending_create_collision
```

- Events `CONFLICT_DETECTED` / `CONFLICT_CLEARED` update `active_conflicts` **without** replacing lifecycle.
- `unresolved` = `lifecycle_state ∈ {PROPOSED, APPROVAL_STARTED}`
- Sibling detection considers only **unresolved** proposals.

### 3. Propose (under lock for targeted / create paths)

**Update proposals** (`target_ledger_id` set): snapshot live semantic hash → `base_content_hash`; compute `proposed_content_hash`; require `proposed metadata.ledger_id == target_ledger_id` (identity change out of scope). Flag `pending_sibling` if another unresolved proposal shares the target.

**New facts** (no `target_ledger_id`): **create-if-absent under the same lock** — derive/validate proposed `ledger_id`, reload live store, fail with `create_target_exists` if occupied; recheck unresolved creates with same proposed id → `pending_create_collision`. New facts are not stale-base CAS, but must not become an overwrite bypass.

### 4. Hash contract (schema v1)

Canonical object:

```json
{
  "hash_schema_version": 1,
  "document": "...",
  "metadata": {
    "ledger_id": "...",
    "kind": "...",
    "status": "...",
    "domain": "...",
    "site": "..."
  }
}
```

- Absent allowlisted values → JSON `null` (not omitted)
- `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)` → UTF-8 → SHA-256 → lowercase hex
- Document: NFC; preserve internal newlines; strip at most one trailing `\n` from file reads; other whitespace is semantic
- Allowlist = semantic fields only; revisit when ledger schema gains semantic fields
- **One shared hash module** for propose and approve

### 5. Approve critical section

```text
Acquire flock
Reconcile any APPROVAL_STARTED for this proposal/target (see §7)
Reload events; recheck unresolved siblings / create collisions
Reload live target
Verify conditions
Append APPROVAL_STARTED (fsync)
Upsert content + proposal_id marker in the SAME Chroma write
Append APPROVED (fsync)
Release lock
```

| Condition | Conflict / action |
|-----------|-------------------|
| Live hash ≠ base | `stale_base`; do not write |
| Unknown id | `target_missing` |
| Tombstoned / superseded-out | `target_tombstoned` |
| Unresolved sibling same target | `pending_sibling`; no silent solo-approve |
| New-fact id already exists | `create_target_exists` |
| Unresolved create same id | `pending_create_collision` |

### 6. Resolution

| Conflict | Resolution |
|----------|------------|
| `stale_base` | **Rebase = new `proposal_id`** with fresh `base_content_hash`. Original → `SUPERSEDED` with `superseded_by_proposal_id`; new records `rebases_proposal_id`. Never mutate the old proposal’s base. |
| `target_tombstoned` | Reject, retarget active successor, or new unit related to tombstone |
| `target_missing` | Fix id, or drop target (true new fact) |
| `pending_sibling` / `pending_create_collision` | Reject one, then proceed |
| `create_target_exists` | Retarget as update (with base hash) or choose new id |

No force-approve through conflicts this pass. Reject remains available.

### 7. `APPROVAL_STARTED` recovery matrix

Run reconciliation before re-approving that proposal, before any new approval on the same target, and via an optional recovery command.

| Observed state | Result |
|----------------|--------|
| Live marker = `proposal_id` and live hash = `proposed_content_hash` | Append `APPROVED` |
| No marker, live hash still = `base_content_hash` | Safe to retry apply |
| No marker, live hash ≠ base | Record conflict; human review |
| Marker = proposal, hash ≠ proposed | Integrity failure; do not auto-resolve |
| Marker belongs to another proposal | Conflict / integrity review |
| Target missing after `APPROVAL_STARTED` | Fail closed; human review |

Application marker is written in the **same Chroma upsert** as proposed content.

### 8. Writer inventory (before Mechanical PASS)

| Writer | May create | May replace semantic content | Gate |
|--------|------------|------------------------------|------|
| Pending propose (events) | No (pending only) | No | Lock for targeted/create |
| Approve / `ingest_approved_ledger` | Yes | Yes | Lock + this protocol |
| `convmem add --file` | Yes | Must not bypass governed ledger replaces | Inventory + close |
| index/log ingest | Yes | Ideally no for ledger decisions | Unlocked OK if no replace |
| repair / migration / admin | Possibly | Possibly | Document or serialize |

**Invariant:** Unlocked ingest cannot replace semantic content of units governed by this protocol.

## Not this arc

Distributed locks, auto-merge, LLM winner-picking, force-approve, MCP write/approve, similarity collision, hybrid retrieval, CI eval, timing JSONL, provenance sidecars, doctor nag.

## Gates (final defaults)

| # | Decision | Default |
|---|----------|---------|
| 1 | Storage | **One** append-only event log; `PROPOSED` event carries full proposal |
| 2 | Hash | Schema v1 + shared module (contract above) |
| 3 | Fail closed | Conflict **set** on `active_conflicts`; no force-ack |
| 4 | Collision | Exact target / create-id; propose + approve; under flock |
| 5 | Legacy | Warn until earlier of: zero hashless targeted unresolved, or **14 days after recorded schema-deploy timestamp**; then block; one-shot migration report at ship |
| 6 | Surfaces + lock | propose/record → approve → ingest; **flock** critical section |
| 7 | Crash recovery | Full §7 matrix; marker in same upsert |
| 8 | Writer inventory | Close bypasses before Mechanical PASS |
| 9 | Rebase | Always **new** proposal_id; old → `SUPERSEDED` |
| 10 | New facts | Create-if-absent under lock; no overwrite |

## Locked

- Single-host application serialization — not native storage CAS  
- Lifecycle ≠ conflict annotations  
- Never silently pick a winner  
- Agents cannot self-approve  
- No doctor nag / force-ack this pass  

## Success / acceptance tests (Execute)

1–4. Hash: key order, operational meta, each allowlisted field, null vs missing  
5–6. Stale / tombstoned not written  
7–8. Sibling at propose; sibling after propose caught at approve  
9. Reject sibling → other proceeds  
10. Legacy warn then block after graduation  
11. Crash after upsert → recover without false stale  
12. Barrier race: two writers cannot both pass same base  
13. Indexing unaffected for non-governed units  
14. Direct writer cannot bypass  
15. Rebase yields new id + SUPERSEDED link  
16. New-fact create-if-absent / pending create collision  
17. CONFLICT_DETECTED does not remove proposal from unresolved set  
18. flock released on crash; event order follows append order  

## Ask of HITL

Reply **`accept defaults`** (these final ten gates) or list overrides. Then Cursor writes EXECUTION on this branch.
