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
| `incremental_jsonl_canary.py` | P1 hermetic canary harness on `main` via PR #296; grant boundary, Gate 0, capsule, faults, serving probe, chunking rehearsal, and grant-listed outer writer scope |
| `scripts/run-jsonl-production-canary.py` | Thin explicit launcher; not registered in CLI or watcher |
| `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` | Kiro-reviewed canary architecture; PASS at `8b48a39` via PR #295 |
| `docs/plans/EXECUTION-codex-jsonl-production-canary.md` | Two-grant P1/P2 plan merged via PR #295 |
| `docs/plans/VERIFY-codex-jsonl-production-canary.md` | P1 hermetic harness evidence on `main`; final reviewed head `40b8c11`, 128 focused tests, scoped pylint 10.00/10 |
| `docs/plans/VERIFY-codex-jsonl-production-integration.md` | Cursor T0–T6 evidence |
| Scratch prototype + canary on `main` | Unchanged inherited evidence |

PR #293 was squash-merged as `881133d`. PR #295 merged the canary
architecture/plan at `b23cabad`. PR #296 merged the P1 hermetic harness as
`907c828` after Kiro PASS at final PR head `40b8c11` and six green CI checks.
The final corrections pin replay to the grant-listed temporary writer lease and
confine network denial to its subprocess worker. No live config, production
Chroma, watcher, provider, P2 run, or activation exists.

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
| P1 hermetic canary harness | **DONE on `main`** via PR #296 (`907c828`); Kiro PASS at final head `40b8c11`, six CI checks green, 128 focused tests PASS | — |
| P2 transfer seam corrective | **AUTHORIZED (not yet implemented)**; Ryan 2026-09-11 grant; Kiro Execute-brief PASS_WITH_CORRECTIONS at `245db63` | Cursor hermetic positive-capability + Gate 0 + P2-T3–T6 orchestration; stop at pushed evidence for Kiro |
| P2 one-source live canary | **UNAUTHORIZED**; source eligible at 68 accepted messages; no executable grant digest | Corrective merge + Kiro review + fresh Gate 0 + Ryan exact-digest authorization |
| Watcher/feature activation | **UNAUTHORIZED** | Separate evidence and Ryan decision |

## 5. Your Role

**If Ryan sent you to implement the P2 corrective pass:** you are Cursor. Read
`docs/inter-model/CODEX-2026-09-11-jsonl-production-canary-p2-corrective-execute.md`
and implement only the positive exact-resource capability mode, full twelve-part
Gate 0, and hermetic P2-T3–T6 orchestration under production-shaped temporary
paths. Preserve P1 production denial and default-off CLI/watcher behavior. Stop
at pushed evidence for Kiro. Do not run live P2, issue a grant digest, open a
PR, or activate.

**If Ryan sent you to execute live P2 or activate:** stop unless Ryan supplied
the separate, reviewed exact-resource P2 grant and its digest after corrective
code merges and Kiro review. P1 merge and corrective authorization do not
authorize live operations or activation.

## 6. What Remains Before Live (sequential)

1. Cursor implements the authorized P2 corrective pass and stops at pushed
   evidence for Kiro review.
2. Kiro reviews the exact corrective tip; Ryan separately decides PR/merge.
3. After corrective merge, revalidate the still-closed source; if it remains
   eligible, freeze every remaining grant field and obtain Kiro review plus
   Ryan's exact-digest authorization.
4. Only under that grant, Cursor runs P2 against the named resources and stops
   at evidence. P2 measures real frontier calls, selected crash replay,
   rollback, and cross-collection serving visibility.
5. Independent review decides whether activation should be planned at all.
6. Ryan alone edits live configuration or activates the watcher route.

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
| P2 corrective Execute handoff | `docs/inter-model/CODEX-2026-09-11-jsonl-production-canary-p2-corrective-execute.md` |
| P2 blocked packet | `docs/inter-model/CODEX-2026-09-11-jsonl-production-canary-p2-grant-packet.md` |
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
| 2026-09-10 | Codex | Opened PR #296 after Kiro PASS; corrected CI lint findings, restored the planned grant-listed outer writer lease after sandbox evidence caught a production-lock escape, and confined network denial to its test worker; corrected tip awaits CI and narrow Kiro recheck |
| 2026-09-10 | Codex | Recorded Kiro PASS at final PR #296 head `40b8c11` and Ryan's squash merge of the P1 hermetic canary harness as `907c828`; P2 remains unauthorized pending session readiness and a separately reviewed exact-resource grant |
| 2026-09-11 | Codex | Froze the eligible source at 68 accepted messages and prepared a blocked P2 review packet after confirming merged P1 rejects live resources and lacks executable P2 Gate 0/orchestration; no grant digest or operation was issued |
| 2026-09-11 | Codex | Recorded Kiro PASS on PR #298 packet at `77e6e2e` and Ryan's authorization of the hermetic P2 corrective Execute handoff; next lane is Cursor implementation |
| 2026-09-11 | Kiro | Execute-brief review PASS_WITH_CORRECTIONS at `245db63`; editorial P2-C13 renumber only; Cursor may begin C0–C4 |

## TL;DR

- Arc Codex production code is on `main` via PR #293 (`881133d`) and remains
  disabled by default.
- The canary architecture/plan merged via PR #295 (`b23cabad`), and the P1
  hermetic harness merged via PR #296 (`907c828`) after Kiro PASS and green CI.
- Kiro PASS on the blocked P2 packet landed via PR #298 (`8741774`); Ryan
  authorized the hermetic corrective implementation pass on 2026-09-11.
- Cursor implements positive P2 capability mode, full Gate 0, and P2-T3–T6
  orchestration under temporary production-shaped paths, then stops for Kiro.
- Live P2, grant digest issuance, PR, and activation remain separately gated.
