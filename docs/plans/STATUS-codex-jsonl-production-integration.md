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
| Existing-source bootstrap | Runtime paid-cap split landed at `32fae68` on `fix/2026-10-10-kiro-bootstrap-paid-attempt-accounting` (DeepSeek-only cap; Ollama observed but exempt). Hermetic evidence: `tests/test_incremental_jsonl_bootstrap_safety.py` + `tests/test_incremental_jsonl_bootstrap_command.py` — 14 passed locally (fake transports only). No live re-run. | Kiro/Copilot review of branch tip, then Ryan merge/grant decision |
| Watcher activation | Unauthorized; watcher disabled | Separate Ryan promotion/config/restart grant |

## 5. Your Role

Paid-cap runtime correction and matching hermetic tests are on
`fix/2026-10-10-kiro-bootstrap-paid-attempt-accounting` at `32fae68` (uncommitted
test/doc deltas may sit atop that tip in the worktree). Next lane: Kiro/Copilot
review of the branch, then Ryan's merge and live-grant decision. Live bootstrap,
runtime promotion, config change, and watcher operation remain separately
Ryan-gated. Crush/Cursor transcript coverage remains out of scope for this
Kiro-only route.

## 6. What Remains Before Live (sequential)

1. Review the paid-cap accounting correction on
   `fix/2026-10-10-kiro-bootstrap-paid-attempt-accounting` (DeepSeek-only cap
   consumption; Ollama observed but cap-exempt; clarified receipt counters).
2. After review, Ryan decides whether to merge the correction branch.
3. Prepare a new live packet with execution-day source digest, verified backup,
   dimension, enforceable DeepSeek HTTP budget, source-backup disposition, and
   one explicit recovery allowance; obtain a separate Ryan grant before any
   retried live bootstrap.
4. Obtain a later Ryan grant before any runtime/config/restart test. Measure
   calls and coverage by source class.

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
| 2026-10-10 | Cursor | Hermetic bootstrap paid-cap tests aligned to `32fae68` accounting (12 focused passes); branch awaits review |
| 2026-10-10 | Cursor | Recorded live bootstrap paid-cap failure (Ollama embeds counted against DeepSeek `max_provider_http_attempts`); paid-cap-only correction implemented on `fix/2026-10-10-kiro-bootstrap-paid-attempt-accounting`, awaiting review |

## TL;DR

- Arc Codex's coordinator and canary are on main, default off.
- Ryan stopped and disabled the watcher on 2026-10-05 for cost containment.
- Bootstrap safety merged via PR #373; live 2026-10-10 run exposed paid-cap
  mis-accounting. Runtime fix at `32fae68` plus hermetic tests (12 focused passes)
  on `fix/2026-10-10-kiro-bootstrap-paid-attempt-accounting` await review before
  merge or retried live grant.
