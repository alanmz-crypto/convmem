# Execution Plan — CG-2 production activation

```text
Planning Status

Phase:        Execution Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Codex authors; Kiro reviews; Cursor downstream implementation
Authority:    Awaiting HITL approval of this execution plan
```

**Source:** Ryan Architecture HITL lock recorded in `47768d1`, against the
approved CG-2 architecture at `e680ce837653698a5be8b78ba02db2f880c40c63`.

**Goal:** Put a single, fail-closed serving-authority boundary in front of
ConvMem production reads, prepare bounded per-owner generation migration, and
prove the first legacy-only and canary steps without activating a production
owner in this plan.

**Plan status:** Planning artifact only. No implementation, configuration,
production gateway soak, owner cutover, physical deletion, or GC is authorized
by this document.

## Human consequence

If Ryan approves this execution plan, Cursor receives five bounded tasks for
implementation and rehearsal. The first runtime milestone keeps every owner in
explicit legacy compatibility while proving that all production reads pass
through one authority layer. A later, separately granted canary may activate
one eligible owner after the evidence gates pass. The largest deliberate
trade-off is that automatic reclamation remains disabled, so storage may grow
during qualification and rollback testing.

## Locked direction

Execution must translate the approved architecture; it must not reopen these
decisions:

- CG-1 path-derived owner identity remains authoritative.
- Canonical rename is explicit old-owner → new-owner migration; stable logical
  owner IDs and a mutable locator registry are out of scope.
- Every serving read resolves an immutable request authority vector through one
  gateway/repository boundary.
- Legacy compatibility is an explicit authority mode, never an error fallback.
- Pointer qualification, active-generation comparison, and current-source hash
  revalidation are mandatory promotion checks.
- Filesystem notifications schedule work; bounded reconciliation proves source
  convergence even when notifications are lost.
- Authority and integrity failures fail closed; only a typed, repository-
  mediated transient backend failure may use an existing compatible fallback.
- Logical IDs, not generation-specific physical IDs, define parity and drift.
- The previous committed generation is retained for rollback; automatic GC and
  physical compaction are disabled in the first activation slice.
- Chroma 1.5.9 mixed-mode behavior must be measured against an authority-clean
  control before any generational owner can serve.

## Scope boundary

### In scope

- A serving-authority gateway/repository and request-frozen authority vector.
- Typed failure domains, bounded authority-resolution retry, and structural
  fallback mediation.
- Routing all known and discovered serving-adjacent Chroma/SQLite reads through
  the boundary, including `ask`, CLI search, MCP related, MCP stats, raw query,
  keyword fallback, `open_chroma_for_read`, and metadata helpers.
- Mandatory source-observation binding at production promotion.
- Watcher-independent startup, restart, overflow, periodic, and pre-canary
  source reconciliation with bounded admission and owner-local coalescing.
- Logical completeness/purity/parity accounting and serving-versus-physical
  statistics.
- Chroma 1.5.9 mixed-mode query characterization, authority-clean control
  construction, queue/reopen/storage measurements, and a no-GC lifecycle.
- Copied-corpus rehearsal, rollback/restart/failure evidence, runbook updates,
  and the filled VERIFY artifact after Execute.

### Out of scope

- Any production owner cutover, legacy fence publication, or activation grant.
- Editing live configuration, creating a production activation manifest, or
  switching the serving gateway in production.
- Automatic inactive-generation deletion, online leases, compaction, or direct
  manipulation of Chroma internal queues.
- Corpus-wide migration, corpus-wide atomicity, stable owner IDs, or automatic
  hardlink merging.
- Canonical rename migration in the first canary slice.
- Changes to Chroma durability pragmas or a new power-loss guarantee.
- A claim of exact k-nearest-neighbor retrieval, serializability, or corpus-wide
  snapshot isolation.
- Unbounded queueing, preservation of every intermediate source edit, or
  implementation of unrelated doctor warnings.

## Ordered tasks

| ID | Deliverable | In scope | Depends on | Gates | Execution lane |
|---|---|---|---|---|---|
| **T1** | Serving authority gateway and boundary enforcement | Authority resolver, request-frozen vector, explicit `LEGACY`/`GENERATIONAL`/`FENCED`/`QUARANTINED` modes, typed failures, retry budget, mediated fallback, all serving entry points and boundary inventory | — | Legacy behavior equivalence; zero unclassified serving reads; authority/integrity failures never fall back; resolver retry terminates; focused and full tests | Cursor |
| **T2** | Source freshness and reconciliation | Secure source observation, mandatory promotion hash check, watcher-independent reconciler, overflow/restart/startup/pre-canary sweeps, bounded queues and owner-local coalescing | T1 | Source changes during build and after qualification refuse promotion; lost-event recovery meets `max_reconciliation_staleness`; no unbounded admission; path policy tests | Cursor |
| **T3** | Logical accounting and operational authority diagnostics | Namespaced parity/drift identity, completeness/purity/duplicate/wrong-generation diagnostics, serving/physical stats split, owner retirement/quarantine evidence, embedding provenance, backlog/storage/reopen metrics | T1; T2 for source-state reporting | Artificial accounting fixtures classify every case; historical rows are not drift; metrics are bounded and redacted; doctor/parity focused tests | Cursor |
| **T4** | Mixed-mode backend and lifecycle proof | Chroma 1.5.9 authority-clean control collection, filtered/expanded candidate strategy, authority safety/cardinality/quality measurements, queue/reopen/storage characterization, retention and GC-off enforcement | T1; T3 for logical oracle | Representative-scale spike passes ratified authority/cardinality budgets or blocks mixed-mode; no raw queue surgery; active/previous/candidate retention survives restart and kill tests | Cursor |
| **T5** | Copied-corpus rehearsal and activation-readiness packet | Legacy-only gateway rehearsal, shadow comparison, rollback/restart/failure matrix, implementation-to-model mapping, performance budgets, operator runbook, filled VERIFY evidence after Execute | T1–T4 | Full suite; independent safety review; exact pinned-Chroma evidence; no unexplained divergence; separate Ryan grants recorded as pending, not inferred | Cursor + designated reviewers |

T2 and T3 may proceed in parallel after T1's interfaces stabilize. T4's
backend spike may begin after T1, but its acceptance decision depends on T3's
logical oracle. T5 is serial after the preceding task gates.

## Task gates and stop conditions

### T1 — global boundary first

The implementation must preserve legacy query results while routing every
serving operation through the authority layer. A static inventory is necessary
but insufficient: helpers beneath `query.py`, `chroma_readonly`, and metadata
fallbacks must be classified as serving, core storage, validation,
administrative, or separately governed infrastructure. An empty or disabled
inventory is a test failure, not proof of zero bypasses.

Stop immediately if an authority, pointer, manifest, fence, quarantine, or
mixed-mode proof error can reach an unmediated legacy read. Do not widen a
catch-all exception to make legacy tests pass.

### T2 — source convergence before promotion

Build from a securely opened source object or private byte snapshot. While the
owner lock is held, recompute the current source observation and require it to
match the candidate manifest before pointer publication. A mismatch queues the
latest desired state and leaves the current authority unchanged.

The reconciler must run independently of watcher overflow reporting and retain
an observable dirty state until a successful sweep. Reconciliation work is
bounded globally and per owner; superseded edits coalesce to the latest desired
state.

### T3 — logical truth before migration

Doctor and parity must compare `(owner_digest, collection_kind, logical_id)`.
Physical Chroma IDs remain diagnostic provenance. Invalid authority is an
authority failure, not a percentage score. Unknown embedding identity,
ambiguous aliases, and unresolved owner migration state block canary selection.

### T4 — backend proof before mixed mode

Use a temporary Chroma 1.5.9 collection containing only rows admitted by the
frozen authority vector as the primary control. Keep exact cosine as a secondary
recall diagnostic. Measure separately:

1. authority safety — zero unauthorized rows;
2. authorized cardinality — no silent underfill when the clean control has `k`;
3. retrieval quality — divergence from the clean control under the ordinary ANN
   contract.

If no bounded candidate strategy satisfies the first two properties, mixed-mode
activation is blocked and the architecture must be revisited. There is no
degraded raw-query path.

### T5 — evidence and grants remain separate

The copied-corpus rehearsal may exercise a canary-like owner in an isolated
root. It may not publish a production fence or pointer. A legacy-only production
gateway soak requires its own exact operation grant. A first-owner canary
requires a later named-owner grant. GC requires a separate sub-gate.

## Architecture-model refinement map

| Model property | Execution owner | Required evidence |
|---|---|---|
| `QualifiedPointerServes`, `SingleCurrentAuthority` | T1 | Resolver and recovery tests against exact pointer/manifest |
| `PostFenceNeverLegacy`, `FrozenLegacyProtected` | T1/T5 | Fence race and frozen-reader tests |
| `PromotionChecksRecorded` | T2 | Active-generation and source-hash stale-candidate tests |
| `LostDriftEventuallyHandled` | T2 | Lost notification, restart, overflow, and periodic sweep tests |
| `RecoveryUsesExactPointer` | T1/T5 | Corrupt/incomplete historical generation recovery tests |
| `GCRespectsProtection` | T4/T5 | Retention accounting; deletion remains disabled in first slice |
| `TentativePinWindowProtected` | T4 | Read/retention interleaving tests; online GC remains off |
| `RenameVectorExclusive`, `RenameGroupStable` | T3/T5 | Explicit rename policy tests; first canary excludes live rename |
| `FrozenGenerationStable` | T1 | Request-frozen vector overlap tests |
| `RetryBudgetTerminates` | T1 | Attempt and elapsed-time budget tests with `AUTHORITY_UNSTABLE` |
| `AuthorityFailuresNeverFallback`, `FallbackIsMediated` | T1 | Typed failure injection and no-bypass tests |

## Evidence requirements for Execute

- Exact implementation tip SHA and branch for every task.
- Focused CG-2 tests plus the complete repository suite; no unexplained
  failures.
- Static and runtime serving-boundary inventory with all serving-adjacent reads
  classified.
- Concurrency, path-race, source-change, lost-notification, process-kill,
  promotion, restart, and rollback evidence.
- Chroma 1.5.9 measurements using the pinned version, including control-view
  comparison, vector lag, reopen time, queue/backlog, deletion behavior, and
  physical amplification.
- Ratified numeric budgets for authority resolution, reconciliation staleness,
  read latency, build/cold-validation time, storage headroom, and recovery.
- The Execute phase must record the external-review applicability decision and
  any required BugBot evidence for the accepted implementation tip; VERIFY
  copies that decision and does not invent one.

## Arc VERIFY companion

- **Path:** `docs/plans/VERIFY-cg2-production-activation.md`
- **Status:** planning stub; no Execute evidence yet
- **Template:** `docs/plans/VERIFY-TEMPLATE.md`
- **Scope:** prove the implementation and rehearsal against this plan and the
  locked architecture; do not treat the planning stub as an activation grant.

## Stop points and authority

| Stop point | Required decision | Owner |
|---|---|---|
| Before implementation | Execution-plan review PASS | Kiro/design lane; Ryan HITL |
| Before any code/runtime change | Execute grant for exact plan and branch | Ryan |
| Before legacy-only production gateway soak | Exact operation grant | Ryan |
| Before first generational owner | Named owner, SHA, rollback point, and activation grant | Ryan |
| Before automatic deletion/GC | Independent read-pin, deletion, crash, and Chroma evidence plus sub-grant | Ryan |

No plan approval implies implementation authority. No implementation merge
implies production authority. No gateway soak implies owner activation.

## Execute entry

- **First task:** T1 after this plan receives designated review and Ryan
  approves the Execute scope.
- **Implementation branch:** fresh Cursor branch from the accepted main/CG-1
  baseline; do not place runtime code on this planning branch.
- **Required companion:** keep `VERIFY-cg2-production-activation.md` updated as
  a stub during Execute, then fill it only from mechanical evidence.
