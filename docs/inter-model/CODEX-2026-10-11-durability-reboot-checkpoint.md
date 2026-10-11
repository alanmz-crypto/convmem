# [Arc none] ConvMem durability review — reboot checkpoint

**Date:** 2026-10-11

**Author:** Codex, architecture/planning lane

**For:** Ryan and the Codex session resuming after the Rescuezilla backup

**Purpose:** Preserve the agreed direction and remaining decisions on GitHub before a reboot. This is a resume handoff, not an approved architecture or an implementation grant.

## 1. Resume state and authority

- **State:** `BLOCKED_ON_RYAN` for architecture drafting; the review and this checkpoint are complete once the containing commit is pushed.
- **Branch:** `plan/2026-10-11-durability-reboot-checkpoint`.
- **Local worktree:** `/home/lauer/Projects/convmem/.worktrees/plan-2026-10-11-durability-reboot-checkpoint`.
- **Base:** `6a23aa93184460ed853996608bb28190c61f8d89`, fetched `origin/main` when the checkpoint branch was created.
- **Checkpoint revision:** the commit containing this file; use its GitHub commit/history link rather than a mutable operational-state claim.
- **Publication:** commit and explicit-refspec push are required before telling Ryan the checkpoint is saved. The final chat supplies the verified remote commit and direct reading link.
- **PR:** not opened. This checkpoint does not require a merge to survive the reboot.
- **Authorization for this work:** Ryan asked to preserve the work on GitHub before rebooting for a Rescuezilla backup. This authorizes the documentation checkpoint and its publication.
- **Pending:** Ryan's backup completion, arc codename and planning-only drafting grant. `Safe Harbor` / `safe-harbor` is a proposal, not an accepted arc identity.
- **No grant here:** implementation, deployment, service changes, live restore, corpus writes, session indexing, merging, or Recovery Authority T4/V4k work.

The shared checkout and deployed runtime were not switched. No new arc brief was created: the named architecture effort has not started. This checkpoint is discoverable from this branch's `LATEST.md`.

## 2. Product goal and provenance

Ryan's priority is durability of the combined code and governance over time; usability and speed are second. The original requirements remain:

1. **No verified recovery point, no risky change.**
2. **Unexpected result, stop and investigate.**
3. **Never repair production blindly.**

The conversation contained several Kiro/Codex/Opus review iterations. Early claims were corrected: inspecting a checkout is not inspecting the deployed runtime; persistent quarantine already exists; collection creation is not the only incidental read-path write; snapshot existence is not proof of recovery; and a one-time inventory does not prevent future drift.

Do not replay the entire adversarial review. Ryan explicitly invoked [Decision and Review Guardrails](DECISION-REVIEW-GUARDRAILS.md), especially delta review and the non-negotiable safety floor. Reopen a settled decision only for new evidence, a changed artifact, or an unresolved safety contract.

Percentages in the conversation express judgment confidence, not incident probabilities. Typical source-grounded conclusions were 85–95%; action ordering was about 75%. Agreement among reviewers is not additional empirical evidence.

## 3. Ownership and next artifact

Agreed role allocation:

1. Codex authors architecture and execution planning.
2. Claude Opus performs independent review.
3. Codex addresses findings; Opus reviews the delta.
4. Kiro provides governing design sign-off.
5. Ryan approves the relevant phase.
6. Cursor implements only the approved and authorized work.

One review plus one delta is the expected cadence, not permission to leave a safety blocker unresolved. Preserve any separately applicable audit gates. A Kiro execution-plan rejection returns to Ryan before resubmission, per the [team charter](TEAM-CHARTER-2026-07-06.md#L119).

After Ryan names and authorizes the arc, create `docs/plans/ARCHITECTURE-<slug>.md` and matching `STATUS-<slug>.md` on a `plan/` branch, using the existing STATUS template and required active-arc entries. Execution planning follows the accepted architecture through its applicable gates. Do not treat this checkpoint as that architecture or as a Cursor Execute handoff.

## 4. Agreed direction

### Existing recovery arrangements first

Use Rescuezilla and Restic before assuming another backup subsystem is necessary. Ryan reports weekly Rescuezilla whole-system backups and says a more recent image is easy to make. A fresh offline image is a practical candidate recovery point before planned corpus-affecting maintenance, subject to scope and usability evidence.

Distinguish independent access, a particular usable recovery point, capture-method consistency, and operational detection. A PASS for one does not establish the others. The acceptable loss window is determined by the newest usable recovery point, not backup frequency alone.

### Detector is a separate bounded decision

The CPU/vector-loss detector in PR #341 is candidate revision `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`, exactly one commit after the reviewed deployed revision `a92a74eb326b3eaa59087b707de10153c7cc0c63`.

The review supports considering that exact observational deployment without waiting for a complete recovery exercise (85% confidence). The added audit reads the corpus under the guard lock and writes audit/control records; it does not call repair. It supplies detection, not durable incident containment. Starting watch is a different operation and was expressly excluded. Advancing to current `origin/main` is also a different deployment.

No deployment has been authorized or performed in this session. Refresh runtime identity and relevant preflight observations at any later authorized deployment; do not promise the new doctor checks will PASS.

### Focused containment and preservation

The future architecture should cover unavailable versus absent state, tombstone-aware approval recovery, recovery-point checks on risky recovery paths, preserving damaged evidence, and containing guarded writes after an unvalidated restore. Identify the scope of each policy, including non-Chroma durable state; local lock/fsync protections do not establish a shared recovery policy.

Prefer existing enforcement boundaries and fewer unintended write paths. Do not claim that an application guard constrains arbitrary same-user filesystem actions.

### Deferred mechanisms

Defer a general operator HOLD, an approved-writer identity registry, a global read-constructor change, and the live-backup freeze. Decide whether stronger routine capture coordination is needed after establishing the acceptable loss window and actual image coverage. More recent images may address planned maintenance without a custom freeze; they do not automatically solve consistency for every intervening live Restic snapshot.

## 5. Recovery evidence and its limits

### Ryan's statements

- Weekly Rescuezilla whole-system backups are part of the existing practice.
- A new image can readily be made before the next phase.
- Ryan intends to reboot for a backup; completion has not been reported at this checkpoint.

### Interlocutor-reported evidence, not independently inspected by Codex

- Attached drive `rszl-larch-5t-fs` reportedly holds `2026-09-16-06-img`, a roughly 250 GB compressed whole-disk image of `nvme1n1` including its boot and root partitions.
- The reported image covers the ConvMem data root, local Restic repository, code and configuration; `nvme0n1` with Ollama models was excluded.
- The image reportedly predates the September 19–20 corruption incident and was captured offline.
- The drive reportedly had approximately 160 GB free: insufficient for a second image of the same approximate size without another destination or more capacity.
- The reported capture timestamps span about 12 minutes. This does not establish total reboot, verification or restoration time.
- The image probably contains the current Restic password based on partition coverage and the live file's modification time. Its archived presence and recoverability have not been demonstrated.

Preserve the reported pre-incident image when arranging a newer backup. Do not delete it or overwrite the only image to make space under this handoff. Record the new image's identifier, completion time, covered volumes and destination after the backup. Physical separation, restore history and the acceptable loss interval remain owner inputs.

### Codex observations from this conversation

- Installed launcher pointed to `.worktrees/runtime-main/convmem.py` using the conda interpreter.
- Reviewed deployed revision: `a92a74eb326b3eaa59087b707de10153c7cc0c63`.
- Shared checkout reviewed: `fb923d58eb43c2fad781fc63a4d863dc63847ff9`, on an unrelated feature branch. It was not the deployed code root.
- Current configured Chroma targets matched when inspected. Missing operation-to-backup target binding is a latent defect, not evidence of a currently wrong-corpus backup.
- Earlier doctor output showed local snapshot `f8d69dc1199636f66d6216f0325cf4218c566c829907dd205c244d00115c324b` and external copy `a38bd4c7bfac4aa5c44634674138fa9c65f83cf37d7b3025c952b5368786f449` as PASS.
- **Latest checkpoint doctor run exited 0, but external health changed to WARN:** the repository was unavailable at its configured mount path. The local snapshot still passed; the configured offline password-copy path still warned. This does not establish that the external copy was deleted. Mount/access state must be refreshed after reboot.
- The reviewer's live census and CPU-log observations were not repeated by Codex during checkpoint preparation. A reported zero-lost-ID census is narrower than absence of silent or semantic corruption.

Doctor was invoked as required by the session protocol. No claim is made that it is physically write-free. No backup restore, test suite, service change or session indexing was run for this checkpoint.

## 6. Unresolved contracts for the architecture author

### A. Rejected backup eligibility — interface finding

The deployed backup applies the qualifying tag during capture, and the gate later selects by tag, path and date. Returning failure after a post-capture signature check would leave the completed snapshot eligible for a later gate invocation.

Any future freeze design must make failed or interrupted qualification remain ineligible across restarts. Provisional tagging and promotion is one suggestion, not an accepted implementation. Account for snapshot-ID changes and external-copy lineage if tags are changed. The decisive future check is a fresh gate invocation after rejected/interrupted qualification, not merely the backup process's exit status.

Sources at the reviewed deployed revision:

- [Tag applied during backup, restic_snapshot.py:923](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/restic_snapshot.py#L923).
- [Selection by tag/path/date, restic_snapshot.py:756](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/restic_snapshot.py#L756).
- [Current snapshot permits continuation, backup_workflows.py:187](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/backup_workflows.py#L187).

A SQLite read lock in rollback-journal mode can protect the database file, but that alone does not prove HNSW or whole-data-root consistency. The complete-data backup arc still leaves broader writer coordination open. Clean sample restores do not prove the capture method safe.

### B. Containment publication and reset — local/contract findings

- The candidate audit releases the write lock before classifying and publishing its result. A later skipped/error result can replace a previous FAIL.
- Existing `_quarantine()` persists the marker and raises. Adding containment must coordinate publication with the lock and preserve a useful audit result despite the exception.
- Existing quarantine reset does not itself prove completed repair or authorized release. Reuse of the admission site does not justify claiming a complete general-HOLD contract.
- Existing restore continues when the census returns unavailable; later successful writes can refresh and prune the older local segment generation.
- Existing restore overwrites/unlinks torn files. Preserving them before replacement requires interruption-safe completion and failure handling; a suggested `copy to torn/` is not yet an approved algorithm.
- Approval recovery can conflate unreadable/filtered state with absent state. Tombstone-aware lookup and a recovery gate need focused design and implementation, not a broad redesign.

Sources: [candidate audit, R:796](https://github.com/alanmz-crypto/convmem/blob/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/chroma_write_guard.py#L796), [quarantine, D:605](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/chroma_write_guard.py#L605), [generation pruning and restore, D:728](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/chroma_write_guard.py#L728), and [approval recovery classification, D:97](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/propose_decision.py#L97).

### C. Existing ownership boundaries and follow-up maintenance

Recovery Authority T3 is landed in its STATUS brief, despite stale T3 labels in some orientation surfaces. T4, V4k and live activation remain explicitly gated. Cite the substantive status and hard stops, and do not treat a new arc as authority to bypass them.

Keep backup-service release/interpreter convergence and permission reconciliation visible as separate follow-ups. The reviewed permission deploy fallback can replace unrelated rules; wildcard tool grants can grow with new tools. These observations are not new execution grants or prerequisites for the unchanged detector revision.

Read before drafting:

- [Team charter](TEAM-CHARTER-2026-07-06.md).
- [Decision/review guardrails](DECISION-REVIEW-GUARDRAILS.md).
- [Recovery Authority STATUS](../plans/STATUS-recovery-authority.md), especially section 7.
- [Complete-data backup STATUS](../plans/STATUS-complete-data-backup-correction-v2.md), especially the open consistency audit.
- Relevant [builder references](../builder-reference/README.md) before architecture edits.

## 7. Resume after the reboot

1. Read this file from the pushed branch or its immutable GitHub commit link. No full chat replay is required to recover the current agreement.
2. Ask Ryan whether the new Rescuezilla backup completed and record its identifier, destination and covered volumes. Do not substitute a reported successful capture for demonstrated restore usability.
3. Refresh only the operational facts needed for the next authorized action. Code roots, USB mounts and service states are time-sensitive. Preserve intentionally stopped services; do not start watch as a resume ritual.
4. Confirm the arc codename and planning-only grant. `Safe Harbor` remains proposed. Then create the architecture/STATUS package with the required arc-list entries on a planning branch.
5. Draft the bounded recovery/containment contracts; route through Opus and Kiro as above. Keep the exact detector deployment separately Ryan-gated.
6. Continue preserving each documentation commit remotely. Do not index this session or write a ledger record unless Ryan separately directs it under the current no-live-writes constraint.

Suggested restart message for Ryan:

> Read `docs/inter-model/CODEX-2026-10-11-durability-reboot-checkpoint.md` on branch `plan/2026-10-11-durability-reboot-checkpoint`. Resume the durability planning discussion from its authority and next-step sections. The Rescuezilla backup is [completed/not completed]; its image and destination are [details]. No deployment or implementation is authorized by this resume message.

## 8. Optional documentation PR handoff

No PR is needed for the remote checkpoint to preserve the work. If Ryan later asks to open one, the proposed title and body are:

**Title:** Preserve durability planning decisions before the backup reboot

**Description:**

This documentation checkpoint lets Ryan and the next Codex session resume the durability work after a Rescuezilla reboot without reconstructing the review thread.

- **Who:** Codex prepared the handoff at Ryan's request; Opus remains the independent reviewer and Kiro the governing design sign-off.
- **What:** A resume document and a current-routing link, with the requirements, evidence limits, source revisions, unresolved contracts and authorization boundaries.
- **When:** Before the planned 2026-10-11 backup/reboot; operational observations are explicitly time-bound.
- **Why:** Preserve the agreement and prevent a future session from treating a proposal or stale health result as an execution grant.
- **How:** Documentation only. No architecture approval, runtime change, implementation, restore or indexing is included.

**Merge reading:** [Reboot checkpoint](CODEX-2026-10-11-durability-reboot-checkpoint.md) and [routing pointer](LATEST.md).

**TL;DR:** Save the planning state; resume after Ryan's backup and planning decision. This grants no live action.

## TL;DR

- The requirements remain verified recovery before risky change, stop on unexpected results, and no blind production repair.
- Codex authors; Opus reviews; Kiro signs off; Ryan authorizes; Cursor implements.
- Existing Rescuezilla/Restic arrangements come first. Detector deployment is separate; freeze, identity registry and general HOLD remain deferred.
- This is a reboot checkpoint, not an approved arc or execution plan. Confirm backup completion, arc name and planning scope on resume.
