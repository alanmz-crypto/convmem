# Architecture — Knowledge-Unit Conflict Detection

**Date:** 2026-07-12  
**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Status:** Awaiting HITL on gates (architecture only — not executed)

## Problem

Chroma already handles **write** contention (stable IDs + upsert). It does **not** catch conflicting **content** updates to the same ledger unit. Two agents can propose contradictory updates in one session; approve/upsert can succeed without compare-and-swap on content and without noticing sibling pending proposals.

## Goal (MVP)

Content-level conflict detection on the **propose → approve → ledger upsert** path only — not a lock system, not a coordination framework.

## Design

1. **Propose (append-only)** — When a proposal targets an existing ledger unit, store on the pending record:
   - `target_ledger_id`
   - `base_content_hash` (hash of live unit at propose time)
   - author / `proposed_by`
   - `session_id` when known  
   Plus existing fields (`summary`, `rationale`, `relates_to`, …).

2. **Approve gate** — Recompute hash on the live unit. If it ≠ `base_content_hash` → **stale base**: do not upsert; leave proposal pending and visible for human resolution.

3. **Pending collision** — If ≥2 `PENDING` proposals share the same `target_ledger_id`: keep **both**, list them as a conflict group, route to existing human approval (Ryan / kiro-review). Never auto-pick a winner.

4. **New facts** — Proposals with no `target_ledger_id` skip CAS (unchanged path).

5. **Ingest** — Chat/log indexing stays non-blocking; no new locks on `convmem index --file`.

## Not this arc

- Distributed locks / leases over Chroma  
- Auto-merge or LLM “pick a winner”  
- Blocking concurrent ingest  
- MCP write/approve  
- Hybrid lexical+dense retrieval, CI eval, timing JSONL, provenance sidecars (later)

## Gates (defaults if Ryan accepts)

| # | Decision | Default |
|---|----------|---------|
| 1 | Storage | Extend `pending_decisions.jsonl` (no second queue) |
| 2 | Hash | SHA-256 of document + allowlisted metadata (`ledger_id`, `kind`, `status`, `domain`, `site`) |
| 3 | Stale approve | Fail closed; leave `PENDING` with `conflict_status=stale_base` |
| 4 | Collision scope | Exact `target_ledger_id` only (similarity deferred) |
| 5 | Legacy PENDING | Warn if hash missing; don’t block approve for one release |
| 6 | Surfaces | `propose_decision` / record → approve → ingest only |

## Locked

- Not a general lock/lease system  
- Never silently pick a winner  
- Agents still cannot self-approve  
- No doctor conflict nag this pass  

## Success

- Stale-base proposals cannot silently land  
- Sibling pending proposals on the same target are visible and human-resolved  
- Concurrent ingest remains as unlocked as today  

## Ask of review

Confirm the MVP is the right layer (propose/approve CAS + exact-ID pending collision), flag gaps/edge cases, and say whether any gate default should change before EXECUTION.
