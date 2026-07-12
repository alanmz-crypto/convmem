# Architecture — Knowledge-Unit Conflict Detection

**Date:** 2026-07-12  
**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Predecessor:** Restic Integrity Preflight (Gate 6) merged @ `c8e6e01` (PR #2)  
**Phase:** Architecture Planning → HITL before Execution Planning

```
Planning Status

Phase:        Architecture Planning
Characters:   Architect, Systems Thinker, Risk Reviewer
Functions:    Planner
Lanes:        Cursor (Tier A); Codex/Kiro review rounds expected before Execute
Authority:    Awaiting HITL
```

---

## Architecture Direction — Content-level conflict detection for ledger updates

**Source:** Ryan priority after Gate 6 close — DeepSeek/review gap: Chroma handles write contention (stable IDs, upsert), but nothing catches conflicting *content* updates to the same ledger unit.  
**Authority:** Awaiting HITL @ 2026-07-12  
**Problem:** Two agents can propose conflicting updates against the same ledger fact in the same session; approve/upsert succeeds without comparing against the unit’s content at proposal time or against sibling pending proposals. Storage-level upsert is not a content compare-and-swap.

### System boundary

**In scope (this pass)**

- Append-only **update proposals** (extend existing `pending_decisions.jsonl` shape or a sibling queue — gate 1) carrying at least:
  - `target_ledger_id` — the unit being updated (or created-as-child with explicit parent)
  - `base_content_hash` — hash of the target’s document (and selected metadata fields) at propose time
  - `proposed_by` / author
  - `session_id` — opaque session/transcript identifier when known
  - existing proposal fields (`summary`, `rationale`, `relates_to`, domain/site, …)
- **Stale-base check at approve/upsert:** if live unit’s content hash ≠ proposal’s `base_content_hash`, **do not silently apply** — reject or flag into the human-approval path (gate 3)
- **Pending-vs-pending contradiction surface:** when ≥2 `PENDING` proposals share the same `target_ledger_id`, or (optional, gate 4) high-similarity same-domain pending pair — **preserve both**, surface a conflict record / list entry, route to existing Ryan/Kiro signer path — never auto-pick a winner
- Hermetic tests for hash helper, stale-base gate, and pending-collision listing
- CLI visibility: list conflicts / show stale on `approve` / `propose_decision --list`

**Out of scope**

- General distributed locking, leases, or mutexes over Chroma
- Blocking ordinary concurrent **ingest** of chat/logs (index adapters stay append/upsert by source unit id)
- Hybrid lexical retrieval, CI eval wiring, per-stage timing, provenance sidecars (later arcs from the same review)
- Changing Restic / write-gate / restore-drill
- MCP write/approve surfaces (still read-only)
- Auto-merge, LLM-judged “which claim wins,” or silent last-writer-wins at content level
- Rewriting history of already-approved decisions (supersede remains the existing path)

**Deferred with owner**

| Item | Owner |
|------|--------|
| Similarity-based pending collision (beyond exact `target_ledger_id`) | Ryan after exact-ID MVP PASSes |
| Backfill `base_content_hash` on historical pending rows | Optional; new proposals only is enough for MVP |
| Doctor nag for open conflicts | Separate HITL after MVP |
| Observation/verify conflict types beyond decision proposals | Later |

### Constraints and invariants (repo reality)

- Today: `propose_decision.propose()` appends to `~/.local/share/convmem/pending_decisions.jsonl` with **no** content hash; `approve()` → `decisions-approved.jsonl` → `ingest_approved_ledger` → Chroma **upsert** by stable ledger id ([`propose_decision.py`](../../propose_decision.py), [`chroma_store.add_unit`](../../chroma_store.py))
- Single interactive lock (`propose_interactive.lock`) only serializes `propose_decision -i` — not content CAS
- Charter: agents never `--approve-last`; Ryan / `kiro-review` signers only
- Contradiction surface before write gate is prior art in corpus (Codex: make contradictions visible first) — this arc implements that for **ledger update proposals**, not a new always-on lock service
- Ordinary ingest must remain non-blocking: conflict machinery attaches to **propose → approve → ledger upsert**, not to every chat chunk

### Options considered

| Option | Summary | Rejected because |
|--------|---------|------------------|
| A — Chroma-level leases / locks | Mutex around unit ids during agent sessions | Coordination bottleneck; wrong layer; ingest would pay |
| B — Exact-target CAS + pending collision (recommended) | Hash at propose; stale check at approve; list/flag same-`target_ledger_id` pendings | — |
| C — Full semantic contradiction engine | Embed every pending vs corpus; LLM judge | Costly; false positives; out of MVP |
| D — Git-style merge on JSONL only | No Chroma awareness | Misses live unit drift after approve of sibling |

### Chosen direction

**Option B.** Treat conflicting *ledger updates* as a first-class pending state:

1. **Propose (append-only):** when a proposal targets an existing ledger unit (or declares `target_ledger_id`), compute `base_content_hash` from the live unit document (+ pinned metadata keys) and store it on the pending record with author + optional `session_id`.
2. **Approve / upsert gate:** recompute hash on the live unit; if mismatch → **stale base** — fail closed on silent apply; surface both the proposal and the current unit for human resolution (gate 3 chooses hard-reject vs leave PENDING with `conflict: stale_base`).
3. **Pending collision:** if another `PENDING` already shares `target_ledger_id`, mark/list a **conflict group**; keep both records; approval of either requires Ryan/Kiro to acknowledge the sibling (or reject one first).
4. **No winner algorithm** — human-approval path remains the only resolver.

This sits on the existing evidence/verification model (`relates_to`, approve signers, approved JSONL → Chroma) without turning concurrent session ingest into a lock queue.

### Risks and reversibility

- **False stale:** metadata-only Chroma bookkeeping changes must not flip the content hash — hash only document + allowlisted metadata keys
- **Adoption gap:** proposals without `target_ledger_id` (pure new facts) skip CAS — document that path explicitly
- **Queue migration:** old PENDING rows lack hash — treat as “unscoped” (warn on approve) or require re-propose (gate 5)
- **Scope creep into ingest locks:** reject any design that blocks `convmem index --file`
- **Rollback:** feature-flag or ignore new fields; remove CLI conflict list; no Chroma schema migration required if hash lives on pending JSONL only

### Downstream handoff

- Next: [`EXECUTION-PLANNING.md`](../planning/EXECUTION-PLANNING.md) after HITL on gates below  
- Expect Codex/Kiro architecture review rounds (same multi-round pattern as branching/hygiene/restore drill) before Execute  
- Later arcs (do not fold in): hybrid lexical+dense, CI eval, retrieval timing JSONL, ingestion provenance sidecars

---

## Decisions Ryan must make before build

| # | Decision | Recommendation (default if you assent) |
|---|----------|------------------------------------------|
| 1 | Storage | **Extend `pending_decisions.jsonl` records** with `target_ledger_id`, `base_content_hash`, `session_id` — no second queue file this pass |
| 2 | Hash input | **SHA-256 of canonical UTF-8 document + sorted allowlisted metadata** (`ledger_id`, `kind`, `status`, `domain`, `site` if present) — exclude Chroma-internal/hnsw noise |
| 3 | Stale base at approve | **Fail closed:** refuse approve/upsert; leave proposal `PENDING` with `conflict_status=stale_base` + message pointing at live hash — Ryan re-proposes or force-ack later (force-ack **out of scope** this pass) |
| 4 | Pending collision scope | **Exact `target_ledger_id` only** this pass; similarity/same-domain pending pairs **deferred** |
| 5 | Legacy PENDING rows | **Warn on approve** if hash fields missing; do not block approve for one release (compat), but **new** proposals that declare a target **must** carry hash |
| 6 | MVP surfaces | **`propose_decision` / `record` propose path + approve/ingest_approved_ledger` only** — not watch/index adapters |

---

## Locked (no re-open without new HITL)

- Not a general lock/lease system; ordinary ingest stays non-blocking
- Never silently pick a winner between conflicting claims
- No MCP approve/write
- No doctor freshness/conflict nag in this pass
- No hybrid retrieval / CI eval / timing / provenance work in this branch
- Agents still cannot self-approve

---

## Verification criteria (architecture bar — Execute will refine)

| Check | PASS condition |
|-------|----------------|
| Propose with target | Pending record contains `target_ledger_id` + `base_content_hash` (+ author; `session_id` when provided) |
| Stale approve | After live unit content changes, approve of old-hash proposal does **not** upsert; conflict visible |
| Sibling pending | Two PENDING same `target_ledger_id` listed as conflict group; both retained |
| New fact path | Proposal without target still works (no CAS) |
| Ingest unaffected | `convmem index --file` path unchanged / no new locks |
| Hermetic tests | Hash stability, stale gate, collision list without live Chroma required where mockable |

---

## Success (executive bar)

- Conflicting updates to the same ledger unit cannot silently land via approve/upsert when the base hash is stale
- Concurrent pending proposals to the same target are visible and human-resolved
- Concurrent chat ingest remains as fast/unlocked as today
- Design stays narrow enough for Codex/Kiro review without sprawling into “coordination framework”

---

## Explicitly not picking (same review’s later arcs)

| Candidate | Why not now |
|-----------|-------------|
| Hybrid BM25 + dense | Next after this MVP |
| Held-out eval in CI | After retrieval changes exist to regress |
| Per-stage retrieval timing JSONL | Observability after conflict MVP |
| Ingestion provenance sidecars | Before screenshot-producing sources, not blocking this |

---

## Gates

Await Ryan: **accept defaults** or override rows 1–6. Then Cursor shapes EXECUTION on this branch (after optional Codex/Kiro arch review if Ryan requests).
