# Safe Harbor — remaining issues

Codex source audit, 2026-10-25. Requested by Ryan; the investigation was read-only, with these issue files as its only authored changes. Ryan's later shutdown request adds a documentation-only checkpoint and routing updates. Codex contributed to this arc, so this is a follow-up audit, not an independent acceptance review.

## Shutdown checkpoint — start here

**State: paused for Ryan's planned two-week workstation shutdown beginning October 26.** The assessment is complete; the four findings remain open. No finding has been reproduced or corrected. The initializer remains parked. There is no evidence from this assessment that requires starting a repair before shutdown.

**Saved branch:** `docs/2026-10-25-safe-harbor-shutdown-checkpoint`, based on `4b4796b6a667509f94475a5a14424204947fbb12`. This is a documentation-only checkpoint, not an implementation candidate or merge request. It preserves all five issue documents and updates Safe Harbor's routing. The earlier initializer/evidence branch is separately preserved at `2b95f58ef79802f80058b07e125bf73802db5f1e`; its origin ref was checked October 25. Do not merge or deploy that branch to resume this assessment.

**Assignment on return:** Cursor performs bounded, isolated **SH-001 validation only**; Codex supervises scope and assesses the evidence. Ryan's October 25 instruction to assign bounded validation supplies this next-step scope. No Cursor session has been started or acknowledged the assignment. SH-002–SH-004 have no assigned implementation lane. Runtime corrections need a separate decision after the validation results.

### Resume prompt

> Resume Arc Safe Harbor from `docs/2026-10-25-safe-harbor-shutdown-checkpoint`. Read `Issues/Arc/Safe_Harbor/README.md`, `SH-001-jsonl-append-boundaries.md` and `docs/plans/STATUS-safe-harbor.md`. Codex supervises; Cursor owns the queued SH-001 isolated validation. Keep the initializer parked and SH-002–SH-004 separate. Confirm the current source and whether another lane has since delivered a correction. Then prepare/run the real admitted-recovery cases in an isolated worktree using the existing pre-import bootstrap, with synthetic stores and independent event/export/Chroma checks. Return separate results for missing-event-newline, missing-export-newline and valid controls before any runtime correction. No production recovery, service/backup/restore actions, PR, hosted CI, merge or deployment. Do not manually index this Codex transcript while the watcher captures it.

The detailed [validation scope](SH-001-jsonl-append-boundaries.md#validation-before-correction) is the handoff contract. Start from a pinned current-main revision and report drift from the audited source before relying on the original finding. Test/harness changes may reproduce the issue; runtime changes are excluded. Do not launch background work across shutdown or treat earlier doctor/backup PASS results as current after two weeks.

To recover the saved documents in an existing clone without switching its shared checkout:

```bash
git fetch origin refs/heads/docs/2026-10-25-safe-harbor-shutdown-checkpoint
git show FETCH_HEAD:Issues/Arc/Safe_Harbor/README.md
```

This turn's doctor exited 0 with five nonfatal warnings, current local/external backup PASS, no guard quarantine and zero native faults this boot. These observations do not qualify a restore or prove the four findings harmless. No tests or new backup/restore operations were run for this checkpoint.

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

<!-- ref: ./SH-001-jsonl-append-boundaries.md, ./SH-002-revision-export-retry.md, ./SH-003-finding-revisions-narrow-evidence.md, ./SH-004-new-guard-directory-durability.md — audit findings -->
<!-- src: ../../../chroma_write_guard.py, ../../../propose_decision.py, ../../../conflict_events.py, /home/lauer/Projects/convmem/.worktrees/feat-2026-10-22-safe-harbor-legacy-initializer/docs/plans/STATUS-safe-harbor.md, /home/lauer/Projects/convmem/.worktrees/feat-2026-10-22-safe-harbor-legacy-initializer/docs/plans/VERIFY-safe-harbor.md -->
