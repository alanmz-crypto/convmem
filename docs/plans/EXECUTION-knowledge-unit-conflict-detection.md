# Execution Plan — Knowledge-Unit Conflict Detection

```
Planning Status

Phase:        Execution Planning → awaiting HITL before Execute
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Cursor (Tier A); Codex read-only if Ryan requests plan audit
Authority:    Architecture gates 1–10 accepted 2026-07-12; EXECUTION amended for write-sequence, hash boundary, named tests
```

**Architecture SSoT:** [`ARCHITECTURE-knowledge-unit-conflict-detection.md`](ARCHITECTURE-knowledge-unit-conflict-detection.md)  
**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Worktree:** `~/.local/share/convmem/worktrees/plan-2026-07-12-knowledge-unit-conflict-detection`

---

## Gate decisions (accepted)

| # | Choice |
|---|--------|
| 1 | One append-only event log; `PROPOSED` carries full proposal |
| 2 | Hash schema v1 over **full normalized semantic record** + shared module |
| 3 | Fail closed; `active_conflicts` set; no force-ack |
| 4 | Exact target / create-id collision; propose + approve under flock |
| 5 | Legacy: warn until zero hashless targeted unresolved **or** 14d after schema-deploy timestamp |
| 6 | propose/record → approve → ingest; flock critical section |
| 7 | Full `APPROVAL_STARTED` recovery matrix; marker in same upsert |
| 8 | Writer inventory; close bypasses before Mechanical PASS |
| 9 | Rebase = new proposal_id; old → SUPERSEDED |
| 10 | New facts: create-if-absent under lock |

### Execution constraints (HITL — preserve)

1. **Lock identity** — Derive lock path from canonical data root / governed store (`chroma_dir` parent or override). Same store → same lockfile.
2. **Event reducer + legacy import** — Legal transitions; duplicate `event_id`; idempotent retries; fail-closed truncated/malformed final JSONL line; `CONFLICT_CLEARED` updates active set; idempotent import of `pending_decisions.jsonl` → initial `PROPOSED` (preserve ids; hashless → Gate 5).
3. **Uncertain Chroma outcomes** — Leave `APPROVAL_STARTED`; reconcile via §7 — no definitive failure event, no blind retry.

---

## Authoritative write sequence (T4 — required)

Today approve appends `decisions-approved.jsonl` **before** Chroma index (`convmem.py` approve path; Chroma failure leaves ledger durable). Protocol recovery is Chroma-marker-aware. Execution must make the three stores consistent:

| Store | Role |
|-------|------|
| Event log | Protocol SSoT for proposal **lifecycle** + conflicts |
| `decisions-approved.jsonl` | Durable approved **record** (existing ledger SSoT) |
| Chroma | Queryable projection; holds `proposal_id` apply marker |

**Ordered apply under flock (success path):**

1. Validate (siblings, hashes, create-if-absent).
2. Append `APPROVAL_STARTED` → flush → fsync.
3. Append approved record to `decisions-approved.jsonl` → flush → fsync (durable content intent; same shape as today).
4. Chroma upsert of normalized unit **including `proposal_id` marker in metadata** in the **same** upsert (marker must survive `ledger_unit_metadata` / normalize path — extend emit list).
5. Append `APPROVED` → flush → fsync.
6. Release lock.

**Recovery additions (beyond arch §7):**

| Observed | Action |
|----------|--------|
| `APPROVAL_STARTED` + Chroma marker=`proposal_id` + hash=proposed | Append `APPROVED` |
| `APPROVAL_STARTED` + row in `decisions-approved.jsonl` for this proposal/ledger + no Chroma marker + live still base (or absent) | **Retry Chroma upsert only** (idempotent); then `APPROVED` |
| `APPROVAL_STARTED` + approved JSONL present + live hash=proposed but marker missing | Repair: re-upsert with marker; then `APPROVED` |
| Uncertain upsert error/timeout after step 2 or 3 | Leave `APPROVAL_STARTED`; do not append failure; run reconciliation before any further approve on that target |

Do not treat “approved JSONL exists” alone as license to skip sibling/hash checks on a **new** approval of a different proposal.

---

## Hash boundary (T2 — corrected)

Hash the normalized semantic record fields (aligned with `normalize_ledger_record` / decision meaning), **not** only five metadata keys:

`ledger_id`, `kind`, `status`, `title`, `summary`, `rationale`, `relates_to`, `confidence`, `domain`, `site`, `notes`, `result`, `alternatives_rejected`, `constraints`

Canonicalize with schema v1 rules (sorted keys, nulls, NFC, shared module). **Pytest: each listed field changes the hash; operational-only fields do not.**

`proposal_id` is an apply marker, excluded from the semantic hash, but **must** be passed through `ledger_unit_metadata` (and any strip/normalize step) so recovery can read it back.

---

## Goal

Ship single-host serialized optimistic concurrency for governed ledger writes with a defined three-store apply/recovery sequence, full semantic hashing, closed direct writers, and named reducer/legacy tests — without locking ordinary chat/log ingest.

---

## Tasks

| ID | Deliverable | In scope | Depends on | Gates |
|----|-------------|----------|------------|-------|
| T1 | EXECUTION + VERIFY amended | Docs | — | HITL |
| T2 | Shared hash module schema v1 | Full semantic field set; per-field tests; marker excluded from hash | T1 | pytest |
| T3 | Event log + reducer + flock (data-root lock) | **Named tests:** duplicate `event_id`; illegal lifecycle transition; truncated/malformed final JSONL line fail-closed; `CONFLICT_CLEARED` updates active set; append order | T2 | pytest |
| T4 | Propose + approve/apply under lock | Write sequence § above; create-if-absent; siblings; **proposal_id in metadata emit**; uncertain-outcome leave `APPROVAL_STARTED` | T3 | integration |
| T5 | Legacy import + Gate 5 | **Named test:** idempotent import preserves `proposal_id`; hashless → warn/block policy; no dup events | T3 | pytest |
| T6 | Close direct writers | Enumerate and gate/forbid governed semantic replace via **`monitor.py`**, **`ingest.py`**, **`inter_model_index.py`**, **`convmem add --upsert`** (and approve/ingest_approved only through protocol). Fill VERIFY inventory with pass/fail per path | T4 | code + evidence |
| T7 | Acceptance suite | Arch tests + constraint tests below + race/crash + marker round-trip after normalize | T4–T6 | pytest |
| T8 | Commit + push | Explicit refspec | T2–T7 | remote |

### Named tests required (map to T3/T5/T7/VERIFY)

| Test ID | Requirement |
|---------|-------------|
| N1 | Duplicate `event_id` → idempotent / deterministic reducer behavior |
| N2 | Illegal lifecycle transition rejected |
| N3 | Truncated or malformed **final** JSONL line → fail closed |
| N4 | `CONFLICT_CLEARED` removes only cleared types from `active_conflicts` |
| N5 | Idempotent legacy `pending_decisions.jsonl` import; stable `proposal_id`; no duplicate `PROPOSED` |
| N6 | `proposal_id` marker present after `ledger_unit_metadata` / normalize round-trip |
| N7 | Each semantic hash field flips hash; bookkeeping fields do not |
| N8–N10 | Write-sequence recovery: approved-JSONL-before-Chroma retry; marker+hash → APPROVED; uncertain upsert stays `APPROVAL_STARTED` |
| N11 | `monitor.py` / `ingest.py` / `inter_model_index.py` / `add --upsert` cannot replace governed ledger semantic content without protocol (or are documented blocked) |

### Out of scope

Distributed locks, force-approve, MCP writes, similarity collision, doctor nag, hybrid retrieval, CI eval, timing, provenance, Restic/restore-drill changes.

### Evidence (Execute)

- pytest including N1–N11 and arch barrier/crash tests
- VERIFY writer table with concrete paths above
- Schema-deploy timestamp path + migration report sample
- Lock path derived from data root (demo with alternate `chroma_dir`)

### Execute entry

- First code task: **T2** after Ryan says `execute`.
- Follow [`EXECUTE-TASK.md`](../planning/EXECUTE-TASK.md).

---

## Sign-off

**Execution Planning:** this artifact (amended).  
**HITL:** Ryan re-approves Execute after this amendment.  
**Mechanical:** Cursor fills VERIFY after T7.

## Exit Criteria (Execution Planning)

- [x] Authoritative three-store write/recovery sequence specified
- [x] Hash boundary = full normalized semantic record
- [x] Execution constraints turned into named tests N1–N11
- [x] Direct writers named for T6
- [x] `proposal_id` marker survival required
- [ ] No code until Ryan HITL / `execute`

Cursor must stop here. Await HITL.
