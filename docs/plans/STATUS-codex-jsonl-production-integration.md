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
| `incremental_jsonl.py` | Default-off production coordinator on `main`; rollback-only capture/restore covers processed, checkpoint/state, prepared, and dedupe files, with dedupe routed through the exact-resource boundary. Live enable without `CONVMEM_INCREMENTAL_ROOT` fail-closed skips rather than writing. |
| `ingest.py` | Build/commit split; default-off dispatch after detect; content-addressed UUID4 ingest assertion IDs |
| `adapters/kiro_session_jsonl.py` | `parse()` unchanged; `parse_complete_prefix()` adds byte ranges |
| `config.py` / `config.example.toml` | `[index.incremental_jsonl]` absent/false by default |
| `chroma_store.py` | Source-scoped snapshot/restore primitives |
| `watch.py` | Unchanged; still `convmem index --file` |
| `incremental_jsonl_isolation.py` | Hermetic T0 boundary; `-I` workers get host site via `CONVMEM_INCREMENTAL_SITE` |
| `incremental_jsonl_canary.py` | P1 harness plus v1 hermetic P2 fixture; live P2 fails closed on v1. The merged exact-resource v2 grant schema requires resource identities, persistent configuration, installed model manifests, and restic binding. |
| `incremental_jsonl_canary_p2.py` | Production-owned `p2-exact-resource-v2` runtime on `main` via PR #301 (`8983a6fc`), including pure Gate 0, prepared-resource receipts, overlay-content binding, durable stage budgets, and exact-resource rollback enforcement. |
| `incremental_jsonl_canary_network.py` | Loopback-allowing, fail-closed network policy shared by Gate 0 and the live worker |
| `incremental_jsonl_canary_live_worker.py` | Live worker; installs network/service denial before provider imports; `t5-bind` binds the second append before T5 |
| `scripts/run-jsonl-production-canary.py` | Explicit P1/P2 launcher; live P2 is one-stage only; `--stage t5-bind-append` binds the second append; `p2-all` is refused |
| `chroma_readonly.py` | Extended with source-path counts for Gate 0; still SQLite `mode=ro` |
| `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` | Kiro-reviewed canary architecture; PASS at `8b48a39` via PR #295 |
| `docs/plans/EXECUTION-codex-jsonl-production-canary.md` | Two-grant P1/P2 plan merged via PR #295 |
| `docs/plans/VERIFY-codex-jsonl-production-canary.md` | P1 and P2 implementation evidence through the final PR #301 corrective; Kiro's exact-tip and post-merge audits PASSed. |
| `docs/inter-model/CODEX-2026-09-12-jsonl-production-canary-p2-v2-grant-packet.md` | Fresh source freeze: eligible at 68 accepted messages. Complete v2 grant and digest intentionally blocked because only source/metadata reads were authorized. |
| `docs/plans/VERIFY-codex-jsonl-production-integration.md` | Cursor T0–T6 evidence |
| Scratch prototype + canary on `main` | Unchanged inherited evidence |

PRs #293, #295, #296, #298, and #299 landed the default-off coordinator,
reviewed canary plan, P1 harness, P2 capability-gap packet, and initial
positive-capability seam. Cursor then completed the live-safety/runtime-
readiness corrective. Kiro PASSed final reviewed head
`5dac4c01564de5842c91cc781f862894424b8510`; all six CI checks passed; Ryan
squash-merged PR #301 as
`8983a6fc909344239e6e3051d85c50c5508c1a16`; and Kiro's post-merge audit
PASSed packet preparation. The named source was freshly remeasured read-only
at 68 accepted messages and is eligible. A complete v2 grant remains blocked
because Ryan authorized no live reads beyond source and metadata. No grant
digest, Gate 0, P2 run, or activation exists.

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
| P2 transfer seam corrective | **DONE on `main`** via PR #299 (`8beda7d`); Kiro PASS at final head `fe0086c`, six CI checks green | — |
| P2 live-safe exact-resource v2 runtime | **DONE on `main`** via PR #301 (`8983a6fc`); Kiro exact-tip and post-merge audits PASSed, all six CI checks passed | — |
| P2 v2 source freeze | **ELIGIBLE**: stable closed source, 68 accepted messages, complete boundary 225091 | Kiro packet review |
| P2 exact-resource v2 grant packet | **BLOCKED / NO DIGEST ISSUED**: source and metadata are frozen; all other live bindings were outside Ryan's read authority | Kiro reviews the blocked packet; Ryan decides whether to authorize a separate exact read-only binding pass |
| Retired v1 candidate | **MUST NOT REUSE** digest `c002385ee2e72e319ddcce2ab5d024c29abbe0031b86cbb26468cb604ee8c621` | Permanently retired for live P2 |
| P2 one-source live canary | **UNAUTHORIZED**; no executable grant digest | Fresh packet + Kiro review + Ryan exact-digest authorization + twelve-part Gate 0 |
| Watcher/feature activation | **UNAUTHORIZED** | Separate evidence and Ryan decision |

## 5. Your Role

**If Ryan sent you for Kiro packet review:** review
`docs/inter-model/CODEX-2026-09-12-jsonl-production-canary-p2-v2-grant-packet.md`.
Confirm the source freeze, blocked-field inventory, and no-digest disposition.
This is review only and authorizes no additional live read or operation.

**If Ryan sent you to complete the replacement grant:** stop unless Ryan names
the exact additional read-only resources and operations. Do not infer missing
paths, identities, model manifests, persistent configuration, backup evidence,
or expected pre-state from the retired v1 packet.

**If Ryan sent you to implement code:** the reviewed runtime is already on
`main`; stop unless Ryan identifies a new defect and authorizes a new lane.

**If Ryan sent you to execute live P2 or activate:** stop unless Ryan supplied
a separately reviewed exact-resource v2 grant and digest for the merged
runtime. Implementation merge does not authorize live operations.

## 6. What Remains Before Live (sequential)

1. Kiro reviews the fresh source freeze and the fail-closed blocked-field
   inventory. No live operation is part of that review.
2. Ryan decides whether to authorize a separately bounded read-only pass over
   the exact remaining v2 bindings.
3. If authorized and every binding validates, Codex prepares a complete fresh
   grant JSON and digest; Kiro reviews that exact packet.
4. Ryan may then authorize that exact digest and non-mutating Gate 0.
5. Only after Gate 0 passes and Ryan separately authorizes the run, Cursor runs
   one live stage at a time against the named resources and stops at evidence.
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
| P2 runtime-readiness packet (Kiro PASS) | `docs/inter-model/CODEX-2026-09-12-jsonl-production-canary-p2-runtime-readiness-corrective.md` on `plan/2026-09-12-codex-p2-gate0-enforcement-corrective` at `a2560b4` |
| Fresh P2 v2 source freeze / blocked grant packet | `docs/inter-model/CODEX-2026-09-12-jsonl-production-canary-p2-v2-grant-packet.md` |
| Canary harness | `incremental_jsonl_canary.py`, `incremental_jsonl_canary_p2.py`, `incremental_jsonl_canary_network.py`, `incremental_jsonl_canary_live_worker.py`, `scripts/run-jsonl-production-canary.py` |
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
| 2026-09-11 | Cursor | P2 corrective implementation complete; Kiro evidence gaps corrected; awaiting exact-tip recheck |
| 2026-09-11 | Cursor | Applied Kiro lint/evidence corrections; scoped pylint and regression gate green; awaiting narrow delta recheck |
| 2026-09-12 | Cursor | Implemented Kiro-PASSed P2 runtime-readiness C0–C7 on `feat/2026-09-12-codex-jsonl-p2-runtime-readiness`; next lane is exact-tip Kiro review. No PR, live Gate 0/P2, or replacement grant |
| 2026-09-12 | Cursor | Live-safety corrective after local Claude FAIL at preserved `5bdc132`; next lane is local Claude re-review. No Kiro, PR, live Gate 0/P2, or replacement grant |
| 2026-09-12 | Cursor | R1–R4 sequence-completeness corrective after Claude FAIL at preserved `a47f32b`; next lane is local Claude re-review. No Kiro, PR, live Gate 0/P2, or replacement grant |
| 2026-09-12 | Cursor | C1–C4 after Kiro CONDITIONAL PASS at preserved `4acb4c5`; next lane is exact-tip Kiro recheck. No Claude, PR, live Gate 0/P2, or replacement grant |
| 2026-09-12 | Cursor | CI overlay-digest and writer-inventory corrective after repo-wide pytest failure on preserved `6cb0107`; next lane is Kiro exact-tip recheck of the new tip. Existing PR #301. No Claude, live Gate 0/P2, or replacement grant |
| 2026-09-12 | Codex | Recorded PR #301 merged as `8983a6fc` after green CI and Kiro PASS; freshly froze the eligible 68-message source but withheld a v2 grant/digest because remaining live bindings were outside Ryan's read authority |

## TL;DR

- Arc Codex's disabled-by-default, live-safe exact-resource v2 runtime is on
  `main` via PR #301 (`8983a6fc`) after final-tip and post-merge Kiro PASS plus
  six green CI checks.
- The named closed source freshly PASSed read-only eligibility at 68 accepted
  messages and complete boundary 225091.
- The v2 grant packet is fail-closed: only source and metadata were authorized
  for live inspection, so required resource/config/model/restic/pre-state
  bindings remain blocked and no complete grant JSON or digest was issued.
- Next lane is Kiro review of the blocked packet, then Ryan decides whether to
  authorize an exact additional read-only binding pass. Gate 0, P2, indexing,
  configuration change, watcher action, PR creation, and activation remain
  unauthorized.
