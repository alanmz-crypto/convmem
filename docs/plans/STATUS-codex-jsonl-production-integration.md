# Arc Brief — Kiro JSONL Incremental Production Integration

> **Arc: Codex. Every model working on this arc must read this file first.**
> State the product goal, your role, current system state, and next action before
> doing substantive work.

---

## 1. What This Is For (product goal)

Arc Codex reduces repeated paid work when Kiro session JSONL and admitted
Codex rollouts append: reuse stable historical transforms and recover safely
from interrupted writes. Existing sources indexed before admission require
separate bootstrap authority; ordinary indexing cannot silently adopt them.

**Current slice:** make the one-shot bootstrap support the three existing
Codex rollouts in Ryan's A1 packet while preserving provider caps and recovery
beside live writers. The current entrypoint cannot do this. Codex has drafted
the execution plan, Kiro passed it at `9423900`, and Ryan authorized Cursor
T1–T5 implementation and hermetic verification. **T1 scoped mechanical COMPLETE** (bwrap V0–V2); T2–T5 NOT STARTED;
live authority remains separate.

**Done for this slice means:** a reviewed compatible implementation, proven
writer coordination and recovery, fresh source/backup/budget/health evidence,
and a separately authorized exact-source execution with durable receipts.
Planning, code merge, or “go A1” alone is insufficient.

## 2. System Design (how the pieces connect)

```text
Kiro JSONL / admitted Codex rollout (read-only source authority)
                   |
                   v
          normal adapter detection
                   |
       unselected source ────────> legacy whole-file ingest
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
- feature and source admission gates remain explicit; a selected-source refusal
  cannot become a silent legacy rebuild;
- guarded Kiro JSONL and admitted Codex rollouts have production routes; Codex
  history is not eligible for the proposed live bootstrap;
- a selected complete prefix may be followed by a pure append, but cannot be
  replaced, truncated, or mutated before commit;
- expensive outputs are fsynced before any Chroma write;
- both real Chroma collections converge or restore from exact before-images;
- `processed.json` cannot advance before checkpoint authority; and
- all implementation verification is temporary, local, network-denied, and
  provider-free.

## 3. What Exists Right Now (current snapshot)

- **Repository baseline:** `origin/main` fetched 2026-10-18 at
  `483373f1cef2142847fcd9c276196593a72a0ecf` (PR #402). Codex admission,
  descriptor/recovery support, and full-rebuild corrections are on main.
  Main's revision is not evidence of deployment.
- **Last observed runtime:** `633f1d1c596f890319b088f959bdce00dec45792`.
  The A1 packet observed enabled incremental routing, an active/enabled watcher,
  and `allow_full_rebuild=true`. Claude's coverage handoff describes a guarded
  watcher canary with a 3,000-paid-call ceiling and a concurrent backfill queue.
  These are dated observations; fresh execution must revalidate them.
- **Existing bootstrap:** `scripts/bootstrap-incremental-jsonl.py` remains
  Kiro-only, requires the normal route disabled and watcher stopped, and uses
  default Kiro state/transform identity. It is incompatible with A1.
- **Paid/recovery protections:** `bootstrap_safety.py` retains durable
  permit-before-HTTP accounting and one recovery; `bootstrap_supersession.py`
  retains predecessor authority. The new direction preserves existing Kiro
  behavior and does not grant Codex supersession.
- **A1 evidence:** the private packet at
  `/tmp/convmem-286-free-window-20261018/A1-dry-run-packet.md` identifies three
  rollout sources, with 2/1/1 chunks and 4/2/2 nominal paid generations.
  Existing retry states said `bootstrap_required`; no checkpoint/transaction/
  rollback files were observed. These counts and hashes are not a grant.
- **Corrective direction:**
  [existing Codex rollout bootstrap](ARCHITECTURE-issue-286-codex-bootstrap-corrective.md)
  received Kiro PASS at `e0e91bd32f96bce1f8c109a84005ed547d8655ff` in the
  review Ryan supplied. Ryan then explicitly approved direction and requested
  execution planning.
- **Execution plan:** [five serial corrective tasks](EXECUTION-issue-286-codex-bootstrap-corrective.md)
  received Kiro PASS with no blockers at
  `942390001bca407c1c28e9972c443ee7612e1c1b`. Ryan explicitly authorized
  Cursor T1–T5 implementation and hermetic verification, including Kiro's
  non-blocking precision notes.
- **Execute handoff:** [Cursor's bounded grant](../inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md)
  records the scope, notes, branch procedure, and operational prohibitions.
  Cursor branch `fix/2026-10-18-issue-286-codex-bootstrap`: T1 code + contract tests + bwrap gate landed; [VERIFY](VERIFY-issue-286-codex-bootstrap-corrective.md) documents V0–V2 PASS at tested-code SHA (see file). Prior hook-only gate rows withdrawn. No production or PR authority.

## 4. Completion State

- Ordinary admitted Codex routing exists; existing-source bootstrap support is
  the missing capability for A1. Neither full rebuild nor direct coordinator
  invocation is an authorized substitute.
- A1 is **PARKED / NO-GO** pending the corrective route. A later “go A1” cannot
  overcome the current entrypoint's technical restrictions.
- A2 indexed one stale Crush database and stopped after its post-file doctor
  returned rc 1: `[FAIL] ledger_documents: database is locked`. A final
  diagnostic also returned rc 1. Kiro subsequently reported doctor rc 0 during
  direction review; that observation does not diagnose the earlier failure or
  authorize resumption. Remaining Crush/Kiro work and manual indexing remain
  stopped.
- A3's offline baseline is complete: 38 committed one-chunk samples, median
  294.7305 s, nearest-rank p95 368.188 s, maximum 607.420 s. These are end-to-end
  event times including provider/queue work, not isolated C1 or commit timings.
- Earlier Kiro bootstrap proposals and supersession reviews remain historical
  evidence, not transferable authority for these Codex sources.

## 5. Your Role

**Cursor next:** read the [authorized Execute handoff](../inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md),
then implement T1–T5 serially in an isolated worktree and supply hermetic
verification. The reviewed plan revision is `942390001bca407c1c28e9972c443ee7612e1c1b`.
Incorporate Kiro's precision notes: no spin on a busy preparation lease, prove
exit-status disjointness, and return cross-arc recovery/cutover gaps to Ryan.

**Kiro:** exact-tip implementation review after Cursor's evidence handoff.
**Codex:** upstream planning/authority handoff; no implementation or self-review
substitution. Material scope or baseline drift returns to Ryan/Codex.

**Ryan/Claude operational ownership:** resolve A2 health readiness, establish
compatible writer participation, supply enforceable outer paid-budget and
backup/source recovery authority, and approve later exact live actions. None
of those operations is granted by the Cursor implementation authorization.

## 6. Remaining gates

1. Cursor begins the authorized T1–T5 work and fills the
   [VERIFY companion](VERIFY-issue-286-codex-bootstrap-corrective.md) at the
   exact implementation SHA. Applicable skipped proofs block mechanical PASS.
2. Obtain exact-tip independent implementation review. PR creation, PR-native
   review triggers, merge and runtime/writer rollout remain separate gates.
3. Resolve health readiness and outer-budget enforcement; revalidate exact
   source/runtime/config/provider identities, verified local/offsite backups,
   source recovery disposition, and actual writer compatibility.
4. Refresh the A1 packet. Only a compatible reviewed runtime plus Ryan's exact
   execution authority permits serial bootstrap. Preserve the 4 GB RSS and
   new-doctor-FAIL stops and initial-plus-one recovery. A2 remains stopped.

## 7. Hard Stops

| Stop | Owner | What it blocks |
|---|---|---|
| Architecture/plan review | Kiro | Cursor implementation before independent design review |
| Execute grant | Ryan | Any production-code implementation |
| Source/config admission | Live config + Ryan | Unselected or ungranted incremental/bootstrap routing |
| Bootstrap required | Separate Ryan grant | Adoption/rebuild of existing indexed sources and associated model cost |
| Implementation evidence review | Kiro | PR disposition and any production canary |
| Production canary | Ryan | Live source/Chroma/config/provider operation |
| Activation | Ryan | Feature enablement and watcher participation |

No model may infer one gate from another. In particular, plan PASS, code merge,
or canary PASS does not enable production indexing.

## 8. Relationship to ConvMem

Arc Codex changes the ingestion efficiency and recovery mechanism for Kiro
JSONL and admitted Codex rollouts. It does not change ConvMem's source/projection
authority direction, retrieval scoring, semantic calibration, or other active arcs.

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
| Authorized Cursor T1–T5 handoff | `docs/inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md` |
| A1 corrective execution plan / verification | `docs/plans/EXECUTION-issue-286-codex-bootstrap-corrective.md`, `docs/plans/VERIFY-issue-286-codex-bootstrap-corrective.md` |
| A1 Codex bootstrap corrective direction | `docs/plans/ARCHITECTURE-issue-286-codex-bootstrap-corrective.md` |
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

- 2026-10-18 | Cursor | T1 scoped mechanical COMPLETE (bwrap isolation + contract proofs); T2 not started.

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
| 2026-10-18 | Codex | A1 corrective direction drafted for Kiro review; A1 remains parked and A2 is stopped on unresolved doctor failure |
| 2026-10-18 | Codex / Ryan | Kiro direction PASS at e0e91bd supplied; Ryan approved direction; execution plan and VERIFY stub drafted for Kiro review, implementation ungranted |
| 2026-10-18 | Ryan / Codex | Kiro plan PASS at 9423900 supplied; Ryan authorized Cursor T1–T5 and hermetic verification with precision notes; Execute handoff ready, NOT_STARTED |

## TL;DR

- [Arc Codex] A1 stays parked: the current bootstrap is Kiro-only and requires
  operational conditions incompatible with the live watcher/config.
- Kiro passed the execution plan at `9423900`; Ryan authorized Cursor T1–T5
  implementation and hermetic verification. The Execute handoff is ready;
  implementation remains NOT_STARTED and live execution remains gated.
- A2 remains stopped on an unresolved doctor failure. A3's 38-sample baseline
  is complete. No source, runtime, config, watcher, or quarantine change is
  authorized by the implementation grant.

<!-- ref: ./ARCHITECTURE-issue-286-codex-bootstrap-corrective.md, ./EXECUTION-issue-286-codex-bootstrap-corrective.md, ./VERIFY-issue-286-codex-bootstrap-corrective.md, ../inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md — current A1 plan and gates -->
<!-- src: /tmp/convmem-286-free-window-20261018/A1-dry-run-packet.md, /tmp/convmem-286-free-window-20261018/A2-report.json, /tmp/convmem-286-free-window-20261018/a3-baseline.json — dated operational evidence -->
