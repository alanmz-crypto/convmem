# Architecture — Knowledge-Unit Conflict Detection

**Date:** 2026-07-12  
**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Status:** Awaiting HITL on gates (architecture only — not executed)  
**Review folded in:** Claude Cloud, 2026-07-12 — hash canonicalization, missing-target, stale resolution, collision timing, legacy graduation, allowlist rationale

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

   **Hash canonicalization (required):** SHA-256 over a **deterministic** serialization — fixed field order, `sort_keys=True` (or equivalent) for any JSON object, stable UTF-8, no insignificant whitespace variance. Non-canonical dumps (e.g. `json.dumps(dict)` without sorted keys) are a correctness bug: identical content can falsely trip `stale_base`.

   **Metadata allowlist rationale:** Hash the **document** plus only semantic ledger fields (`ledger_id`, `kind`, `status`, `domain`, `site`). Exclude operational/bookkeeping fields that may change without a real content conflict (e.g. verification timestamps, internal indexes). **Revisit the allowlist whenever the ledger schema gains a semantic field** — new fields otherwise silently fall outside the hash (false-negative “no conflict”).

2. **Approve gate** — Recompute hash on the live unit.
   - If live unit **missing / tombstoned** → fail closed same as content mismatch (`conflict_status=target_missing`); do not upsert.
   - If hash ≠ `base_content_hash` → **stale base**: do not upsert; leave proposal `PENDING` with `conflict_status=stale_base`.
   - **Resolution path for `stale_base` / `target_missing`:** human **re-proposes** against current content (new `base_content_hash`). No “force approve anyway” override in this pass — that would reintroduce silent drift. Reject remains available via existing reject flow.

3. **Pending collision (exact `target_ledger_id`)** — Keep **both** proposals; never auto-pick a winner.
   - **On propose:** if another `PENDING` already shares `target_ledger_id`, flag a conflict group immediately (second author sees it now).
   - **On approve:** re-check siblings; if a sibling appeared since propose, still refuse silent solo-approve until the human resolves (reject one, or re-propose after acknowledging the group).
   - Route to existing human approval (Ryan / kiro-review).

4. **New facts** — Proposals with no `target_ledger_id` skip CAS (unchanged path).

5. **Ingest** — Chat/log indexing stays non-blocking; no new locks on `convmem index --file`.

## Not this arc

- Distributed locks / leases over Chroma  
- Auto-merge, LLM “pick a winner,” or force-approve-through-stale  
- Blocking concurrent ingest  
- MCP write/approve  
- Similarity-based pending collision (deferred)  
- Hybrid lexical+dense retrieval, CI eval, timing JSONL, provenance sidecars (later)

## Gates (defaults if Ryan accepts)

| # | Decision | Default |
|---|----------|---------|
| 1 | Storage | Extend `pending_decisions.jsonl` (no second queue) |
| 2 | Hash | SHA-256 of **canonically serialized** document + allowlisted metadata (`ledger_id`, `kind`, `status`, `domain`, `site`); sorted keys / fixed order required |
| 3 | Stale / missing target at approve | Fail closed; leave `PENDING` with `conflict_status=stale_base` or `target_missing`; resolve by **re-propose** (or reject) — no force-ack this pass |
| 4 | Collision scope + timing | Exact `target_ledger_id` only; check **on propose and on approve** |
| 5 | Legacy PENDING | Warn if hash fields missing; **graduate to blocking** once no `PENDING` proposal older than **14 days** lacks a hash (or queue empty of hashless rows — whichever first). Soft-warn is temporary, not permanent tolerance. |
| 6 | Surfaces | `propose_decision` / record → approve → ingest only |

## Locked

- Not a general lock/lease system  
- Never silently pick a winner  
- Agents still cannot self-approve  
- No doctor conflict nag this pass  
- No force-approve through stale/missing target this pass  

## Success

- Stale-base and missing-target proposals cannot silently land  
- Sibling pending proposals on the same target are visible at propose and re-checked at approve  
- Concurrent ingest remains as unlocked as today  
- Hash is stable for identical content (canonical serialization)  

## Ask of review / HITL

Confirm MVP layer + these six tightenings. Gate defaults above incorporate Claude’s notes (esp. Gate 5 graduation). Reply **accept defaults** or list overrides before EXECUTION.
