# Arc Brief — Kiro JSONL Incremental Production Integration

> **Arc: Codex. Every model working on this arc must read this file first.**
> State the product goal, your role, current system state, and next action before
> doing substantive work.

---

## 1. What This Is For (product goal)

ConvMem currently reprocesses an entire Kiro session transcript whenever its
append-heavy `messages.jsonl` changes. Arc Codex aims to make repeated indexing
incremental and crash-replayable: reuse stable historical chunks, transform
only the overlap frontier and new messages, and never pay twice for a completed
transform after a crash.

**Done means:** disabled-by-default production code has passed hermetic
real-Chroma fault/replay review; a separately authorized activation can later
enable one controlled Kiro source without changing chunking, retrieval, or
other adapters. Production activation is not part of the current phase.

## 2. System Design (how the pieces connect)

```text
Kiro sess_*/messages.jsonl (read-only source authority)
                   |
                   v
          normal adapter detection
                   |
       flag off/non-Kiro ─────────> legacy whole-file ingest
                   |
                   v
      IncrementalJsonlCoordinator
        | source prefix snapshot + continuity
        | overlap-aware chunk frontier
        | fsynced prepared transform cache
        | checkpoint + transaction + rollback journal
        v
       existing governed writer/pruner
          |                     |
          v                     v
 conversation_summaries   knowledge_units
          \_____________________/
                    |
          checkpoint commits first
                    |
          export/dedupe/processed followers
```

Key invariants:

- source JSONL is source authority; checkpoint is processing/recovery
  authority; Chroma and sidecars are derived projections;
- absent/false feature configuration is the current path unchanged;
- only `jsonl_kiro_session` is eligible;
- a selected complete prefix may be followed by a pure append, but cannot be
  replaced, truncated, or mutated before commit;
- expensive outputs are fsynced before any Chroma write;
- both real Chroma collections converge or restore from exact before-images;
- `processed.json` cannot advance before checkpoint authority; and
- all implementation verification is temporary, local, network-denied, and
  provider-free.

## 3. What Exists Right Now (file map)

| Surface | Current state |
|---|---|
| `scratch_jsonl_prototype/engine.py` | Reviewed scratch state machine on `main`: prefix, continuity, frontier, generation, replay, fallback, crash transitions |
| `scratch_jsonl_prototype/chroma_projection.py` | Reviewed isolated bridge through the real production Chroma writer/pruner on `main` |
| `scratch_jsonl_prototype/live_source_canary.py` | Reviewed one-shot read-only live-source canary on `main`; no production write or activation |
| `docs/inter-model/VERIFY-jsonl-incremental-scratch-prototype.md` | Scratch and real-Chroma evidence, limits, and execution incident disclosure |
| `docs/inter-model/VERIFY-jsonl-incremental-live-source-canary.md` | Frozen-source canary evidence plus deterministic-test correction |
| `ingest.py` | Production whole-file transform/write/prune path; no incremental dispatch yet |
| `adapters/kiro_session_jsonl.py` | Production Kiro parser; currently materializes the full message list and exposes no byte ranges |
| `watch.py` | Debounced subprocess caller of `convmem index --file`; watcher is currently stopped by Ryan and is not controlled by this arc |
| `chroma_write_store.py` / `chroma_store.py` | Governed production writer session and source-scoped operations; no production transaction journal |
| `docs/plans/ARCHITECTURE-codex-jsonl-production-integration.md` | Proposed production architecture on the planning branch; awaiting Kiro review |
| `docs/plans/EXECUTION-codex-jsonl-production-integration.md` | Proposed bounded Cursor Execute plan on the planning branch; awaiting Kiro review |

No production implementation, live config change, source checkpoint, provider
call, watcher action, migration, or activation exists in Arc Codex.

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Scratch JSONL state machine | **DONE on `main`** (PR #289) | — |
| Isolated real-Chroma writer/pruner pass | **DONE on `main`** (PR #291) | — |
| Read-only live-source canary | **DONE on `main`** (PR #292) | — |
| Production architecture | **CORRECTED on planning branch** | Narrow Kiro confirmation of C1–C3 |
| Bounded Execute plan | **CORRECTED on planning branch** | Narrow Kiro confirmation of C1–C3 |
| Ryan architecture/Execute acceptance | **NOT STARTED** | Kiro confirms corrected tip |
| Cursor implementation | **UNAUTHORIZED / NOT STARTED** | Kiro PASS then separate Ryan Execute grant |
| Implementation review/PR | **NOT STARTED** | Successful bounded Cursor evidence |
| Production bootstrap/canary | **UNAUTHORIZED** | Separate post-merge Ryan grant |
| Watcher/feature activation | **UNAUTHORIZED** | Separate evidence and Ryan decision |

## 5. Your Role

**If Ryan sent you to review now:** you are Kiro. Confirm only the C1–C3
precision revision: the real processed-state sidecar lock and source-lock
commit interval, the named source-before-export invariant, and the new
incremental prune trigger. Do not reopen accepted design or implement/run live
indexing.

**If Ryan later sent you to implement:** you are Cursor and must have a
separate explicit Execute grant. Follow the ordered T0–T6 plan, stop on a
concrete architecture contradiction, use only temporary paths and deterministic
fakes, and stop at evidence for Kiro.

**If Ryan sent you to activate:** stop unless the exact source, live config
change, provider/cost boundary, watcher state, rollback action, and canary stop
condition are separately authorized. Merge of disabled code is not activation.

## 6. What Remains Before Live (sequential)

1. Kiro confirms the C1–C3 documentation correction at the new exact tip.
2. Ryan accepts the architecture and separately authorizes Cursor Execute.
3. Cursor implements T0–T6 with no live resources or provider calls.
4. Kiro independently reviews the exact implementation/evidence tip.
5. Ryan decides whether to open/merge the disabled implementation PR.
6. After merge, Ryan separately chooses a new source or authorizes a one-time
   clean bootstrap rebuild and its model-cost ceiling.
7. A bounded production-path canary measures cross-collection mixed visibility,
   replay time, frontier calls, and rollback under an exact source/grant.
8. Independent review decides whether watcher/feature activation is safe.
9. Ryan alone edits live configuration or activates the watcher route.

## 7. Hard Stops

| Stop | Owner | What it blocks |
|---|---|---|
| Architecture/plan review | Kiro | Cursor implementation before independent design review |
| Execute grant | Ryan | Any production-code implementation |
| Default-off flag | Live config + Ryan | Incremental routing in production |
| Bootstrap required | Separate Ryan grant | Adoption/rebuild of existing indexed sources and associated model cost |
| Implementation evidence review | Kiro | PR disposition and any production canary |
| Production canary | Ryan | Live source/Chroma/config/provider operation |
| Activation | Ryan | Feature enablement and watcher participation |

No model may infer one gate from another. In particular, plan PASS, code merge,
or canary PASS does not enable production indexing.

## 8. Relationship to ConvMem

Arc Codex changes the ingestion efficiency and recovery mechanism for one
adapter. It does not change ConvMem's source/projection authority direction,
retrieval scoring, semantic calibration, or other active arcs.

- The source transcript remains authoritative input.
- Chroma remains the serving projection used by current retrieval.
- The production writer gate, source locks, exclusion/purge rules, Shadow
  mutation observation, and R2b writer inventories remain in force.
- Recovery Authority and CG-2 govern different production authority changes;
  Arc Codex cannot invoke their operations.
- The drifting live golden retrieval baseline is unrelated to this planning
  diff and is not run or retuned here.

The known cross-collection atomicity seam is not declared solved: Chroma has no
atomic two-collection transaction. The before-image journal makes a torn apply
recoverable, while a later canary must measure how long mixed state can remain
visible to readers.

## 9. Key Design Files

| Purpose | Path |
|---|---|
| Production architecture | `docs/plans/ARCHITECTURE-codex-jsonl-production-integration.md` |
| Bounded implementation plan | `docs/plans/EXECUTION-codex-jsonl-production-integration.md` |
| Current arc snapshot | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Scratch evidence | `docs/inter-model/VERIFY-jsonl-incremental-scratch-prototype.md` |
| Live-source canary evidence | `docs/inter-model/VERIFY-jsonl-incremental-live-source-canary.md` |
| Review handoff | `docs/inter-model/CODEX-2026-09-09-jsonl-production-integration-review.md` |
| Production ingest | `ingest.py` |
| Kiro adapter | `adapters/kiro_session_jsonl.py` |
| Production writer/store | `chroma_write_store.py`, `chroma_store.py` |

## 10. How to Update This Brief

Keep this document a current-state snapshot, not a session diary.

1. Overwrite sections 3–6 after a milestone moves; do not append narrative.
2. Change branch-only state to `main` only after verifying the merge.
3. Rewrite section 5 for the next lane.
4. Remove completed work from the forward sequence.
5. Add one milestone-level Update Log row.
6. Preserve hard stops until Ryan explicitly crosses them.
7. Test: a fresh model should know the current authority and next action from
   this file alone.

### Update Log

| Date | Who | Change |
|---|---|---|
| 2026-09-09 | Codex | Created Arc Codex production-integration architecture, bounded Execute plan, and Kiro review boundary after merged scratch/canary evidence |
| 2026-09-09 | Codex | Applied Kiro C1–C3 precision review: accurate processed sidecar/source-lock interval, named source-before-export invariant, and explicit new incremental prune trigger |

## TL;DR

- Arc Codex has reviewed scratch and live-source evidence on `main`; only the
  production Architecture and Execute plan exist on the current branch.
- Next is narrow Kiro confirmation of C1–C3, not implementation.
- Cursor, live indexing, providers, migration, PR creation, and activation all
  remain separately Ryan-gated.
