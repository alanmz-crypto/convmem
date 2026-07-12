# Execution Plan — Knowledge-Unit Conflict Detection

```
Planning Status

Phase:        Execution Planning → awaiting HITL before Execute
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Cursor (Tier A); Codex read-only if Ryan requests plan audit
Authority:    Architecture gates 1–10 accepted 2026-07-12 (Ryan: accept defaults)
```

**Architecture SSoT:** [`ARCHITECTURE-knowledge-unit-conflict-detection.md`](ARCHITECTURE-knowledge-unit-conflict-detection.md)  
**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Worktree:** `~/.local/share/convmem/worktrees/plan-2026-07-12-knowledge-unit-conflict-detection`

---

## Gate decisions (accepted)

| # | Choice |
|---|--------|
| 1 | One append-only event log; `PROPOSED` carries full proposal |
| 2 | Hash schema v1 + shared module |
| 3 | Fail closed; `active_conflicts` set; no force-ack |
| 4 | Exact target / create-id collision; propose + approve under flock |
| 5 | Legacy: warn until zero hashless targeted unresolved **or** 14d after schema-deploy timestamp |
| 6 | propose/record → approve → ingest; flock critical section |
| 7 | Full `APPROVAL_STARTED` recovery matrix; marker in same upsert |
| 8 | Writer inventory; close bypasses before Mechanical PASS |
| 9 | Rebase = new proposal_id; old → SUPERSEDED |
| 10 | New facts: create-if-absent under lock |

### Execution constraints (HITL — preserve; not new gates)

1. **Lock identity** — Derive lock path from the canonical convmem data root / governed store identity (config `chroma_dir` parent, or explicit override). Every process writing the same governed ledger must resolve to the **same** lockfile. Do not hard-code only `~/.local/share/convmem/` if alternate data dirs / test stores / env profiles exist.
2. **Event reducer + legacy import** — Specify legal lifecycle transitions; duplicate `event_id` handling; idempotent retry events; fail-closed on truncated/malformed final JSONL records; how `CONFLICT_CLEARED` updates the active set; how existing `pending_decisions.jsonl` rows become initial `PROPOSED` events (idempotent; preserve `proposal_id`; hashless targeted → Gate 5 policy, not drop/duplicate).
3. **Uncertain Chroma outcomes** — On upsert error/timeout after `APPROVAL_STARTED`, do **not** append a definitive failure or blind-retry. Leave `APPROVAL_STARTED` and run the architecture §7 matrix (marker+proposed hash → APPROVED; no marker+base hash → safe retry; else fail closed for review).

---

## Goal

Ship single-host serialized optimistic concurrency for governed ledger writes: event log, shared hash module, flock-scoped propose/approve, create-if-absent, rebase-as-new, crash recovery, writer-bypass closed — without locking ordinary chat/log ingest.

---

## Tasks

| ID | Deliverable | In scope | Depends on | Gates | Lane |
|----|-------------|----------|------------|-------|------|
| T1 | This EXECUTION + [`VERIFY-knowledge-unit-conflict-detection.md`](VERIFY-knowledge-unit-conflict-detection.md) | Docs | Arch accept | Ryan HITL on Execute | Cursor |
| T2 | Shared hash module (`ledger_content_hash` or similar) schema v1 | Canonicalize + tests 1–4 | T1 | pytest | Cursor |
| T3 | Event log + reducer + flock helper (data-root–derived lock) | Append/fsync; lifecycle vs conflicts; recovery hooks | T2 | unit tests | Cursor |
| T4 | Wire targeted propose + approve/apply under lock | Create-if-absent; sibling checks; same-upsert marker | T3 | integration | Cursor |
| T5 | Legacy import + Gate 5 migration timestamp/report | Idempotent; hashless policy | T3 | unit + smoke | Cursor |
| T6 | Writer inventory + close bypasses | Document + gate/forbid governed replace outside protocol | T4 | evidence in VERIFY | Cursor |
| T7 | Acceptance tests 5–18 (incl. race + crash recovery) | Arch Success list | T4–T6 | pytest | Cursor |
| T8 | Commit + push | Explicit refspec | T2–T7 | remote tip | Cursor |

### Out of scope

- Distributed locks, force-approve, MCP writes, similarity collision
- Doctor nag, hybrid retrieval, CI eval, timing, provenance
- Changing Restic / restore-drill / write-gate snapshot cadence

### Evidence (Execute)

- pytest covering arch tests 1–18 (or documented DEFER with reason for env-only race)
- Writer inventory table filled with pass/fail for bypass
- Migration report sample + schema-deploy timestamp location documented
- No hard-coded lock that ignores alternate data roots

### Execute entry

- First code task: **T2** after Ryan says `execute` / `do what is designed`.
- Follow [`EXECUTE-TASK.md`](../planning/EXECUTE-TASK.md).

---

## Sign-off

**Execution Planning:** this artifact.  
**HITL:** Ryan approves Execute (or waives with `execute`).  
**Mechanical:** Cursor fills VERIFY after T7.  
**Ryan:** merge when satisfied.

## Exit Criteria (Execution Planning)

- [x] Gates recorded as accepted
- [x] Three execution constraints explicit
- [x] Bounded tasks T1–T8
- [ ] No self-transition to code until Ryan HITL / `execute`

Cursor must stop here. Await HITL.
