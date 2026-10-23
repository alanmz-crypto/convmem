# Arc Brief — Kiro and Codex JSONL Incremental Production Integration

> **Arc: Codex. Every model working on this arc must read this file first.**
> State the product goal, your role, current system state, and next action before
> doing substantive work.

---

## 1. What This Is For (product goal)

Arc Codex makes repeated Kiro and Codex transcript indexing incremental and
crash-replayable: reuse stable historical chunks, transform only the overlap
frontier and new messages, and never pay twice for a completed transform after
a crash. The guarded production routes now cover selected Kiro session JSONL
and admitted Codex rollout JSONL, with unselected sources staying on the legacy
path. Current live selection and runtime evidence are in §3. The current follow-up
is #393, scoping paid-transform reuse for Crush SQLite; doctor acknowledgment
is parked at Ryan's direction (2026-10-23).

**Done means:** hermetic real-Chroma fault/replay review and authorized
production measurements establish frontier reuse, durable paid-work reuse,
and visibility/recovery behavior. Each adapter's source and activation grants
remain distinct. Codex admission and the publication fence are live; Stage 1
and Stage 2 acceptance remains Ryan to confirm, and the deployment's
doctor-exit-0 criterion remains unmet (§4). No Kiro source is currently selected.

## 2. System Design (how the pieces connect)

```text
Kiro session JSONL / Codex rollout JSONL (read-only source authority)
                   |
                   v
          normal adapter detection
                   |
   feature off / unselected / other adapter ──> legacy whole-file ingest
                   |
     selected Kiro exact path + policy / admitted Codex rollout
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
- production eligibility is exact-source `jsonl_kiro_session` or admitted
  `jsonl_codex_rollout`, subject to their separate policies; Codex history is
  supported only inside hermetic isolation, while Cursor JSONL and Crush SQLite
  retain the legacy route;
- a selected complete prefix may be followed by a pure append, but cannot be
  replaced, truncated, or mutated before commit;
- expensive outputs are fsynced before any Chroma write;
- both real Chroma collections converge or restore from exact before-images;
- `processed.json` cannot advance before checkpoint authority; and
- implementation fault/replay tests are temporary, local, network-denied, and
  provider-free; live operations and measurements require their own grants.

## 3. What Exists Right Now (file map)

Snapshot verified on 2026-10-22 against `origin/main` at `1a68675`, the clean
runtime worktree, the effective watcher service, and the live incremental
configuration. Merged implementation and observed live operation are distinct
from acceptance of the Stage 1 and Stage 2 measurements.
Ryan later squash-merged the refreshed docs through PR #413 as `75d8e2a` and
the priority-#1 handoff through PR #414 as `5c0a01b`. The last verified runtime was the
granted `1a68675`; neither docs merge needs a deployment. Ryan also merged
the acknowledgment design through PR #415 as `3d24c75`; it is unimplemented
and now parked.

The operational rows below are the last verified 2026-10-22 snapshot, not a
new runtime attestation. On 2026-10-23, a read-only recheck found current boot
`4a99c57d3478481192186b681f64687c` and no original `timeshift[835726]` crash.
Doctor still exits 1 on a separate CPU-7 zsh event. Ryan waived that known
startup failure for session progress and directed Codex to park acknowledgment
and scope #393. This is not a hardware diagnosis or deployment acceptance.
Ryan separately reports creating a Clonezilla image this morning and testing
it successfully by installing it on another computer; this is user-reported
restore evidence, not a new Timeshift/Restic test.

| Surface | Current state |
|---|---|
| Coordinator and isolated Codex integration | Kiro coordinator/canary work is on `main` through PR #301 (`8983a6f`). S0–S3 Codex integration merged through PR #307 (`d657767`); successor `19d34a5` is no longer pending integration. Hermetic tests retain their fake-provider boundary. Cursor JSONL and Crush SQLite remain legacy routes. |
| Guarded Kiro production route | PR #365 (`f3171fc`) added the exact-source boundary and existing-source bootstrap. Paid accounting and failed-operation supersession landed through PR #377 (`d1c28f9`) and PR #381 (`e798bba`); exact-path recovery parity landed through PR #396 (`9ef4ecd`). These merges do not grant another bootstrap. |
| Test isolation | The mocked-provider failure-log correction merged through PR #384 (`6a23aa9`); the `eaae6e9` fix no longer awaits a PR decision. |
| Codex rollout admission | PR #388 supplies the guarded admission route. Live config has `enabled = true`, `live_sources = []`, `allow_full_rebuild = true`, and root `/home/lauer/.codex/sessions`, with `admitted_after = "2026-10-12T04:04:00Z"`, `max_transform_chunks_per_run = 10`, and `max_source_bytes = 268435456`. Journal entries show committed `incremental_codex_admitted_run` events. This proves operation, not Stage 1/Stage 2 acceptance. |
| Watcher retry and wedge corrections | The inter-model rejection-loop fix merged through PR #390 (`8a7cdab`), resolving the #308 prerequisite. Stage 2 wedge fixes merged through PR #395 (`3e705e4`); manifest failure caching and inventory refresh merged through PR #403 (`395e523`). |
| Transform compatibility | PR #399 (`9be0a4f`) binds reuse to semantic transform inputs rather than unrelated implementation changes. `distill.py`, `llm.py`, `incremental_transform_contract.py`, and `incremental_checkpoint_migration.py` are byte-identical between runtime `686d50e` and target `1a68675`; this promotion does not invalidate checkpoints or require a paid rebuild. |
| Scoped-proof observer | PR #405 (`77a5e89`) added an off-by-default shadow observer. Live config sets `mutation_proof_observer = "shadow"`; this does not authorize replacing the existing integrity proof. |
| Opt-in Kiro watch route | PR #406 (`adcf5b3`) added opt-in Kiro incremental indexing with a crash-safe paid-call budget. Live `live_sources = []` selects no exact Kiro source. |
| Same-source publication fence | PR #411 (`6cacc1b`, reviewed tip `1916a15`) keeps the source lock through processed-row publication and journal cleanup. PR #412 (`1a68675`) records the merge. Ryan's exact-SHA grant was executed on 2026-10-22: the watcher now runs the fence. |
| Effective watcher runtime | `.worktrees/runtime-main` is clean on branch `main` at granted SHA `1a686753d8fd1b710883050e8a4f9c45b7ae1e26`, fast-forwarded from `686d50e` after its indexing child completed. The watcher restarted once at `2026-10-22T13:52:35-05:00`, active under PID `904311`, invocation `db09e9881aa7454499a1ae117be5dac5`. Effective `MemoryMax` is `8589934592` bytes (8 GiB); live config SHA-256 remained `9719875a5906d0a708be2fc54640df74b9515c1be8e39e18401c8b25015db89c`. |
| Crush cost follow-up, issue #393 | [Scope proposal](SCOPE-crush-indexing-cost-reuse.md) on `plan/2026-10-23-issue-393-crush-indexing-scope`. Source inspection confirms the legacy whole-file route and global cross-session chunks. No Crush implementation exists; the next design must define logical SQLite capture, session-local chunks, durable provider-result reuse and adoption. |

## 4. Completion State

| Milestone | State | Next gate |
|---|---|---|
| Coordinator, S0–S3, and guarded production boundary | Merged through #301, #307, and #365 | Preserve reviewed behavior |
| Kiro bootstrap prerequisites | Accounting #377, supersession #381, test isolation #384, and recovery parity #396 are merged | Fresh exact-source evidence, proposal, review, and Ryan grant for any later retry; do not reuse stale proposal `c5fec18c…79c81` |
| Codex admission and watcher prerequisites | Admission #388, rejection-loop #390, wedge fixes #395, compatibility #399, and manifest cache #403 are merged; live Codex admission is observed | Preserve current settings; do not infer canary acceptance from live operation |
| Optional integrity observation and Kiro route | #405 and #406 are merged; observer is live in shadow mode, with no exact Kiro source selected | Separate authority for any config or source change |
| Same-source publication fence | #411 is merged and deployed at `1a68675` under Ryan's one-time exact-SHA/restart grant | Grant consumed; no further restart or promotion is authorized by it |
| Runtime-promotion verification | The 2026-10-22 promotion and its activity checks completed; full acceptance was not established. The original Timeshift event is absent after reboot; the latest doctor still exits 1 on a separate CPU-7 event. | Ryan waived the known CPU-7 startup failure for session progress; no deployment-acceptance claim follows |
| Interrupted Timeshift backup | The 2026-10-22 replacement snapshot completed normally. On 2026-10-23 Ryan separately reported a Clonezilla image successfully restored onto another computer. | User-reported Clonezilla recovery test passed; it is not evidence of a Timeshift/Restic restore test |
| Stale Timeshift mount cleanup | Ryan completed the root active-user check and normal unmount; Codex verified `/run/timeshift/835726/backup` absent at `14:48:28 CDT`, with the reconnected volume still read-write and watcher unchanged | Scoped cleanup complete; grant consumed. Retention's previous failed status remains recorded; retry/reset would need separate authority |
| Doctor acknowledgment | **PARKED by Ryan, 2026-10-23.** The original Timeshift event is absent from the current boot. Design #415 merged as `3d24c75`; cursor revision `2a138be` closes identity finding 3, but Codex/Claude G0 remains FAIL for malformed-read FAIL preservation and undefined re-ack after revocation. Nothing is implemented. | No active execution step; a future resume requires corrected design and review. The original one-event G5 is moot |
| Crush indexing cost, issue #393 | **SCOPING authorized.** The scope compares global-chunk caching, direct JSONL reuse and a session-aware Crush path; it proposes the latter. | Claude scope review, then a binding architecture and execution plan. No code, warm-up, paid canary or live configuration grant |
| Stage 1 and Stage 2 outcomes | **Ryan to confirm**; checked repository and corpus search do not establish the measured results or acceptance | Locate authoritative result/grant evidence before declaring either stage passed |
| Pre-activation rollout residual-burn decision | **Ryan to confirm**; admission cutoff alone does not prove the chosen disposition | Confirm the recorded decision; no exclusion, retirement, or rebuild is authorized here |

## 5. Your Role

**The active task is issue #393 scoping, not doctor acknowledgment.** Ryan
explicitly directed Codex to park acknowledgment and scope the Crush paid-work
problem on 2026-10-23. Codex owns planning and future implementation; Claude
handles independent reviews for this follow-up at Ryan's direction. Start
with [the scope proposal](SCOPE-crush-indexing-cost-reuse.md).

The scope is a design input, not an implementation-ready specification.
It identifies why a cache of today's global chunks is only partial: appending
to an earlier-sorting session shifts later windows. The proposed complete
approach needs session-local chunks, a consistent logical SQLite capture,
and durable provider-result reuse. Snapshot identity, provider binding,
projection/read compatibility, corruption/spending and existing-data adoption
must be resolved in a binding architecture and execution plan before Execute.
Claude independently reviews the scope and then the exact design revision.
Ryan retains the implementation and live-operation decisions.

The source inspection reused Claude's recorded #393 fake-provider probe rather
than repeating a paid run. No host Crush database, production Chroma, source
configuration or watcher operation belongs in this scoping task.

**Acknowledgment is parked.** Its merged design is preserved, as is the
unmerged cursor revision `2a138be9b0a12ae8849665435ab7ba1674154853` on
`docs/2026-10-22-doctor-ack-g0-revision`. The read-only G0 review closed the
cursor defect but retained FAIL: malformed JSON must not erase a detected
fault, and re-ack after revocation is unspecified. Do not repair or implement
that packet unless Ryan resumes it. The original boot-specific live operation
is moot because its Timeshift entry is absent after reboot.

Ryan's known CPU-7 startup exception allows session progress; it does not
change `cpu_tripwire`, establish a hardware cause, or supply the separate
production acceptance decision. His reported successful Clonezilla restore is
preserved in §3–§4 without substituting it for an unperformed Timeshift test.

The previously granted `1a68675` promotion and one watcher restart are
consumed, as is the stale Timeshift mount-cleanup grant. Do not repeat them,
deploy protocols, edit live configuration, bootstrap, clear quarantines or
initiate paid canaries. Stage 1, Stage 2 and residual-burn acceptance remain
**Ryan to confirm**. Their reconciliation is separate from #393 scoping.

## 6. What Remains Before Live (sequential)

1. Claude reviews the #393 scope. Codex then authors a binding architecture
   and execution plan for the chosen direction, resolving the questions in
   the scope before seeking a design verdict and Ryan's Execute grant.
2. After design PASS and a bounded grant, Codex implements hermetically;
   Claude independently reviews the exact revision. Implementation evidence,
   PR/merge, promotion and any source-specific warm-up/model cost remain
   separate decisions. Do not inherit Codex/Kiro JSONL live grants for Crush.
3. Independently reconcile Stage 1/Stage 2 and residual-burn evidence when
   Ryan resumes that task. Do not repeat paid canaries to replace missing
   records or infer acceptance from a running service.
4. A future Kiro bootstrap, Timeshift maintenance or acknowledgment resume
   requires its own current proposal and authority. None is the current task.

## 7. Hard Stops

| Stop | Owner | What it blocks |
|---|---|---|
| Architecture/plan review | Claude for #393 per Ryan; existing JSONL reviews retain their assigned lane | Implementation before independent design review |
| Execute grant | Ryan | Any production-code implementation |
| Default-off flag | Live config + Ryan | Incremental routing in production |
| Bootstrap required | Separate Ryan grant | Adoption/rebuild of existing indexed sources and associated model cost |
| Implementation evidence review | Claude for #393 per Ryan; existing JSONL reviews retain their assigned lane | PR disposition and any production canary |
| Production canary | Ryan | Live source/Chroma/config/provider operation |
| Activation | Ryan | Feature enablement and watcher participation |

No model may infer one gate from another. In particular, plan PASS, code merge,
or canary PASS does not enable production indexing.

## 8. Relationship to ConvMem

Arc Codex changes ingestion efficiency and recovery for the selected JSONL
adapters; #393 is its separately scoped Crush cost follow-up. It does not change ConvMem's source/projection authority direction,
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
| Current #393 scope | `docs/plans/SCOPE-crush-indexing-cost-reuse.md` |
| Parked doctor acknowledgment design | `docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md`, `docs/plans/EXECUTION-doctor-fault-acknowledgment.md` |
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
| 2026-10-23 | Codex | Parked acknowledgment after the original event left the current boot; scoped #393 with Codex implementation/Claude review ownership and separate design/Execute gates |
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
| 2026-10-21 | Claude | Independent review of #286 forward publication fence at `e6ce3c4`: PASS-WITH-CHANGES (fence logic correct; pylint, shadow/R2b inventories and repository manifest would fail CI); mechanical fixes handed to Codex Luna max via `CODEX-LUNA-2026-10-21-issue-286-fence-ci-fixes-handoff.md`. Fence intentionally reverses the 2026-09-10 note that released the source lock before processed publication |

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
| 2026-10-21 | Ryan | Squash-merged the #286 same-source processed-publication fence via PR #411 as `6cacc1b` (reviewed tip `1916a15`); no production activation or live indexing followed |
| 2026-10-22 | Codex | Refreshed Arc Codex §3–6 from merged #307–#412 and live read-only evidence: Codex admission is active at runtime `686d50e`, fence promotion awaits an exact SHA, effective limit is 8 GiB, and unproven Stage 1/Stage 2/residual-burn outcomes remain Ryan to confirm. |
| 2026-10-22 | Codex | Executed Ryan's exact `1a68675` fast-forward and one restart: watcher active, config unchanged, 10-minute journal clean, and normal Codex commit observed; host-access doctor exited 1 on the pre-existing CPU-tripwire report, leaving that acceptance criterion unmet. |
| 2026-10-22 | Codex | Corrected stale Kiro-only design and tripwire routing descriptions; read-only host triage identifies loss of Timeshift's active USB backup volume before its crash, with physical cause and CPU damage unproven and doctor acceptance still unmet. |
| 2026-10-22 | Ryan / Codex | Ryan confirmed deliberate external-USB drive removal for testing, explaining the disconnects; Timeshift crash mechanics, interrupted-backup validity, and doctor acceptance remain unresolved. |
| 2026-10-22 | Codex | Completed backup/disposition review: failed 13:00 snapshot absent, replacement reported successful at 13:07:24 with metadata, retention still fails on a stale disconnected-device mount, and original doctor acceptance remains unmet. |
| 2026-10-22 | Ryan / Codex | Ryan granted exact stale-mount active-user check and normal unmount; mount/process checks completed, but root active-user inspection requires local sudo authentication, so no unmount was attempted. |
| 2026-10-22 | Ryan / Codex | Ryan completed the root active-user check and normal unmount; Codex verified the stale mount absent, reconnected backup volume still read-write, and watcher unchanged. Scoped cleanup complete; historical retention and doctor failures remain recorded. |
| 2026-10-22 | Codex | Opened docs PR #413 at Ryan's request and routed the brief and current handoff to review; merge remains Ryan-owned, doctor acceptance remains unmet, and no further host authority is implied. |
| 2026-10-22 | Codex | Confirmed the requested doctor clearance has no existing reset mechanism and exactly one check still fails; stopped at the gate-redesign boundary and left a new-model handoff in §5 without live changes. |
| 2026-10-22 | Codex | Recorded Ryan's PR #413 squash merge and no-reboot constraint; prepared the standalone priority-#1 acknowledgment handoff for a fresh model, preserving the product queue and leaving implementation and acceptance incomplete. |
| 2026-10-22 | Codex / PR Steward | Opened handoff delivery PR #414 under Ryan's assignment; fresh-model acknowledgment design remains unstarted, with no live changes or merge authority. |
| 2026-10-22 | Claude | After Ryan merged #414 as `5c0a01b`, drafted the priority-#1 design: per-entry, boot-bound acknowledgments shown as WARN, gates G0–G6, and tests T0–T44. Kiro design review is next; nothing is implemented or live. |

## TL;DR

- [Arc Codex] The publication fence is deployed at clean runtime `1a68675`;
  the watcher restarted once under Ryan's exact grant and is active with an
  effective 8 GiB limit. Live configuration is unchanged.
- Promotion carried #410–#412 without changing the transform contract.
  The ten-minute journal is clear, and a normal admitted Codex run committed
  afterward. Host-access doctor exited **1** on the pre-existing CPU-tripwire
  report; full handoff acceptance remains unmet despite the startup waiver.
- Stage 1/Stage 2 results and the pre-activation residual-burn decision are
  **Ryan to confirm**. Merged Kiro bootstrap prerequisites do not authorize a
  retry of stale proposal `c5fec18c…79c81`.
- Priority #1: the design for acknowledging this one doctor fault awaits Kiro
  review. It is not implemented, and doctor acceptance remains unmet.

<!-- ref: ../inter-model/LATEST.md, ./SCOPE-crush-indexing-cost-reuse.md — current Arc Codex routing and #393 scope -->
<!-- ref: ../inter-model/CODEX-2026-10-22-doctor-ack-next-model-handoff.md — priority-#1 design pickup and subsequent queue -->
<!-- ref: ./ARCHITECTURE-doctor-fault-acknowledgment.md, ./EXECUTION-doctor-fault-acknowledgment.md, ../inter-model/KIRO-2026-10-22-doctor-fault-ack-design-review-handoff.md — priority-#1 design and Kiro pickup -->
<!-- src: ../inter-model/CODEX-LUNA-2026-10-21-issue-286-fence-ci-fixes-handoff.md — reviewed fence and verification context -->
<!-- src: ../../incremental_jsonl.py, ../../incremental_jsonl_formats.py — current production routing -->
<!-- src: ../../cpu_tripwire.py, ../../doctor.py — boot-scoped failure and absence of a reset mechanism -->
<!-- src: /etc/timeshift/timeshift.json — configured backup-volume identity -->
<!-- src: /run/media/lauer/BIT-Brg-larch-7t/timeshift/snapshots/2026-10-22_13-03-52/info.json, /usr/local/bin/timeshift-enforce-retention.sh — replacement metadata and observed stale-mount selection -->
