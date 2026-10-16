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
| Incremental coordinator | On main, default off. Enabled Kiro routing without the hermetic root returns skipped. Existing indexed sources without a checkpoint return bootstrap_required/skipped. |
| Hermetic isolation | Tokenized, fake-provider test boundary; it cannot be a live switch. |
| Format registry | Kiro JSONL outside isolation; Codex history/rollout only inside isolation. Cursor JSONL and Crush SQLite are not eligible. |
| Canary runtime | P2 readiness correction merged by PR #301 (8983a6f); no live P2 or activation grant. |
| Issue #286 successor | S0-S3 branch 19d34a5 remains unmerged; Copilot and Kiro documentation-acceptance rechecks PASS at that exact tip, with whitespace independently checked by Codex. |
| Issue #286 guarded live route | Ryan squash-merged PR #365 onto `main` as f3171fc on 2026-10-09. The guarded production boundary, canonical exact-source gate, and one-shot existing-source bootstrap are present but default off; no live config, bootstrap, or runtime promotion occurred. Copilot and Kiro passed the final PR tip 7ed46c4; all six GitHub checks passed, including 2680 Python 3.12 tests. Crush SQLite and Cursor JSONL remain on the legacy route. |
| Exact-source review packet | Sol corrected the issue #286 packet at commit 4aecb96 after adjudicating the first same-revision PASS/FAIL conflict in Copilot's favor. Kiro and Copilot then both passed the packet as an accurate `NO-GO`. The first implementation received exact-revision Kiro PASS and Copilot FAIL at b68daea; Sol-High accepted Copilot's replay/rollback finding. Cursor corrected it at b108ab6, and Kiro/Copilot both passed exact revision 318c2f9 with no blockers. |
| Watcher | Stopped and disabled 2026-10-05 at Ryan's request; runtime pin a92a74e unchanged. |

## 4. Completion State

| Milestone | State | Next gate |
|---|---|---|
| Coordinator and canary | Merged on main through PR #301; disabled | Preserve reviewed behavior |
| S0-S3 Codex route | Reviewed 506afc1, successor 19d34a5 unmerged; Copilot/Kiro docs rechecks PASS | Ryan PR decision for that separate branch |
| Live-activation design | Kiro PASS at e4fa954 with RC-1 through RC-3 | Preserved in reviewed implementation |
| Production boundary and exact-source gate | Merged on `main` via PR #365 (f3171fc); default off, with no live source grant | Ryan exact-source/config/runtime grant before any production route |
| Existing-source bootstrap paid accounting | Merged on `main` via PR #377 (`d1c28f9`); DeepSeek-only paid cap with Ollama observed but cap-exempt. | Preserve reviewed behavior |
| Failed-operation supersession | Merged on `main` through PR #381 as `e798bba`; predecessor-preserving supersession, paid-attempt enforcement, lineage publication, and retained predecessor evidence are present. The latest retry stopped before grant materialization because two mocked rows from `tests/test_index_loud_failures.py` changed live `synthesis_failures.jsonl`, making proposal `c5fec18c…79c81` stale. Cursor corrected the test at `eaae6e9` on `fix/2026-10-10-pytest-synthesis-failure-isolation` by redirecting the real failure logger to temporary test storage; production code is unchanged. Copilot's targeted safety/isolation audit PASSed exact code commit `eaae6e9` with no blockers. The two focused refusal tests pass, and the live ledger remained byte-for-byte and metadata-identical across the run. | Ryan decides PR creation and merge; fresh backup/proposal authority follows only after the fix lands |
| Codex rollout admission | Merged on `main` via PR #388; default off, with no admission config. Design: `docs/plans/DESIGN-issue-286-codex-rollout-admission.md` (Kiro PASS at `9e91973`, §13 amended 2026-10-11). It admits new rollouts after an explicit, identity-checked `admitted_after` time; pre-activation rollouts stay legacy; refusals quarantine terminally by path. Copilot PASS and Kiro PASS at `78b9295`. | Ryan Stage 1 grant (`docs/inter-model/CLAUDE-2026-10-11-issue-286-codex-stage1-packet.md`) |
| Watcher activation | Unauthorized; watcher disabled | Separate Ryan promotion/config/restart grant |

## 5. Your Role

The Kiro bootstrap remains stopped before grant materialization or paid calls.
Proposal `c5fec18c…79c81` is unconsumed but stale and cannot be reused. The sole
inventory drift was two mocked 402/503 rows that
`tests/test_index_loud_failures.py` appended to live
`synthesis_failures.jsonl`; all other mutation surfaces, including the Kiro
source's two summary rows and 17 knowledge units, remained exact.

Cursor corrected the isolation leak at code commit `eaae6e9` on
`fix/2026-10-10-pytest-synthesis-failure-isolation`. Each affected `_build`
call now patches `ingest._SYNTHESIS_FAIL_LOG` to a temporary path while keeping
the real failure-logging code under exercise. Production code is unchanged.
Copilot's targeted safety/isolation audit PASSed that exact code commit with no
blockers. The two focused refusal tests pass in 0.50 seconds. The live ledger's
SHA-256 (`31e8d29e…9672`), 633839-byte size, and nanosecond mtime were identical
before and after; all four paused timers were restored active. Ryan decides PR
creation and merge. Fresh backups, proposal, packet review, and live execution
remain later separate gates. No lane may promote config/runtime or restart the
watcher without separate Ryan authority.

**Codex rollouts (separate track):** Codex rollout admission is on `main`
(PR #388), default off. Its purpose is to stop the paid re-index burn for
new Codex sessions; nothing in production is reduced until Stage 1 and
Stage 2 run. Prepare or run Stage 1 only under Ryan's grant, following the
Stage 1 packet. Active pre-activation rollouts, including a 590.7 MiB
session started Sep 21, stay on the legacy route and need the packet's
residual-burn decision before Stage 2. This track authorizes no live
bootstrap, config, runtime, or watcher action.

## 6. What Remains Before Live (sequential)

1. Ryan decides whether to create and merge the test-isolation PR.
2. After the fix lands, capture current mutation state, refresh
   backup coverage, and prepare a new exact proposal and review packet.
3. Immediately before any later authorized retry, revalidate the exact
   local/offsite pair, source/runtime/config/binding/dimension, and establish a
   no-other-writer window through final evidence capture.
4. If granted, execute only the exact source/runtime/config/budget operation and
   return measured call, coverage, lineage, and isolation evidence.
5. Obtain a later separate Ryan grant before any runtime/config/restart or
   watcher promotion; measure calls and coverage by source class.

Codex rollouts (separate track):

1. Ryan grants Stage 1 (manual, watcher stopped), per
   `docs/inter-model/CLAUDE-2026-10-11-issue-286-codex-stage1-packet.md`.
   Don't add the incremental table to the shared live config while
   `runtime-main` is still on `a92a74e`.
2. Before Stage 2, decide the residual burn (retire or exclude active
   pre-activation rollouts), fix #308 (the inter-model rejection loop) and
   reconcile the 4G watch drop-in. Then Ryan grants Stage 2 (a 24 h watcher
   canary); activation is a separate grant.
3. Before any Kiro exact-path live incremental run, land the exact-path
   recovery parity fix. Its design is on
   `docs/2026-10-11-issue-286-exact-path-recovery-parity`; Kiro ruled it a
   separate prerequisite.

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
| 2026-10-12 | Claude | Stage 2 stopped at the paid ceiling (~410/400; new sessions ~12); Ryan authorized fixes P1–P3 + Track A rule change; Cursor handoff `CURSOR-2026-10-12-issue-286-stage2-fixes-handoff.md` |
| 2026-10-13 | Claude | Wedge-fix corrective 1 (`117d698`) fixed the round-1 blockers; small corrective 2 (retry backstop, doctor WARN, tamper honesty, watcher digest cost) to Cursor |
| 2026-10-13 | Claude | Wedge-fix corrective 2 (`c8436b1`): 0 tests fail only at the tip against main; short corrective 3 (doctor crash on a real wedge, false rollback tamper message) to Cursor |
| 2026-10-13 | Claude | Wedge-fix corrective 3 (`8a8c03a`) fixed the doctor crash; one-item corrective 4 (rollback tamper message compares unit ids, not bytes) to Cursor |
| 2026-10-13 | Claude | Wedge-fix corrective 4 (`62fe3a2`) made the rollback check id-based; one-item corrective 5 (stop false tamper reports on clean rollbacks of grown sessions) to Cursor |
| 2026-10-13 | Claude | Wedge-fix corrective 5 (`c7072fc`) passed round-6 verify; branch ready for Copilot audit and Kiro design review |
| 2026-10-13 | Claude | Codex safety audit FAILed `c7072fc` (dedupe rollback loss, unbounded paid retries, incomplete C1 coverage, work under C1, Claude deferral); Kiro PASS with conditions; corrective 6 to Cursor |
| 2026-10-13 | Claude | Round 8 FAILs corrective 6 (`e1914f5`): Codex's burn holes closed, but the new lock-order check makes `index --file` pay then fail on every Codex/Kiro source, and the write guard breaks ledger approvals; corrective 7 (S0–S7) to Cursor; not deployable |
| 2026-10-13 | Claude | Round 9 FAILs corrective 7 (`905e602`): the real `index --file` route commits and the paid-retry bounds hold through it, but refine, monitor and retirement now take C1 inside an open store session (refine pays then fails; a burn if the refine unit is enabled); corrective 8 (T0–T5) to Cursor; not deployable |
| 2026-10-13 | Claude | Round 10 FAILs corrective 8 (`61307d7`): the lock order is fixed and the refine daemon is hardened, but refine and monitor keep a reader open across writes (refine pays, then the write guard refuses), refine's tests now write through the user's config, and the R2b inventory is stale; corrective 9 (T0–T4) to Cursor; not deployable |
| 2026-10-14 | Claude | Round 11 FAILs corrective 9 (`d2abcbe`) on one mechanical item: all round-10 findings fixed, leak census 86 → 1 test, but the writer inventories are one edit behind the code (6 tip-only failures); corrective 10 (inventory regeneration + one test's environment, no production code) to Cursor; not deployable |
| 2026-10-14 | Claude | Round 12 FAILs corrective 10 (`41561ef`) on one test-only item older than the branch (a D1 test leaks the live-diagnosis bootstrap's patches; CI would go red on 3 probes); X0/X1 fixed, 0 tip-only failures, leak census 0; corrective 11 (7 lines, test-only) to Cursor; Crush re-pay filed as #393; not deployable |
| 2026-10-14 | Claude | Round 13 PASSes corrective 11 (`0ee6994`): disk-backed suites show no branch failure (one pre-existing inode flake, Z1), leak census 0; ready for the Astra audit and Kiro review; not deployable until the merge and Ryan's grants |
| 2026-10-14 | Claude | Astra's round-2 audit FAILs `0ee6994` (four blockers, one a burn path in the retry bounds); Kiro PASS with conditions; round 14 reproduces all four and withdraws round 13's PASS; corrective 12 (retry reservation, sidecar C1, no embedding under C1, commit revalidation, Kiro CO-1/CO-7) to Cursor; not deployable |
| 2026-10-14 | Claude | Round 15 FAILs corrective 12 (`8d6ee76`): Astra's four blockers closed (the retry burn path included), but the new drift check refuses every existing ledger row (readonly vs write-store digest) plus four smaller gaps; corrective 13 to Cursor; not deployable |
| 2026-10-14 | Claude | Round 16 FAILs corrective 13 (`2ffaf79`): round 15's findings closed; new stale ledger cache after a commit (7 tip-only test failures) and a full-store scan under C1 per row; corrective 14 to Cursor; a second Mirror Crush index (263 units, about 38 paid calls) ran outside the watcher this evening; not deployable |
| 2026-10-14 | Claude | Round 17 FAILs corrective 14 (`700b6ba`) on one finding: round 16 closed, C1 holds short, suite clean but for Z1, leak census 0; the repair scan makes `convmem doctor` take minutes; corrective 15 to Cursor; not deployable |
| 2026-10-15 | Claude | Round 18 PASSes corrective 15 (`7d46e6e`): all retained probes pass, suite clean but for Z1, leak census 0; X5 doctor-query follow-up; Astra re-audit and Kiro re-review next; not deployed |
| 2026-10-15 | Claude | Astra round 3 FAILs `7d46e6e` (concurrent retry cap bypass, repair and monitor drift crashes); Kiro round 3 PASS with conditions; Claude round 19 reproduces Astra and withdraws round 18; corrective 16 to Cursor; not deployable |
| 2026-10-15 | Claude | Round 20 PASSes corrective 16 (`928700b`) on safety (concurrent cap holds across processes); R2b inventory stale again, one mechanical regeneration before Astra's re-audit; not deployed |
| 2026-10-15 | Claude | Round 21 PASSes `74c8ee7`: inventory current, no tip-only failure, diff coverage and static checks added, no hidden broken branch; Astra re-audit and Kiro check next; not deployed |
| 2026-10-15 | Claude | Astra round 4 FAILs `74c8ee7` (corrupt retry state overwritten, snapshot per refusal); Claude round 22 reproduces, withdraws round 21; corrective 17 to Cursor; not deployed |
| 2026-10-15 | Claude | Round 23 at `881c804`: R4-F1/F2 closed; FAIL on N13 (pre-capture unchanged shortcut bypasses the lineage guard and clears the retry hold, no paid calls); corrective 18 to Cursor; not deployed |
| 2026-10-15 | Claude | Round 24 PASS at `a89f573` (corrective 18 closes N13/N14; no tip-only failure; 0 leaks); Astra re-audit next, then PR draft; not deployed |
| 2026-10-15 | Claude | Astra round 5 FAILs `a89f573` (shortcut skips revalidation and the retry gate); Claude round 25 reproduces, withdraws round 24; corrective 19 to Cursor; not deployed |
| 2026-10-15 | Claude | Round 26 at `d5d10b5`: FAIL with Astra's round 6. R5-F1/R5-F2 closed; capture-error codes reset retry counters (R6-F1) and the R2b inventory is stale (R6-F2); corrective 20 adds a one-line accounting fix and merges main `c6f0724` |
| 2026-10-16 | Claude | Round 27 at `3e0caf9`: FAIL under main's CI launcher. R6-F1 closed; the merge with main breaks approval recovery (C1 taken inside a Chroma session) and 87 config-dependent tests (branch conftest); corrective 21 is a tested diff, run under the launcher |
| 2026-10-16 | Claude | Round 28 at `d0510f8`: PASS. Corrective 21 matches the tested diff; 0 tip-only failures under main's CI launcher; Astra round 7 next |

## TL;DR

- The Kiro JSONL coordinator and canary remain on `main`, default off; watcher stays
  stopped and disabled with no restart authority.
- Failed-operation supersession is on `main` through PR #381 (`e798bba`); the
  first successor grant safely refused with zero new calls or corpus mutation;
  Kiro and Copilot both PASS refreshed packet `2fa81eb`, digest
  `5e29ae13…90bb`, with no blockers.
- Fresh local/offsite backups share tree `eb4cd065…575a`; authorized proposal
  `c5fec18c…79c81` is unconsumed but stale because the live predecessor
  mutation inventory no longer matches its bound digest. The sole drift is two
  mocked test failures appended to the live synthesis-failure ledger. The retry
  stopped before grant materialization or paid calls. The isolation fix is
  implemented and Copilot-audited at `eaae6e9`; its two focused tests pass with
  the live failure ledger unchanged. Ryan's PR decision is next. Config and
  watcher promotion remain separately gated.
- Codex track: rollout admission merged via PR #388, default off. The burn
  isn't reduced until Stage 1 and Stage 2 run under Ryan's grants. No live
  bootstrap, config change, or watcher promotion is authorized.
