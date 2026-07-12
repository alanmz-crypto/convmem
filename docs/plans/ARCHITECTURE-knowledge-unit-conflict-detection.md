# Architecture — Knowledge-Unit Conflict Detection

**Date:** 2026-07-12  
**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Status:** Awaiting HITL — **accept with overrides** (architecture only; not executed)  
**Reviews folded in:** Claude Cloud tightenings + second-pass correctness review (CAS gap, crash recovery, state model, Gate 5, writer inventory)

## Problem

Chroma handles **write** contention (stable IDs + upsert). It does **not** catch conflicting **content** updates to the same ledger unit. A naive “read hash → compare → upsert” is only a **preflight**, not compare-and-swap, unless the check and write are serialized.

## Goal (MVP)

Content-level optimistic concurrency on **propose → approve → ledger upsert**, with a **narrow local critical section** so conflicting semantic updates cannot silently land. Not a distributed lock system; not an orchestration framework.

## Design

### 1. Propose (append-only events)

When a proposal targets an existing ledger unit, record at least:

| Field | Role |
|-------|------|
| `proposal_id` | Stable identity (existing `dec_prop_…` id) |
| `target_ledger_id` | Unit being updated |
| `base_content_hash` | Semantic hash of live target at propose time |
| `proposed_content_hash` | Semantic hash of the **proposed** document+allowlisted metadata |
| `hash_schema_version` | Integer; start at `1` |
| `proposed_by` / `session_id` | Author + optional session |
| existing fields | `summary`, `rationale`, `relates_to`, … |

**New facts** (no `target_ledger_id`) skip CAS.

**Hash contract (frozen for schema v1):**

- Canonical JSON object: `{ "hash_schema_version": 1, "document": "...", "metadata": { ... } }`
- Metadata keys allowlisted only: `ledger_id`, `kind`, `status`, `domain`, `site`
- Absent allowlisted values → JSON `null` (not omitted)
- `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)` then UTF-8 → SHA-256 → lowercase hex
- Document string: NFC Unicode; preserve internal newlines; strip only a single trailing `\n` if present for file-read consistency — leading/trailing other whitespace is semantic
- **One shared hash module** used by both propose and approve (no duplicated logic)
- **Allowlist rationale:** hash semantic content only; exclude operational fields (e.g. timestamps/indexes) that change without a real conflict. **Revisit allowlist when ledger schema gains a semantic field.**

### 2. Append-only state model (not in-place “append-only” fiction)

Do **not** rewrite history ambiguously. Prefer **transition events** appended to the pending queue (or a sibling `pending_decision_events.jsonl` if rewriting the main row is unavoidable — Gate 1 default: **events file + derived latest state**).

Authoritative states (latest valid transition wins):

```text
PROPOSED | CONFLICT_DETECTED | APPROVAL_STARTED | APPROVED | REJECTED | REBASED
```

Each event: `proposal_id`, `event_id`, `event_type`, `recorded_at`, optional `related_proposal_ids`, `conflicts`, hashes observed.

**Conflicts are a set**, not a single `conflict_status`:

```json
"conflicts": ["stale_base", "pending_sibling"]
```

or structured records with `type`, `detected_at`, `observed_hash` / `proposal_ids`. A proposal may carry more than one conflict type.

### 3. Narrow critical section (required for true CAS)

**Invariant:** All semantic updates to an existing ledger unit governed by this protocol are serialized through **one local approval/proposal critical section** (file lock under `~/.local/share/convmem/`, analogous to `propose_interactive.lock` but covering propose-append for targeted proposals + approve/apply).

Inside the lock:

```text
Acquire lock
Reload pending/events
Recheck sibling PENDING (exact target_ledger_id)
Reload live target
Verify target exists / not tombstoned; base hash matches
Mark APPROVAL_STARTED (durable)
Upsert / apply
Record APPROVED (or failure transition)
Release lock
```

Targeted **propose** also takes the same lock briefly: reload queue → detect siblings → append `PROPOSED` (+ `CONFLICT_DETECTED` if needed). Without this, two proposers can both miss each other.

If Ryan later rejects even this narrow local mutex, the feature must be renamed to **best-effort stale-base preflight** — not CAS. **Default: keep the mutex.**

### 4. Approve outcomes

| Condition | Action |
|-----------|--------|
| Live hash ≠ `base_content_hash` | Fail closed; `conflicts` += `stale_base`; stay unresolved until rebased |
| Target missing (unknown id) | Fail closed; `conflicts` += `target_missing` |
| Target tombstoned / superseded-out | Fail closed; `conflicts` += `target_tombstoned` |
| Sibling PENDING same target | Fail closed for silent solo-approve; `conflicts` += `pending_sibling` |
| OK | Apply under lock; transition `APPROVED` |

**Collision timing:** flag siblings **on propose** and **re-check on approve**.

### 5. Resolution paths (separated)

| Conflict | Resolution |
|----------|------------|
| `stale_base` | Human **re-proposes** (`REBASED` / new proposal) against current live content — new `base_content_hash`. No force-approve this pass. |
| `target_tombstoned` | Reject, retarget an active successor, or propose a **new** unit with explicit relationship to the tombstone. |
| `target_missing` | Fix `target_ledger_id`, or drop target and treat as new fact. |
| `pending_sibling` | Reject one sibling, or acknowledge both then approve under policy after the other is rejected/resolved. |

### 6. Crash-safe approval retries

Store `proposal_id`, `base_content_hash`, `proposed_content_hash`, `hash_schema_version` on the proposal.

Recovery rule:

> If live semantic hash equals `proposed_content_hash` **and** the unit records this `proposal_id` as applying source (metadata field set at upsert), complete the `APPROVED` transition — do **not** report false `stale_base`.

Use `APPROVAL_STARTED` + reconciliation, or an applied-proposal marker on the unit. Content-hash alone is insufficient (two proposals could converge on identical text).

### 7. Ingest / writer coverage

**Invariant:** Unlocked ingest **must not** replace semantic content of units governed by this approval protocol.

Before Execute: inventory writers (table below) and close bypasses (e.g. if `convmem add --file --upsert` can overwrite decision units, gate or forbid that path for ledger ids).

| Writer | May create | May replace semantic content | Uses approval gate |
|--------|------------|------------------------------|--------------------|
| `propose_decision` | No (pending only) | No | N/A |
| approve / `ingest_approved_ledger` | Yes | Yes | Yes (this arc) |
| `convmem add --file` | Yes | Must establish | Must not bypass protected ledger updates |
| index/log ingest | Yes | Ideally no for ledger decisions | No |
| repair/migration / admin | Possibly | Possibly | Document or serialize |

Normal `convmem index --file` stays non-blocking for chat/log units.

## Not this arc

Distributed locks/leases, auto-merge, LLM winner-picking, force-approve-through-stale, MCP write/approve, similarity collision, hybrid retrieval, CI eval, timing JSONL, provenance sidecars, doctor conflict nag.

## Gates (revised defaults)

| # | Decision | Default |
|---|----------|---------|
| 1 | Storage | Pending **events** JSONL (append-only transitions) + derived latest state; proposal carries hash fields above |
| 2 | Hash | Schema v1 contract + shared module (canonicalization as specified) |
| 3 | Stale / missing / tombstoned | Fail closed; conflicts **set**; resolve per §5 — no force-ack |
| 4 | Collision | Exact `target_ledger_id`; check on propose **and** approve; under same local lock |
| 5 | Legacy PENDING | **Warn** until the earlier of: (a) zero hashless **targeted** pending rows, or (b) **14 days after schema deploy timestamp** recorded at ship. Then **block** hashless targeted approvals (must re-propose). Emit a one-shot migration report at deploy. |
| 6 | Surfaces + serialization | `propose_decision` / record → approve → ingest only, plus **narrow local critical section** for targeted propose + approve |
| 7 | Crash recovery | `APPROVAL_STARTED` + `proposal_id` on applied unit + `proposed_content_hash` recovery rule |
| 8 | Writer inventory | Prove no bypass of semantic replace for governed ledger units before Mechanical PASS |

## Locked

- Not a general/distributed lock system — local file mutex only, scoped to this protocol  
- Never silently pick a winner  
- Agents cannot self-approve  
- No doctor nag / force-ack this pass  
- Without the mutex, do not claim CAS  

## Success / acceptance tests (Execute must cover)

1. Key-order-equivalent JSON → same hash  
2. Operational metadata change → same hash  
3. Each allowlisted field change → different hash  
4. Missing vs `null` consistent  
5. Stale target → not written; stays unresolved with `stale_base`  
6. Tombstoned target → not recreated; `target_tombstoned`  
7. Sibling at propose → reported  
8. Sibling after propose → caught at approve  
9. Reject sibling → remaining can proceed  
10. Hashless legacy: warn in window, block after graduation  
11. Crash after upsert → recover without false `stale_base`  
12. Barrier race: two competing semantic writers cannot both pass same base  
13. Ordinary indexing unaffected  
14. Direct writer cannot bypass protected ledger-update path  

## Ask of HITL

Reply **`accept defaults`** (meaning these **revised** eight gates) or list further overrides. Then Cursor writes EXECUTION on this branch.
