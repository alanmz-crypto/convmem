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
real-Chroma fault/replay review, a one-shot exact-resource production canary
has measured frontier reuse and the cross-collection visibility/recovery seam,
and a separately authorized activation can later enable one controlled Kiro
source without changing chunking, retrieval, or other adapters. Production
activation is not part of the current phase.

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
| `incremental_jsonl.py` | Production coordinator on `main` via PR #293; the implementation is default-off and includes the reviewed pylint-regression correction. Live enable without `CONVMEM_INCREMENTAL_ROOT` fail-closed skips rather than writing. |
| `ingest.py` | Build/commit split; default-off dispatch after detect; content-addressed UUID4 ingest assertion IDs |
| `adapters/kiro_session_jsonl.py` | `parse()` unchanged; `parse_complete_prefix()` adds byte ranges |
| `config.py` / `config.example.toml` | `[index.incremental_jsonl]` absent/false by default |
| `chroma_store.py` | Source-scoped snapshot/restore primitives |
| `watch.py` | Unchanged; still `convmem index --file` |
| `incremental_jsonl_isolation.py` | Hermetic T0 boundary; `-I` workers get host site via `CONVMEM_INCREMENTAL_SITE` |
| `incremental_jsonl_canary.py` | P1 hermetic canary harness on `feat/2026-09-10-codex-jsonl-production-canary-p1`; grant boundary, Gate 0, capsule, faults, serving probe, chunking rehearsal |
| `scripts/run-jsonl-production-canary.py` | Thin explicit launcher; not registered in CLI or watcher |
| `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` | Kiro-reviewed canary architecture; PASS at `8b48a39` via PR #295 |
| `docs/plans/EXECUTION-codex-jsonl-production-canary.md` | Two-grant P1/P2 plan merged via PR #295 |
| `docs/plans/VERIFY-codex-jsonl-production-canary.md` | P1 hermetic harness evidence on the feature branch |
| `docs/plans/VERIFY-codex-jsonl-production-integration.md` | Cursor T0–T6 evidence |
| Scratch prototype + canary on `main` | Unchanged inherited evidence |

PR #293 was squash-merged as `881133d`. PR #295 merged the canary
architecture/plan at `b23cabad`. P1 hermetic harness evidence is on
`feat/2026-09-10-codex-jsonl-production-canary-p1` awaiting exact-tip Kiro
review. No live config, production Chroma, watcher, provider, P2 run, PR, or
activation exists.

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Scratch JSONL state machine | **DONE on `main`** (PR #289) | — |
| Isolated real-Chroma writer/pruner pass | **DONE on `main`** (PR #291) | — |
| Read-only live-source canary | **DONE on `main`** (PR #292) | — |
| Production architecture | **PASS at `84ec51a`** | — |
| Bounded Execute plan | **PASS / AUTHORIZED** | — |
| Ryan architecture/Execute acceptance | **DONE 2026-09-10** | — |
| Cursor implementation | **DONE on `main`** via PR #293 (`881133d`) | — |
| Implementation review/PR | **DONE**; Kiro exact-tip PASS at `17d7e23`, six CI checks PASS, squash-merged as `881133d` | — |
| Production-canary architecture/plan | **DONE on `main`** via PR #295 (`b23cabad`); Kiro PASS at `8b48a39` | — |
| P1 hermetic canary harness | **DONE on feature branch**; exact tip pushed for Kiro review | Kiro exact-tip review, then Ryan PR decision |
| P2 one-source live canary | **UNAUTHORIZED** | P1 review/merge + exact grant digest + Ryan authorization |
| Watcher/feature activation | **UNAUTHORIZED** | Separate evidence and Ryan decision |

## 5. Your Role

**If Ryan sent you to review P1:** you are Kiro. Re-run the focused hermetic
matrix from `docs/plans/VERIFY-codex-jsonl-production-canary.md` at the exact
pushed tip of `feat/2026-09-10-codex-jsonl-production-canary-p1`. Do not run
P2, live resources, repo-wide pytest, or open a PR on Ryan's behalf.

**If Ryan sent you to implement P2 or activate:** stop. P2 and activation remain
separately authorized. P1 merge does not authorize them.

**If Ryan sent you to merge:** Ryan alone decides PR creation after Kiro PASS.
Cursor must not open the PR.

## 6. What Remains Before Live (sequential)

1. Kiro exact-tip review of P1 harness evidence on
   `feat/2026-09-10-codex-jsonl-production-canary-p1`.
2. Ryan separately decides PR creation and merge of P1.
3. The dedicated Kiro session grows through ordinary use from the current 16
   accepted messages to 61–109; canary tooling never edits it.
4. After P1 merges, Kiro reviews a fresh exact-source grant packet and Ryan
   separately decides whether to authorize one P2 run.
5. P2 measures real frontier calls, selected crash replay, rollback, and
   cross-collection serving visibility, then stops at evidence.
6. Independent review decides whether activation should be planned at all.
7. Ryan alone edits live configuration or activates the watcher route.

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
| Production-canary architecture | `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` |
| Production-canary execution plan | `docs/plans/EXECUTION-codex-jsonl-production-canary.md` |
| Current arc snapshot | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Cursor T0–T6 evidence | `docs/plans/VERIFY-codex-jsonl-production-integration.md` |
| Scratch evidence | `docs/inter-model/VERIFY-jsonl-incremental-scratch-prototype.md` |
| Live-source canary evidence | `docs/inter-model/VERIFY-jsonl-incremental-live-source-canary.md` |
| P1 harness evidence | `docs/plans/VERIFY-codex-jsonl-production-canary.md` |
| P1 Execute handoff | `docs/inter-model/CODEX-2026-09-10-jsonl-production-canary-p1-execute.md` |
| Canary harness | `incremental_jsonl_canary.py`, `scripts/run-jsonl-production-canary.py` |
| Kiro review handoff | `docs/inter-model/CURSOR-2026-09-10-jsonl-production-integration-review.md` |
| Production ingest | `ingest.py` |
| Incremental coordinator | `incremental_jsonl.py` |
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
| 2026-09-09 | Codex | Applied Kiro C1–C3 precision review: accurate processed-state sidecar/source-lock interval, named source-before-export invariant, and explicit new incremental prune trigger |
| 2026-09-10 | Codex | Finalized C1 to preserve the standalone processed-state critical section after releasing the source-locked apply; C2/C3 remain confirmed |
| 2026-09-10 | Codex | Recorded Kiro PASS at `84ec51a` and Ryan's bounded Cursor T0–T6 Execute grant; implementation remains not started and operational actions remain gated |
| 2026-09-10 | Cursor | Landed hermetic T0–T6 on `feat/2026-09-10-codex-jsonl-production-integration` at `5341bb1`; next lane is exact-tip Kiro review. No PR, live indexing, or activation |
| 2026-09-10 | Codex | Opened PR #293 after Kiro PASS at `162d67f`; corrected the CI pylint-regression delta without changing the baseline and removed a full-suite test reload-order dependency, routing the new exact tip back to Kiro before merge |
| 2026-09-10 | Codex | Recorded Kiro's corrected-tip PASS at `17d7e23` and Ryan's squash merge of disabled production integration via PR #293 as `881133d`; live bootstrap, canary, and activation remain unauthorized |
| 2026-09-10 | Codex | Drafted the two-grant production-canary architecture and execution plan around a dedicated new Kiro source; next lane is Kiro design review, with P1/P2 still unauthorized |
| 2026-09-10 | Codex | Applied Kiro C1–C3: corrected the 110/111 append boundary, canonicalized the embedding tag in the grant, and added plan jargon glossaries; awaiting narrow confirmation |
| 2026-09-10 | Cursor | Landed hermetic P1 canary harness on `feat/2026-09-10-codex-jsonl-production-canary-p1`; next lane is exact-tip Kiro review. No PR, P2, or activation |

## TL;DR

- Arc Codex production code is on `main` via PR #293 (`881133d`) and remains
  disabled by default.
- The canary architecture/plan merged via PR #295 (`b23cabad`); P1 hermetic
  harness evidence is pushed on `feat/2026-09-10-codex-jsonl-production-canary-p1`
  for exact-tip Kiro review.
- P2, PR creation, live indexing, providers, and activation remain separately
  Ryan-gated.
