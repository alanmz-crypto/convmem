# Safe Harbor — remaining issues

Codex source audit, 2026-10-25. Requested by Ryan; the investigation was read-only, with these issue files as its only authored changes. Ryan's later shutdown request adds a checkpoint, routing updates and the five required repository-manifest classifications. Codex contributed to this arc, so this is a follow-up audit, not an independent acceptance review.

## Shutdown checkpoint — start here

**State: paused for Ryan's planned two-week workstation shutdown beginning October 26.** The assessment is complete; the four findings remain open. No finding has been reproduced or corrected. The initializer remains parked. There is no evidence from this assessment that requires starting a repair before shutdown.

**Saved branch:** `docs/2026-10-25-safe-harbor-shutdown-checkpoint`, based on `4b4796b6a667509f94475a5a14424204947fbb12`, now tracked by draft PR **#418**. It preserves all five issue documents, routing and their manifest classifications; it contains no Safe Harbor runtime correction. The earlier initializer/evidence branch is separately preserved at `2b95f58ef79802f80058b07e125bf73802db5f1e`; its origin ref was checked October 25. Do not merge or deploy that branch to resume this assessment.

### Close receipt — 2026-10-25, 23:13 CDT

Ryan requested an immediate recorded stopping point for every agent. **This lane is checkpoint-only and stops after pushing this receipt.** No local test or implementation job is left running by this lane. Hosted CI may finish while the workstation/chat is closed; pending is not PASS.

- **Delivery:** initial checkpoint `23883f65f130f94ba576cf796b9f656dbf5d0534`; manifest correction `b2e6ffef0f76b14d2991d63680961af02cceb64b`. The correction adds exactly five `unrelated` rows to the existing manifest. Include/watch scope, runtime, tests and lint baseline are unchanged. This receipt is a later documentation-only successor; use the remote branch/PR for its exact final tip.
- **Original CI:** run `40245662735` at `23883f6` had **5 failed, 3811 passed, 14 skipped**. Pylint itself passed. One failure was our missing classifications; four concerned SQLite temporary-file placement and watcher-route runner requirements.
- **Qualified local correction evidence:** on the clean `b2e6ffe` worktree, the existing committed-manifest test passed through the Safe Harbor `-I -S -B` parent bootstrap and clean proof-profile child: **1 passed, 0 skipped in 2.23 seconds**, Python 3.13.12, uid 1000, exit 0. Tracked source/harness hashes were unchanged. Temporary logs at `/tmp/safe-harbor-t3-suite-28bq_uk0` are disposable; this receipt and the PR preserve the essential result. This is not full-suite or SH-001 evidence.
- **Shared fixes:** PR **#419** passed all listed hosted checks and was merged at `d54f92bcd78248c8aee8a54df758564752d79aa4` on October 25, 22:49 CDT. Its accepted head was `ab21be08c1689186390a9bb8e4dcc0e5a04e3c95`. Those changes are **not in this checkpoint branch**. On return, inspect current main and integrate the accepted fixes before expecting #418's four shared failures to disappear. Preserve the disclosed host-dependent skips.
- **Pending checks:** #418 run `40263810496` at `b2e6ffe` still had pytest in progress at the close observation; Pylint/security checks passed. Saving this receipt triggers normal successor CI. Read the final candidate's checks on resume; no merge readiness is claimed.
- **Other lane:** #417 is an independent doctor-routing documentation PR, not a dependency on #418. Its owner acknowledged shutdown: clean pushed branch `docs/2026-10-25-doctor-ack-g4-routing` at `0a99bf99491aec9e987f711903b53a137ba140e7`, no local job remaining, hosted pytest pending. That lane retains ownership. If later integration touches shared routing files, preserve both arcs' entries rather than replacing the other lane's work.
- **Coordination:** the shutdown request was sent to the four other active Codex tasks and the #417 owner through the app's thread messaging. Receipt from #417 is recorded above; other sessions own their own checkpoints. Do not infer that every external agent or application has stopped from this lane's completion.

### Session continuity and preservation limits

- Codex session ID: `01a1292d-9453-7023-a056-71c99b70bd12`.
- Full local transcript: `/home/lauer/.codex/sessions/2026/10/10/rollout-2026-10-10T23-16-55-01a1292d-9453-7023-a056-71c99b70bd12.jsonl` (existence and matching session metadata checked during close).
- Task worktree: `/home/lauer/.local/share/convmem/worktrees/docs-2026-10-25-safe-harbor-shutdown-checkpoint`.
- GitHub preserves the committed findings, scope, evidence summary and resume instructions. The raw private transcript is local and is not copied to GitHub. Automatic watcher capture is the configured chat-ingestion route; final-turn ingestion is not asserted here. No manual session index was run.
- No corpus/system-disk backup, restore test, drive custody confirmation or initializer execution follows from this checkpoint. Recovery limits in STATUS remain open.

### First action on return

Inspect draft #418's final tip and checks, current main including #419, and #417's separate routing delivery. Finish the bounded documentation/CI integration only under the applicable owner scope; no force-push or merge is implied. Then return to the queued SH-001 validation below when Ryan resumes. Preserve all four findings and keep the initializer parked.

### Owner-only close record

The pushed checkpoint is the completed preservation record. The curated ledger remains Ryan-owned; Codex did not run these commands. The close search returned generic checkpoint patterns rather than a closer curated decision, so this uses the documented coordination-protocol root. Review the proposal before approving it.

```bash
convmem record \
  --relates-to dec_prop_20260623_161428_c311 \
  --summary "ConvMem Safe Harbor paused with findings and resume state saved in draft PR #418." \
  --rationale "T1-T5 remain accepted and merged. SH-001-SH-004 remain unresolved; initializer parked. Checkpoint and manifest correction are pushed. Shared CI fixes #419 merged; #418 integration and final CI remain pending. Resume from Issues/Arc/Safe_Harbor/README.md. No merge, deployment or live operations granted. Coordination root used because the close search returned no closer curated decision." \
  --author codex-session

convmem record --approve-last
```

**Assignment on return:** Cursor performs bounded, isolated **SH-001 validation only**; Codex supervises scope and assesses the evidence. Ryan's October 25 instruction to assign bounded validation supplies this next-step scope. No Cursor session has been started or acknowledged the assignment. SH-002–SH-004 have no assigned implementation lane. Runtime corrections need a separate decision after the validation results.

### Resume prompt

> Resume Arc Safe Harbor from `docs/2026-10-25-safe-harbor-shutdown-checkpoint`. Read `Issues/Arc/Safe_Harbor/README.md`, `SH-001-jsonl-append-boundaries.md` and `docs/plans/STATUS-safe-harbor.md`. Codex supervises; Cursor owns the queued SH-001 isolated validation. Keep the initializer parked and SH-002–SH-004 separate. Confirm the current source and whether another lane has since delivered a correction. Then prepare/run the real admitted-recovery cases in an isolated worktree using the existing pre-import bootstrap, with synthetic stores and independent event/export/Chroma checks. Return separate results for missing-event-newline, missing-export-newline and valid controls before any runtime correction. No production recovery, service/backup/restore actions, PR, hosted CI, merge or deployment. Do not manually index this Codex transcript while the watcher captures it.

The detailed [validation scope](SH-001-jsonl-append-boundaries.md#validation-before-correction) is the handoff contract. Start from a pinned current-main revision and report drift from the audited source before relying on the original finding. Test/harness changes may reproduce the issue; runtime changes are excluded. Do not launch background work across shutdown or treat earlier doctor/backup PASS results as current after two weeks.

To recover the saved documents in an existing clone without switching its shared checkout:

```bash
git fetch origin refs/heads/docs/2026-10-25-safe-harbor-shutdown-checkpoint
git show FETCH_HEAD:Issues/Arc/Safe_Harbor/README.md
```

The October 25 orientation doctor exited 0 with five nonfatal warnings, local/external backup PASS, no guard quarantine and zero native faults this boot. These dated observations do not qualify a restore or prove the four findings harmless. The only later local test was the isolated manifest check described above; no new backup/restore operations were run.

## Findings

Four bounded issues merit follow-up, in suggested order:

1. **[SH-001 — Recovery can append onto an unterminated JSON record](SH-001-jsonl-append-boundaries.md).** An otherwise complete last record without a newline passes parsing. The next append can join two objects, corrupting the event log or export while reporting completion. Fix the framing checks before effects.
2. **[SH-002 — An interrupted revision can strand the old export](SH-002-revision-export-retry.md).** If Chroma advances but export replacement fails, retry treats the old, previously verified export as a conflict. Preserve the refusal of arbitrary conflicts while defining recovery for this known partial state.
3. **[SH-003 — Revising a finding can erase earlier unresolved details](SH-003-finding-revisions-narrow-evidence.md).** Findings with the same segment/kind/reason replace their prior failure list and details. Retain unresolved evidence within the existing authority; changing a digest alone does not preserve it.
4. **[SH-004 — First-marker durability depends on a later event append](SH-004-new-guard-directory-durability.md).** Marker publication does not sync the new guard directory's parent. A later event append normally does, but its failure can be swallowed while containment is reported. Make that durability requirement part of marker publication.

All are proposed **P2** issues: bounded corrections or explicit recovery decisions, not evidence of an ongoing emergency. This ordering prioritizes potential false success before availability and evidence-retention gaps. Confidence and the strongest qualification appear in each issue; incident probabilities are unknown.

## Scope and evidence

- Initial inspection baseline: deployed checkout `.worktrees/runtime-main` at `1a686753d8fd1b710883050e8a4f9c45b7ae1e26` (clean during inspection).
- Subsequent observation: runtime is now at `4b4796b6a667509f94475a5a14424204947fbb12`, matching `origin/main`, following a separate lane's promotion. The cited implementation files are unchanged from the inspection baseline. The initial assessment used local refs; checkpoint preparation subsequently fetched origin. This lane performed no promotion.
- Current operational context: Safe Harbor's saved STATUS on `feat/2026-10-22-safe-harbor-legacy-initializer` at `2b95f58ef79802f80058b07e125bf73802db5f1e`. That branch's parked initializer was not treated as deployed code.
- Read source, existing tests, accepted architecture/execution contracts, recorded evidence and existing issues. Startup doctor passed; brief, unresolved and a corpus search provided orientation.
- **No tests or reproductions were run for these findings.** Proposed checks are future isolated work, not completed evidence. No fixes, production recovery, service changes, backup operations or session indexing were performed. No secrets were displayed or copied.
- Review covered incident publication/preservation/release, approval recovery and export/event completion, admission binding and freshness consumers. It is not an exhaustive audit of every writer or filesystem/backend behavior.

## Existing limitations kept separate

- Large export reads and memory use are already tracked in the separate local report `Issues/units-export-whole-file-reads-16gib.md` (outside this checkpoint); they are not a new Safe Harbor finding here.
- Live Restic capture consistency and demonstrated restore/boot/application usability remain narrower than backup availability or an image integrity check. These are already recorded recovery-assurance gaps.
- Strict release intentionally refuses newer/pending work and missing backend evidence. The legacy initializer remains parked; this audit does not authorize it.
- No claim that these findings invalidate all prior evidence: each names the additional state or failure boundary the existing checks miss.

## Assessment and ownership — 2026-10-25

**The initializer stays parked. SH-001–SH-004 remain four separate unresolved static findings, without reproduction evidence or an existing corrective delivery.** Cursor is now designated for the queued SH-001 validation only; no runtime implementation is active or assigned by that designation.

The located Claude handoff assessed Cursor's legacy initializer candidate `dd0c4670e0c8e84d0487d6a9460fa755a2d76c84` and recorded Ryan's parking decision on October 22 in commit `1b83699ccbd3d4446973a406b5e6d767a3e32c7d`. Its four missing initializer tests are distinct from SH-001–SH-004. The [saved Claude assessment](https://github.com/alanmz-crypto/convmem/blob/2b95f58ef79802f80058b07e125bf73802db5f1e/docs/plans/VERIFY-safe-harbor.md#claude-verification-and-owner-parking-2026-10-22) records that scope; the later recovery-input update `0147a44f422904d47c2e3c536142d2f5ed694c97` is documentation, not a correction of these findings.

The contacted doctor-acknowledgment lane explicitly disclaimed ownership of SH-001–SH-004 and knew no implementation owner. Its delivery `c8559bd7b82cd4a6da2955b6483b4b1c99ff5196` changes five routing/documentation files only. Codex remains in the assessment lane; there is no confirmed corrective handoff to await or assess.

## Queued first validation

**SH-001 is queued for isolated validation after Ryan resumes**, because it can report completion after making durable state unreadable. Its [selected validation/correction scope](SH-001-jsonl-append-boundaries.md#selected-validation-and-correction-scope--2026-10-25) separates the authorized validation from the still-proposed runtime correction. No tests or fixes have run; the resume prompt above supplies the queued handoff.

The remaining order is SH-002, SH-003, then SH-004. Keep them separate from the first correction: SH-002 needs a decision about sufficient evidence for retry; SH-003 needs retained-scope validation; SH-004 needs a precise directory-sync fault case. No new architecture or general HOLD mechanism is proposed.

<!-- ref: ./SH-001-jsonl-append-boundaries.md, ./SH-002-revision-export-retry.md, ./SH-003-finding-revisions-narrow-evidence.md, ./SH-004-new-guard-directory-durability.md, ../../../docs/plans/STATUS-safe-harbor.md, ../../../config/repository-knowledge/openclaw-watch-scope-v1.json — findings, pause state and checkpoint classifications -->
<!-- src: ../../../chroma_write_guard.py, ../../../propose_decision.py, ../../../conflict_events.py, /home/lauer/Projects/convmem/.worktrees/feat-2026-10-22-safe-harbor-legacy-initializer/docs/plans/STATUS-safe-harbor.md, /home/lauer/Projects/convmem/.worktrees/feat-2026-10-22-safe-harbor-legacy-initializer/docs/plans/VERIFY-safe-harbor.md -->
