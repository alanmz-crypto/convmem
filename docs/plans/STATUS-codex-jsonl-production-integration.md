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
       unselected/unsupported ───> legacy whole-file ingest
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
- this packet selects only `jsonl_kiro_session`; separately configured
  `jsonl_codex_rollout` admission is already deployed;
- a selected complete prefix may be followed by a pure append, but cannot be
  replaced, truncated, or mutated before commit;
- expensive outputs are fsynced before any Chroma write;
- both real Chroma collections converge or restore from exact before-images;
- `processed.json` cannot advance before checkpoint authority; and
- all implementation verification is temporary, local, network-denied, and
  provider-free.

## 3. What Exists Right Now

The incremental coordinator, guarded Kiro exact-source route, semantic-v2 Kiro
identity, durable cohort budget, Codex admission, and source-scoped recovery
machinery are on `main`. Deployed runtime was independently read at
`686d50e8e671b773cacc44c14e70aa3cbd822d2e` on 2026-10-20 UTC.

The watcher is active/enabled under the existing Codex canary arrangement.
Live incremental config is enabled for Codex, with `live_sources=[]` and no
`kiro_session` policy: Kiro still takes the legacy route. Shared full rebuild
is true; the shadow observer is already set to `shadow`. Both paid transform
models remain `deepseek-v4-flash`. These are observations, not new grants.

The [Kiro Stage 1 packet](../inter-model/ASTRA-2026-10-20-issue-286-kiro-stage1-packet.md)
and [read-only cohort evidence](../inter-model/ASTRA-2026-10-20-issue-286-kiro-stage1-evidence.json)
are on `docs/2026-10-20-issue-286-kiro-stage1-packet` for Kiro review. Five ranked
legacy sessions need 28 nominal bootstrap calls. Proposed lifetime cohort cap:
120 actual paid HTTP attempts. The original Stage 1 is one existing source
(K1, three chunks) plus one dedicated new session; the latter still needs an
exact-path addendum. The other four priority sources are later expansion.

The packet found that the Kiro cohort accounting context replaces the bootstrap
per-source accounting context. The shared cohort cap remains, but the bootstrap
source cap/receipt cannot be claimed to count the paid transforms. No fix or
live probe was performed. The existing canary meter also uses total completed
chunks, including reuse, rather than actual Kiro attempts.

The Oct 13 Codex transaction `46313d437ae4446282a752270770c614` remains v1/APPLYING
with `recovery_unproven`; both its bound rollback file and transaction snapshot
are missing. An excluded historical Kiro source also retains a v1 transform-failed
transaction. None of the five selected Kiro candidates has a checkpoint or
pending transaction. No global “no pending transaction” claim is established.

## 4. Completion State

- Kiro incremental implementation: merged/deployed, opt-in and unenrolled.
  The CX-A sidecar test and CX-B Codex golden test requested by Kiro are present;
  this planning session did not repeat implementation certification.
- Kiro Stage 1 packet: prepared for exact-tip Kiro review, **spending NO-GO**.
- Kiro cohort source inventory: five paths and current hashes captured, not
  frozen against future appends; all five need semantic-v2 bootstrap.
- Operational cohort ledger and new-session binding: not materialized/created.
- Bootstrap accounting and Kiro guard measurement: prerequisites identified;
  implementation, deployment, and operational grants remain separate.
- Pending-transaction disposition and writer isolation: unresolved. Old bootstrap
  proposals are not current execution authority.
- Codex watcher operation: existing separately authorized canary; this packet
  neither interrupts nor expands it. Runtime/model/observer changes are not
  inferred from a documentation handoff.

## 5. Your Role

**Next lane: Kiro.** Review the exact committed Stage 1 packet and distinguish
packet accuracy from live spending readiness. Assess the accounting finding,
cohort choice, original two-source scope, 120-attempt envelope, new-source
addendum, missing recovery authority, and guard contract. Do not execute it.

After review, Ryan decides the needed correction/recovery work and final scope.
Any implementation follows its own lane/grant. Refresh source/config/runtime/
provider/backup bindings after prerequisites change. A packet PASS is not a live
grant; execution still needs Ryan's exact **“go Stage 1”**. No PR is requested for
this packet. Keep work isolated from other lanes' worktrees.

## 6. What Remains Before Kiro Stage 1

1. Kiro reviews the packet at its exact committed revision.
2. Resolve the per-source/cohort accounting conflict under separate authority and
   prove both caps and receipts with hermetic tests; separately qualify the Kiro
   measurement contract. Rebind the packet to the reviewed deployed runtime.
3. Resolve the Oct 13 transaction or obtain an independently accepted, explicit
   non-interaction proof; classify the retained old Kiro transaction as well.
   Do not clear quarantine, delete state, or fabricate rollback authority.
4. Bind the real new-session control before first index, refresh the selected
   source/sidecar hashes, and review exact bootstrap/post-bootstrap config phases.
5. Obtain fresh verified complete-data local/offsite backups, exact grants and
   cohort-ledger materialization authority, and a no-other-writer window covering
   watcher, reconciler, timers, ordinary CLI/MCP writers, and final evidence.
6. Ryan grants the exact Stage 1 operation. Execute only that reviewed scope;
   measure actual attempts, coverage, lineage, retrieval, and non-source isolation.
7. After accepted pilot evidence, request separate authority for the remaining
   priority cohort and watcher Stage 2. No automatic restart or budget renewal.

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
| Corrected exact-source decision packet | `docs/inter-model/SOL-2026-10-09-issue-286-bootstrap-review-packet.md` at reviewed commit `4aecb96` |
| Authorized corrective handoff | `docs/inter-model/SOL-2026-10-09-issue-286-bootstrap-safety-corrective-execute.md` |
| Cursor T0–T6 evidence | `docs/plans/VERIFY-codex-jsonl-production-integration.md` |
| Scratch evidence | `docs/inter-model/VERIFY-jsonl-incremental-scratch-prototype.md` |
| Live-source canary evidence | `docs/inter-model/VERIFY-jsonl-incremental-live-source-canary.md` |
| P1 harness evidence | `docs/plans/VERIFY-codex-jsonl-production-canary.md` |
| P1 Execute handoff | `docs/inter-model/CODEX-2026-09-10-jsonl-production-canary-p1-execute.md` |
| P2 runtime-readiness packet (Kiro PASS) | `docs/inter-model/CODEX-2026-09-12-jsonl-production-canary-p2-runtime-readiness-corrective.md` on `plan/2026-09-12-codex-p2-gate0-enforcement-corrective` at `a2560b4` |
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
| 2026-10-20 | Codex Astra | Prepared the read-only Kiro Stage 1 packet and five-source inventory; bootstrap accounting, guard measurement, missing wedge authority, and operational gates keep spending NO-GO; Kiro packet review next. |
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

| 2026-10-05 | Codex | Opened PR #365; corrected the Pylint regression without changing the safety contract, obtained Copilot/Kiro PASS at 05197a7, and kept the watcher disabled while remaining CI waits for runners |
| 2026-10-05 | Codex | Resolved the full-suite reload-order failure, brought PR #365 current with main, and obtained Copilot/Kiro exact-tip PASS plus six green checks at b17f47c; Ryan's merge and live grants remain separate |
| 2026-10-09 | Ryan | Squash-merged guarded Kiro live-route implementation via PR #365 as f3171fc; production bootstrap, activation, watcher restart, and broader source coverage remain ungranted |
| 2026-10-09 | Sol | Resolved the exact-source packet conflict in Copilot's favor and obtained same-revision Kiro/Copilot PASS at corrected commit 4aecb96; packet remains `NO-GO` pending Ryan's implementation-correction decision |
| 2026-10-09 | Ryan / Sol | Ryan authorized Cursor's bounded hermetic bootstrap-safety corrective; live resources, providers, PR creation, merge, and watcher/config/runtime operations remain gated |
| 2026-10-09 | Cursor / Sol | Implemented the authorized bootstrap-safety corrective at 273c27a on a collision-safe post-PR-#369 branch; focused tests and Pylint pass, while exact-tip review and CI-equivalent full-suite evidence remain |
| 2026-10-09 | Sol-High | Accepted Copilot's exact-revision FAIL over Kiro's PASS: APPLYING replay can replace original rollback/isolation authority; carried work onto post-PR-#370 main for Cursor correction |
| 2026-10-09 | Cursor / Sol | Corrected replay authority, independent dimension preflight, and redirects at b108ab6; focused, inventory, secret, invariant, and Pylint gates pass; exact-tip review and CI-equivalent full suite remain |
| 2026-10-09 | Kiro / Copilot | Both lanes issued complete PASS verdicts with no blockers on exact corrected revision 318c2f9; CI-equivalent full suite and Ryan's PR decision remain |
| 2026-10-10 | Cursor | Live bootstrap exposed paid-cap mis-accounting (Ollama embeds counted against DeepSeek `max_provider_http_attempts`); runtime fix `32fae68`, 12 focused passes at evidence commit `2b7228b`, Copilot scoped PASS on runtime, Kiro PASS on evidence; next gate Ryan PR/merge decision |
| 2026-10-10 | Cursor / Sol | Failed-operation supersession implementation complete on `fix/2026-10-10-kiro-bootstrap-failed-operation-supersession` (manifest-bound carried accounting, 34 focused pytest cases, pylint clean); exact-tip Kiro/Copilot review next; no live retry/config/watcher authority |
| 2026-10-10 | Sol / Kiro / Copilot | Exact-tip review complete at `a6169a5`: both lanes PASS after contained exclusive lineage-temp creation closed the final blocker; 178 affected production-Python tests pass; Ryan PR/merge decision next |
| 2026-10-10 | Ryan / Sol | Ryan merged PR #381 as `e798bba`; source remains unchanged and fresh successor packet preparation began with live execution still `NO-GO` |
| 2026-10-10 | Kiro / Copilot | Both lanes PASS the exact successor packet at `c7c12e8`, digest `b7dc9bfc…b980`; Ryan's backup-disposition and execution-grant decisions remain |
| 2026-10-10 | Sol | Mounted the designated offsite drive and verified snapshot `653a8198…f7ac4` as the exact Restic copy of local snapshot `ac1087c8…a3954`; refreshed packet awaits same-revision Kiro/Copilot review |
| 2026-10-10 | Kiro / Copilot | Both lanes PASS packet `f9418bf`, digest `f8ca5df1…ceb3d`, with no blockers; Ryan's separate exact-grant decision is next, with Restic recheck and writer-window advisories to include |
| 2026-10-10 | Sol | Authorized successor grant safely refused before activation or calls: packet used pre-overlay fingerprint `7fda8eef…f8528`; corrected post-overlay fingerprint is `d2ecd101…473f5`; exact corrected-packet review is next |
| 2026-10-10 | Kiro / Copilot | Both lanes PASS corrected packet `b380a43`, digest `3b9d1138…b21ff`, with no blockers; Ryan's new exact-grant decision is next, with fresh backup and named writer-isolation conditions |
| 2026-10-10 | Sol | Created fresh local snapshot `19201163…340a5` and exact offsite copy `bfa9ac35…16da1`, sharing tree `eb4cd065…575a`; refreshed packet awaits narrow same-revision review |
| 2026-10-10 | Kiro / Copilot / Sol | Both lanes PASS refreshed packet `2fa81eb`, digest `5e29ae13…90bb`, with no blockers; Sol prepared non-executed replacement proposal operation `c5fec18c…79c81`; Ryan's exact-grant decision is next |
| 2026-10-10 | Ryan / Sol | Ryan authorized replacement proposal `c5fec18c…79c81`; exact local Restic resolution timed out before writer pause or transport, so execution stopped with zero new calls or corpus mutation and the proposal remains unconsumed |
| 2026-10-10 | Sol | Diagnosed the local Restic timeout as a workspace-sandbox boundary: the same exact-ID read completed with the expected tree in 0.728 seconds under scoped host access; the proposal remains unconsumed pending Ryan's retry decision |
| 2026-10-10 | Ryan / Sol | Ryan authorized the retry; local exact validation succeeded under scoped host access, but offsite snapshot `bfa9ac35…16da1` timed out after 120 seconds, so execution again stopped before transport or mutation and the proposal remains unconsumed |
| 2026-10-10 | Sol | Diagnosed the offsite timeout as Restic's normal lock path against the read-only mount; explicit `--no-lock` opened the repository and returned the exact expected snapshot/tree in about 0.55 seconds without mutation |
| 2026-10-10 | Sol | Corrected the temporary validator to use `--no-lock` only offsite; the exact local/offsite IDs, shared tree, copy lineage, paths, timestamp, and tags all PASSed, with the proposal still unconsumed |
| 2026-10-10 | Ryan / Sol | Ryan authorized another exact retry; after backup PASS and writer-window establishment, supersession admission refused the stale proposal on predecessor mutation-inventory mismatch before grant materialization, dimension probing, transport, or mutation |
| 2026-10-10 | Sol | Proved the sole drift was a 310-byte append to live `synthesis_failures.jsonl`: two mocked HTTP-failure rows from `tests/test_index_loud_failures.py`; all other mutation surfaces, including Kiro Chroma rows, remained exact |
| 2026-10-10 | Cursor / Copilot / Sol | Cursor isolated the mocked failure logger to temporary test storage at `eaae6e9`; Copilot's targeted safety/isolation audit PASSed that exact code commit with no blockers; tests and linters remain unrun pending Ryan's decision |
| 2026-10-10 | Sol | Focused pytest passed both provider-refusal cases in 0.50 seconds while the live failure ledger's SHA-256, size, and nanosecond mtime remained identical; all paused timers were restored active and Ryan's PR decision is next |
| 2026-10-10 | Claude | Recorded PR #381 merge (`e798bba`); drafted Codex rollout admission design for Kiro review on `docs/2026-10-10-issue-286-codex-rollout-admission-design`; no live authority |
| 2026-10-10 | Kiro | Design PASS at `9e91973` with six binding conditions (design §13); next gate Ryan implementation grant |
| 2026-10-10 | Ryan / Claude | Ryan granted hermetic Cursor implementation; Execute handoff written; resume state `NOT_STARTED` |
| 2026-10-11 | Kiro / Claude | Kiro amended design §13 conditions 3–4: refusal quarantine is terminal by path (digest is evidence only); implementation on `feat/2026-10-10-issue-286-codex-rollout-admission` needs one more corrective |
| 2026-10-11 | Kiro / Copilot / Claude | Gate 3 FAIL at `905ad40` (Kiro: Pylint gate; Copilot: six safety findings); Kiro accepted the D8 lineage fields and generic quarantine; corrective-4 handoff written, `NOT_STARTED` |
| 2026-10-11 | Kiro / Copilot / Claude | At `a5f1756`, Kiro PASS and Copilot FAIL (D8 refusal quarantine, checkpointless recovery, `~` root); Claude confirmed all three |
| 2026-10-11 | Cursor | Corrective 5 (C5b, C1b, C6b, D1) applied; Copilot and Kiro recheck of the new tip next |
| 2026-10-11 | Copilot / Kiro / Claude | Copilot PASS and Kiro PASS at `78b9295`; PR #388 opened; next gate Ryan Stage 1 grant |
| 2026-10-17 | Cursor | Implemented the Stage 2 prerequisite failure-cache and repository-knowledge inventory refresh on `fix/2026-10-17-repository-manifest-failure-cache`. Live config and watcher remain untouched. |

## TL;DR

- **[Arc Codex]** Kiro incremental is deployed but unenrolled; existing Codex
  watcher activity continues under its own authority.
- Five priority Kiro sessions require 28 nominal bootstrap calls; the proposed
  cohort lifetime cap is 120 actual attempts. Original Stage 1 is K1 plus a new
  exact-bound session, not all five at once.
- Kiro packet review is next. Bootstrap accounting, guard measurement, wedge
  disposition, live ledger, backup/grant binding, and writer isolation keep
  execution NO-GO until Ryan's later exact “go Stage 1”.

<!-- src: ../inter-model/ASTRA-2026-10-20-issue-286-kiro-stage1-packet.md — current Stage 1 evidence and gates -->
<!-- ref: ../inter-model/LATEST.md — next-lane review routing -->
