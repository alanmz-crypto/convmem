# Verify Plan — CG-2 production activation

```text
Planning Status

Phase:        Verify Planning (pre-Execute stub)
Characters:   Independent Reviewer, Test-First Reviewer
Functions:    Reviewer
Lanes:        Codex predeclares; Cursor mechanical; Kiro or named independent lane sign-off; Ryan GATE
Authority:    Post-Execute HITL — no execution evidence exists yet
```

**Status:** Planning stub. This document declares the proof required for the
CG-2 arc; it does not report implementation results or authorize activation.

**Subject / tip:** TBD after Execute; architecture baseline
`e680ce837653698a5be8b78ba02db2f880c40c63`.

**EXECUTION / ARCHITECTURE:**
[`EXECUTION-cg2-production-activation.md`](EXECUTION-cg2-production-activation.md) /
[`ARCHITECTURE-cg2-production-activation.md`](ARCHITECTURE-cg2-production-activation.md)

**Goal:** Prove that the implementation preserves one serving authority,
rejects stale work and lost source notifications, accounts for logical rather
than physical identity, and remains safe through rehearsal, restart, rollback,
and bounded Chroma operation.

## Human consequence

If this VERIFY plan passes after Execute, Ryan can decide whether the
implementation is ready for the separately granted legacy-only gateway soak.
It still does not itself activate a production owner or enable GC.

### 5 Ws

| | |
|---|---|
| **Who** | Cursor supplies mechanical evidence; Kiro or a Ryan-named independent lane signs; Ryan gates acceptance and activation separately. |
| **What** | Evidence for the CG-2 authority migration implementation and its first bounded rehearsal. |
| **When** | After Execute and implementation review, before any gateway soak or owner cutover. |
| **Why** | The architecture is race-sensitive: a green ordinary test suite cannot prove no fallback, stale promotion, lost-event drift, or mixed-mode underfill. |
| **How** | Use static inventory, independent logical/control oracles, failure injection, crash/restart tests, and the pinned Chroma 1.5.9 operational matrix. |

**TL;DR:** This VERIFY artifact will accept only mechanical evidence tied to
the exact Execute tip; architecture PASS and planning approval are not runtime
proof.

**Honest limits:** The formal TLA+ model proves the bounded authority state
machine, not Python refinement, filesystem durability, Chroma ANN behavior, or
performance. Those require the checks below.

### Merge reading

- [CG-2 architecture](ARCHITECTURE-cg2-production-activation.md)
- [CG-2 execution plan](EXECUTION-cg2-production-activation.md)
- [Active handoff](../inter-model/LATEST.md)
- [Formal model evidence](formal/cg2/README.md)
- [Exact-SHA triple delta confirmation](../inter-model/CURSOR-2026-08-15-cg2-delta-confirmation.md)

## Scope lock

| In scope | Out of scope |
|---|---|
| Global serving boundary with all owners initially legacy | Production activation of any owner |
| Authority resolution, typed fallback, retry budget, and request freezing | Corpus-wide snapshot/serializability claims |
| Source-hash promotion guard and bounded reconciliation | Guaranteeing edits after the final source check cannot occur |
| Logical completeness/purity/parity and operational diagnostics | Treating physical IDs as semantic identity |
| Chroma 1.5.9 mixed-mode control comparison and storage/reopen evidence | Exact mathematical kNN or unsupported Chroma queue surgery |
| Copied-corpus rehearsal, rollback, restart, and failure matrix | Automatic GC, compaction, or legacy retirement |

## Verification design

| Field | Answer |
|---|---|
| **Independent oracle** | Active-manifest logical sets plus an authority-clean Chroma 1.5.9 control collection; exact cosine is a secondary recall diagnostic. The formal model is a transition oracle, not an implementation oracle. |
| **Failure-injection method** | Change source during build/qualification, mutate authority evidence during resolution, lose notifications, kill processes around staging/promotion, corrupt or hide manifests, inject typed backend failures, and overlap reads with retention. |
| **Negative control** | Deliberately re-enable a raw Chroma read, physical-ID parity, broad fallback catch, wrong-generation row, dropped reconciliation sweep, or unbounded candidate query; the corresponding boundary or accounting check must fail. |
| **Dual-path coverage** | CLI search/ask/related/stats, MCP search/ask/related/stats, raw query mode, keyword/metadata fallback, `open_chroma_for_read`, readonly metadata helpers, watcher/index ingest, validator/recovery, and administrative diagnostics. |

## V0 — Preconditions and evidence identity

The following values are filled after Execute. During this planning stub they
are intentionally not PASS claims.

| Field | Planned value |
|---|---|
| `subject_tip_sha` | TBD — exact accepted Execute tip |
| `architecture_sha` | `e680ce837653698a5be8b78ba02db2f880c40c63` |
| `execution_plan_sha` | TBD — accepted execution-plan tip |
| `gate_applicability` | Recorded by Execute; VERIFY copies it |
| `bugbot_reviewed_sha` | Recorded by Execute if applicable |
| `result` | Pending Execute evidence |
| `finding_disposition` | Pending Execute evidence |
| `authority_reference` | Ryan acceptance or applicable review record |

| ID | Check | Planned status |
|---|---|---|
| V0a | Subject tip resolves to the exact implementation being verified | PLANNED |
| V0b | Execute recorded applicability, reason, and review evidence | PLANNED |
| V0c | If required, BugBot-reviewed SHA equals subject tip SHA; mismatch is FAIL | PLANNED |
| V0d | Required findings are fixed or Ryan-accepted under Execute’s lifecycle | PLANNED |
| V0e | If exempt, exemption reason and subject tip are recorded | PLANNED |

## V1 — Serving-boundary completeness

| ID | Check | Planned status |
|---|---|---|
| V1a | Static inventory classifies every serving-adjacent Chroma/SQLite read and does not pass vacuously when empty | PLANNED |
| V1b | CLI, ask, MCP related, MCP stats, raw, keyword, readonly, and metadata paths reach the gateway or are explicitly non-serving | PLANNED |
| V1c | Legacy-only gateway results match the pre-gateway reference corpus within the ratified comparison rule | PLANNED |
| V1d | No raw authority/pointer/manifest failure reaches legacy fallback | PLANNED |

## V2 — Authority resolution and fallback safety

| ID | Check | Planned status |
|---|---|---|
| V2a | Fence, pointer, manifest, retirement, and quarantine evidence are read/copy/verified without torn vectors | PLANNED |
| V2b | A post-fence resolution cannot select LEGACY; a pre-fence frozen reader may finish while retained data exists | PLANNED |
| V2c | Pointer/manifest qualification failure, integrity failure, and mixed-mode proof failure fail closed | PLANNED |
| V2d | Only the typed transient backend class can enter repository-mediated fallback with the same frozen authority vector | PLANNED |
| V2e | Attempt and elapsed budgets terminate with observable `AUTHORITY_UNSTABLE` and no rows/cache/fallback | PLANNED |

## V3 — Source freshness and reconciliation

| ID | Check | Planned status |
|---|---|---|
| V3a | Source mutation during build and after cold qualification rejects promotion without changing current authority | PLANNED |
| V3b | Startup, restart, root rebuild, overflow/uncertainty, periodic, and pre-canary reconciliation paths run | PLANNED |
| V3c | A deliberately lost notification is found and queued/quarantined within `max_reconciliation_staleness` | PLANNED |
| V3d | Reconciliation dirty state cannot be cleared by observer restart alone | PLANNED |
| V3e | Owner-local coalescing and global admission limits prevent unbounded rebuild/staging work | PLANNED |
| V3f | Symlink, hardlink, rename, delete/recreate, traversal, and trusted-root policy tests match the selected deployment policy | PLANNED |

## V4 — Logical accounting and provenance

| ID | Check | Planned status |
|---|---|---|
| V4a | Completeness and purity handle empty expected/observed sets by an explicit ratified convention | PLANNED |
| V4b | Missing, unexpected, duplicate, wrong-owner, wrong-generation, retained, abandoned, and physical-amplification cases are distinct | PLANNED |
| V4c | Historical retained rows do not count as active drift | PLANNED |
| V4d | Projection parity uses `(owner_digest, collection_kind, logical_id)`; physical-ID changes do not create semantic drift | PLANNED |
| V4e | Serving counts and physical storage/backlog counts are not conflated | PLANNED |
| V4f | Missing/unknown embedding identity and ambiguous owner/alias state block readiness rather than being inferred away | PLANNED |

## V5 — Mixed-mode backend correctness

| ID | Check | Planned status |
|---|---|---|
| V5a | The authority-clean Chroma 1.5.9 control uses matching embeddings, metric, and HNSW parameters | PLANNED |
| V5b | Mixed physical retrieval returns zero rows outside the frozen authority vector | PLANNED |
| V5c | When the clean control has `k` eligible rows, inactive/history rows do not silently underfill the mixed result within the ratified bound | PLANNED |
| V5d | Retrieval-quality divergence is reported separately from authority safety/cardinality | PLANNED |
| V5e | Unbounded or unproven candidate expansion blocks mixed-mode rollout; no raw fallback is used | PLANNED |

## V6 — Crash, rollback, retention, and recovery

| ID | Check | Planned status |
|---|---|---|
| V6a | Process death after staging, during qualification, before/after pointer publication, and during recovery leaves authority recoverable or fails closed | PLANNED |
| V6b | Active and previous generations survive a real kill during publication and restart | PLANNED |
| V6c | Rollback requalifies and republishes a retained committed generation; it never resurrects legacy rows | PLANNED |
| V6d | Recovery follows the durable pointer and never elects the most complete generation | PLANNED |
| V6e | Automatic GC and physical compaction remain disabled; protected generations are not deleted by the canary path | PLANNED |

## V7 — Operational budgets and soak readiness

| ID | Check | Planned status |
|---|---|---|
| V7a | Ratified budgets exist for gateway latency, resolution retry, reconciliation staleness, build/validation, reopen/replay, backlog, disk headroom, and amplification | PLANNED |
| V7b | Chroma 1.5.9 vector lag, queue rows, reopen duration, delete behavior, and storage growth are measured locally at representative scale | PLANNED |
| V7c | Legacy-only gateway rehearsal shows no correctness regression and acceptable latency | PLANNED |
| V7d | Shadow comparison divergence is within the ratified rule and unexplained divergence pauses rollout | PLANNED |
| V7e | Runbook names exact grants, rollback point, pause conditions, and evidence artifacts | PLANNED |

## V8 — Independent sign-off and Ryan GATE

| ID | Check | Planned status |
|---|---|---|
| V8a | Kiro or Ryan-named independent reviewer signs the exact Execute tip and residual risks | PENDING POST-EXECUTE |
| V8b | Ryan decides whether to accept the implementation package and separately whether to grant legacy-only soak | PENDING RYAN GATE |
| V8c | Any first-owner activation packet names the exact owner, SHA, rollback generation, doctor evidence, and operation grant | PENDING FUTURE ACTIVATION |

Verifier performs no cleanup or correction. A failed check returns to the
execution/revision lane; it does not become an implicit degraded activation.

## Evidence log

```text
VERIFY-cg2-production-activation — planning stub
Architecture baseline: e680ce837653698a5be8b78ba02db2f880c40c63
Execution tip: TBD
Mechanical run: not run — Execute has not started
Independent sign-off: pending
Ryan GATE: pending
```
