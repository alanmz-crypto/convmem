# Implementation Handoff: CG-2 production activation execution

**Date:** 2026-08-15
**Author:** OpenAI Codex (execution planning)
**For:** Cursor implementation lane
**Authorization:** Ryan, 2026-08-15 — Execute grant for the approved CG-2
execution package at `6a808f1`

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` |
| **Branch** | Start a fresh `feat/2026-08-15-cg2-production-activation` branch from the accepted CG-1/main baseline |
| **Tip SHA** | Planning package: `6a808f1`; architecture baseline: `e680ce8` |
| **Push status** | Push every implementation commit immediately with an explicit refspec |
| **PR** | Not opened |
| **Ryan GATE** | Execute is granted for T1–T5. Production gateway soak, owner activation, and GC remain separate Ryan grants. |
| **Track A ingest** | Cursor indexes its own session transcript at handoff per protocol |

## Goal / role / system state / next action

**Goal:** Move CG-1 toward safe production authority without allowing stale,
wrong-generation, or legacy-resurrected rows to serve.
**Role:** Cursor implements the approved T1–T5 package and supplies mechanical
evidence; Codex remains the upstream planning lane.
**System state:** CG-1 is merged and hermetic; the CG-2 architecture is locked;
the execution plan passed Kiro review; all production owners remain legacy.
**Next action:** Start T1 on a fresh implementation branch after reading the
execution plan, this handoff, and the CG-2 STATUS file.

## What to build

Implement the five tasks in
[`EXECUTION-cg2-production-activation.md`](../plans/EXECUTION-cg2-production-activation.md):
first establish the global serving-authority boundary while all owners remain
legacy, then add source-freshness/reconciliation, logical accounting,
Chroma-specific mixed-mode proof and lifecycle controls, and finally the
copied-corpus rehearsal/readiness evidence. The result must preserve the
existing legacy behavior during the first runtime milestone and make all
future generation cutovers explicitly gated.

**Why this exists:** CG-1 prevents hybrid committed generations but is not
wired into production. CG-2 must make authority explicit at every read and
promotion boundary before any owner can migrate.

## Integration points

The implementation is expected to touch these surfaces after inspection; do
not assume the conceptual names below are final APIs:

| Surface | Purpose |
|---|---|
| `query.py`, `ask.py`, `convmem.py` | CLI/search/ask/stats serving entry points and existing fallback paths |
| `mcp_server.py` | MCP search, ask, related, and serving stats |
| `chroma_store.py`, `chroma_readonly.py` | Core repository/storage and metadata helpers beneath serving callers |
| `file_generation_*.py` | CG-1 owner, manifest, validation, pointer, and promotion substrate |
| `watch.py`, `ingest.py` | Source scheduling, reconciliation, bounded admission, and promotion binding |
| `doctor.py`, `projection_parity.py` | Logical completeness/purity/parity and operational diagnostics |
| `tests/` | Focused boundary, concurrency, path-race, crash, accounting, and Chroma tests |

## Specification

### Inputs

- Locked architecture `e680ce837653698a5be8b78ba02db2f880c40c63`.
- Execution plan `6a808f1` and VERIFY stub in the same plan branch.
- Existing CG-1 implementation and tests on the accepted main baseline.
- Pinned Chroma `1.5.9` behavior measured in isolated test roots.
- No live configuration or production activation manifest.

### Algorithm / behavior

1. **T1 — Authority boundary:** resolve owner authority once per request using
   durable fence/pointer/manifest/retirement evidence; read/copy/verify and
   retry on evidence churn; freeze the resulting authority vector before row
   dereference. Use typed authority/integrity/transient failures. Only the
   repository-mediated transient class may fall back, and it must preserve the
   same frozen authority set.
2. **T2 — Source freshness:** build from a securely opened source object or
   private snapshot; while holding the owner lock, recompute the current source
   observation and refuse promotion when it differs from the candidate. Add a
   bounded, watcher-independent reconciler for startup, restart, overflow or
   uncertainty, periodic sweeps, root changes, and pre-canary checks. Coalesce
   superseded owner work.
3. **T3 — Logical truth:** compare namespaced logical identity
   `(owner_digest, collection_kind, logical_id)`. Separate completeness,
   purity, duplicates, wrong owner/generation, retained history, and physical
   amplification. Keep serving counts distinct from physical storage counts.
4. **T4 — Backend proof:** compare mixed-mode retrieval with an authority-clean
   Chroma 1.5.9 control using matching embeddings, metric, and HNSW settings.
   Report authority safety, authorized cardinality, and retrieval quality as
   separate properties. Keep automatic GC, compaction, and internal queue
   surgery disabled.
5. **T5 — Evidence:** run copied-corpus legacy-only rehearsal, rollback,
   restart, process-kill, source-race, lost-notification, and divergence tests;
   map implementation tests to all 12 formal properties; fill VERIFY from
   mechanical evidence. Stop at every separate Ryan grant.

### Output / contract

- No serving path can query raw Chroma or readonly SQLite state without an
  explicit authority classification.
- Authority/integrity failures are observable and fail closed.
- A generational owner cannot silently fall back to legacy.
- A candidate cannot promote after active-generation or source-hash drift.
- Logical doctor/parity output is truthful when physical generations coexist.
- The first production milestone remains legacy-compatible and does not
  publish a production fence, pointer, activation manifest, or GC deletion.

### Constants and budgets

Do not invent final values. Measure and ratify during T4/T5 for:

- `authority_resolution_retry_budget.max_attempts`
- `authority_resolution_retry_budget.max_elapsed`
- `max_reconciliation_staleness`
- gateway latency regression
- cold-validation/reopen/replay time
- queue/backlog, disk headroom, and storage-amplification limits

## What NOT to build

- Do not activate any production owner or edit live configuration.
- Do not publish a legacy fence or production pointer during this Execute
  scope.
- Do not implement automatic inactive-generation deletion, online GC, or
  physical compaction.
- Do not introduce stable logical owner IDs, mutable locator registries,
  automatic hardlink merging, or corpus-wide atomicity.
- Do not weaken typed fallback into `except Exception` behavior.
- Do not manipulate Chroma internal queues or change SQLite/Chroma durability
  pragmas.
- Do not claim exact kNN, serializability, or power-loss guarantees beyond the
  locked architecture.
- Do not make unrelated doctor, ranking, backup, or site changes.

## Test expectations

Add focused tests in the appropriate existing/new test modules. Use temporary
roots and deterministic fixtures; never rely on the live corpus or changing
STATUS/LATEST files for behavior assertions.

1. **Boundary inventory:** every serving-adjacent read is classified; an empty
   or disabled discovery result fails.
2. **Legacy equivalence:** all CLI/MCP serving surfaces preserve reference
   results through the gateway while every owner is legacy.
3. **Authority races:** fence/pointer/manifest churn retries or refuses; typed
   authority/integrity failures never fall through to legacy.
4. **Retry termination:** attempt and elapsed budgets produce
   `AUTHORITY_UNSTABLE`, with no rows, cache entry, or fallback.
5. **Source races:** source mutation during build and after qualification
   refuses promotion; current authority remains intact.
6. **Reconciliation:** startup, restart, lost notification, root uncertainty,
   periodic sweep, delete/recreate, and rename inventory differences converge
   within the ratified bound.
7. **Logical accounting:** missing, unexpected, duplicate, wrong-owner,
   wrong-generation, retained, abandoned, empty-set, and physical-ID-change
   fixtures report the correct category.
8. **Mixed mode:** authority-clean control comparison proves safety/cardinality
   separately from ANN quality; unbounded proof blocks rollout.
9. **Crash/recovery:** kill around staging, qualification, pointer publication,
   and restart; active/previous retention and exact-pointer recovery survive.
10. **Formal refinement:** produce a test-to-property map for all 12 TLA+
    properties in the Execute evidence package.

## Acceptance criteria

- [ ] T1–T5 deliverables are implemented only within the execution plan scope.
- [ ] Focused CG-2 tests and the complete repository suite pass with no
      unexplained failures.
- [ ] Static and runtime serving-boundary inventory covers all known and
      discovered serving-adjacent reads.
- [ ] Source reconciliation, stale-promotion refusal, logical accounting, and
      Chroma control evidence meet ratified budgets.
- [ ] Crash, rollback, restart, path-race, and lost-notification evidence is
      recorded at the exact implementation tip.
- [ ] VERIFY is filled only from mechanical evidence and names the exact
      subject tip plus external-review applicability decision.
- [ ] No production configuration, owner fence/pointer, activation manifest,
      automatic GC, or physical compaction was performed.
- [ ] No regression in the existing suite; lint/type gates pass per repository
      conventions.
- [ ] Each commit is pushed immediately; PR is opened only when the package is
      ready for review. Ryan remains the merger.

## Branch convention

```text
feat/2026-08-15-cg2-production-activation
```

Push immediately after each commit with an explicit refspec. Do not work on
the planning branch for runtime code. Ryan squash-merges unless a PR says
**Do not squash**.

## Related files

| What | Path |
|---|---|
| Locked architecture | `docs/plans/ARCHITECTURE-cg2-production-activation.md` |
| Execution scope | `docs/plans/EXECUTION-cg2-production-activation.md` |
| VERIFY companion | `docs/plans/VERIFY-cg2-production-activation.md` |
| Arc STATUS | `docs/plans/STATUS-cg2-production-activation.md` |
| Formal model | `docs/plans/formal/cg2/` |
| Triple delta review | `docs/inter-model/CURSOR-2026-08-15-cg2-delta-confirmation.md` |
| Current pointer | `docs/inter-model/LATEST.md` |

## Leaving / picking up checklist

**Author (leaving):**

- [x] This handoff is committed and pushed with the plan package.
- [x] `LATEST.md` names this handoff and the resume state.
- [x] `STATUS-cg2-production-activation.md` records the Execute grant.
- [x] Runtime work remains on a fresh Cursor implementation branch.

**Implementer (picking up):**

- [ ] Read this handoff, the execution plan, VERIFY stub, and STATUS before
      first edit.
- [ ] Run `convmem work start feat cg2-production-activation` or resume an
      explicitly authorized implementation branch.
- [ ] State Goal / role / system state / next action in the implementation
      session.
- [ ] Push immediately after every commit and stop for Ryan if scope,
      authority, security, or architecture changes are required.
