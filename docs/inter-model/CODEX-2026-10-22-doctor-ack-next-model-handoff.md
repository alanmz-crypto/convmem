# [Arc Codex] New-model handoff: reviewed acknowledgment of one boot-scoped crash

**Date:** 2026-10-22

**Author:** Codex, deployment/verification/docs lane

**For:** a fresh Codex design model, then Kiro review; not Cursor Execute yet

**Authorization:** Ryan prioritized acknowledgment of this specific crash while
continuing to flag new faults, cannot reboot now, and requested a handoff when
this session cannot appropriately finish the priority. His original stop rule
requires this model to stop at any gate redesign and hand off to a new model.

## Resume state

- **State:** `NOT_STARTED` for acknowledgment design and implementation.
  This document completes the handoff only; priority #1 is not complete.
- **Branch:** `docs/2026-10-22-doctor-ack-next-model`.
- **Base:** `origin/main` at `75d8e2ada48da930283a7911c3db7efc807fc9f3`,
  Ryan's squash merge of deployment/status docs PR #413.
- **Tip and push:** resolve with `git log -1 origin/docs/2026-10-22-doctor-ack-next-model`;
  push immediately after each commit. The final chat reports publication status.
- **PR:** #414 is open for this handoff under Ryan's PR Steward assignment;
  #413 is already merged. Ryan owns the merge decision.
- **Next lane:** Ryan dispatches a fresh design model with this brief. Kiro
  reviews the resulting design. Cursor implementation, live acknowledgment,
  runtime promotion and acceptance each retain their own required authority.
- **Track A:** `/home/lauer/.codex/sessions/2026/10/22/rollout-2026-10-22T13-30-40-01a164e1-2862-7ac0-a1f8-3611e92c4496.jsonl`;
  manual indexing has been deferred to the running watcher, without `--now`.

## Product outcome and present boundary

Ryan wants to acknowledge the already-investigated Timeshift crash without a
reboot, while doctor continues to flag new faults. There is no existing
acknowledgment command or saved failure flag to reset. The old deployment
contract's doctor-exit-0 criterion remains unmet; the startup waiver does not
accept the deployment or change that criterion.

The current model did not choose a new identity scheme, storage format, CLI,
authorization mechanism or verdict policy. Those are design work for the new
model. This is a problem/evidence handoff, not an approved architecture or an
Execute grant. Do not infer implementation or live-use authority from it.

## Evidence already established

The deployed runtime is clean `main` at
`1a686753d8fd1b710883050e8a4f9c45b7ae1e26` in `.worktrees/runtime-main`.
The publication fence deployment and one watcher restart are complete; both
that grant and the later exact stale-mount cleanup grant are consumed.
PR #413 changed docs only; its merge does not need a runtime promotion.

The latest service check in this handoff session found the watcher active,
PID `904311`, activation `2026-10-22 13:52:35 CDT`, `NRestarts=0`.
Normal admitted Codex indexing commits were observed after deployment.
These facts establish activity, not full acceptance or a new grant.

Deployed-runtime doctor previously completed with exit 1 and exactly one failed
check, `cpu_tripwire`. Local/offsite backup, index and native-crash checks
passed. The targeted tripwire recheck still returns the same failure.
No evidence has been deleted and no exception has been activated.

Exact kernel event, read from `journalctl -k -b 0 -o json`:

- Host: `archlinux`.
- `_BOOT_ID`: `7f8e9d592ecc46c7aeb599df6b9457b2`.
- `__REALTIME_TIMESTAMP`: `1792692082959438` microseconds;
  rendered time `2026-10-22T13:01:22-05:00`.
- Process/PID: `timeshift[835726]`; signal context is a segfault at address 0.
- CPU attribution: `likely on CPU 13 (core 33, socket 0)`.
- Message: `timeshift[835726]: segfault at 0 ip 0000557bdb8648da sp 00007ffe1ccb1ff0 error 4 in timeshift[168da,557bdb854000+40000] likely on CPU 13 (core 33, socket 0)`.

Those fields are evidence, not a chosen acknowledgment key. Revalidate them
against the current boot before any eventual operation; a PID or process name
alone must not be treated as proof that a different event is the old crash.

Ryan intentionally unplugged external USB drives for testing. The configured
Timeshift backup volume disconnected at `13:01:18 CDT`, followed by I/O errors
and the crash four seconds later. Storage-loss error handling is the leading
explanation; the exact Timeshift bug and any CPU defect remain unproven.
No machine-check event was found in the earlier checked boot journal.

The failed `2026-10-22_13-00-00` snapshot was absent. Replacement
`2026-10-22_13-03-52` had hourly/daily metadata and a journal success at
`13:07:24 CDT`; this was not a restore or filesystem-integrity test.
Ryan completed the root active-user check and normal unmount of the stale
`/run/timeshift/835726/backup` mount. At `14:48:28 CDT`, Codex verified it
absent, the reconnected backup volume still read-write, and the watcher
unchanged. Retention's earlier failed unit status was not reset or retried.

## Existing integration points to inspect

- `cpu_tripwire.py`: `read_kernel_faults()` reads the current boot's journal;
  `read_coredumps()` is bounded by boot time; `evaluate()` classifies faults;
  `check()` gathers and evaluates signals. It does not store a failure latch.
- `doctor.py`: `_check_cpu_tripwire()` maps `fail` to a failed `DoctorCheck`.
- `convmem.py`: doctor CLI; no tripwire acknowledgment/reset option exists.
- `tests/test_cpu_tripwire.py`: existing parsing and policy tests.
- `docs/inter-model/KIRO-2026-10-17-cpu-tripwire-advisory-userspace-handoff.md`:
  historical policy rationale; PR #398 is merged, not pending deployment.
- `incremental_transform_contract.py` and the Arc Codex brief: preserve semantic
  transform compatibility; do not resurrect unrelated-module checkpoint invalidation.

The current policy FAILs on machine checks, known-bad CPUs returning online,
and CPU-attributed faults outside the configured known-bad set `[4, 5, 8, 9]`.
Unattributed userspace faults are WARN. That classification alone does not
establish a hardware root cause for this Timeshift crash.

## Required design questions and review bar

The new model should produce a bounded design and execution plan for Kiro
review, resolving rather than assuming:

1. What evidence identifies only the approved event, including boot boundaries
   and journal/coredump correspondence?
2. Who may acknowledge it, where authority and reason are recorded, how doctor
   makes an acknowledgment visible, and how it can be inspected or revoked?
3. How malformed, missing, stale, conflicting or interrupted acknowledgment
   state behaves without silently broadening an exception?
4. How the policy continues to fail on new unacknowledged faults, including a
   new Timeshift crash or another crash on CPU 13; machine checks and known-bad
   CPUs returning online must not be hidden by this event's disposition.
5. Which tests demonstrate both acknowledgment of the intended fixture and
   rejection of unrelated/new events, without touching host logs or production
   state? Include cross-boot, recurrence and invalid-state negative controls.
6. What separately authorized implementation, deployment, one-event live use,
   rollback and verification steps are required? Preserve the distinction
   between a changed doctor result and Ryan's deployment acceptance decision.

No answers to those questions are approved by this handoff. Use the relevant
builder references and the team's normal Codex design → Kiro review → Ryan
Execute grant → Cursor implementation/review process.

## Non-goals and hard stops

- No reboot now, kernel/journal clearing, coredump deletion, CPU offlining,
  expansion of `known_bad_cpus`, process-name-wide exception or blanket bypass.
- No production code, tests, scripts or live configuration changes in this
  handoff branch. Its manifest edit classifies this new document only.
- No watcher restart/promotion, protocol deployment, quarantine clearing,
  retention reset/retry, snapshot deletion, bootstrap, bulk index or provider calls.
- No merge, force-push or automatic PR creation. Ryan owns merge and ledger writes.
- No claim that acknowledgment proves the machine healthy, repairs Timeshift,
  validates a backup restore, or supplies missing Stage 1/Stage 2 evidence.

## Queue after priority #1

Keep these separate from the acknowledgment change; they are not authorized
implementation bundled into it:

1. **Arc Codex evidence reconciliation:** locate authoritative Stage 1/Stage 2
   and residual-burn records; otherwise keep them `Ryan to confirm`. Review
   the reported quarantines and old wedged transaction without clearing them.
   Do not repeat paid canaries merely because evidence has not been located.
2. **Next substantive ingestion implementation, issue #393:** changed Crush
   SQLite databases still use the legacy route and re-pay unchanged history.
   The issue's fake-provider probe reports 3 summary/distill calls on first
   index, 0 unchanged, then 4 after one appended message. A new design/review
   and scoped grant are needed; the Codex/Kiro JSONL implementation is not
   proof of Crush coverage.
3. **Retrieval correctness:** issue #320 tracks stale golden checks and a
   candidate-pool recall gap. Its existing measurement found a larger pool
   improves the demonstrated case but adds latency; do not blindly change
   live config or repeat the completed measurement. Issue #263 separately
   tracks bounded verbatim evidence and confident false negatives.

The cross-arc rollup and automated brief still contain stale watcher/cap
claims. Prefer the current Arc Codex brief plus fresh read-only runtime checks;
do not revive old activation packets or treat issue bodies as current grants.

## Handoff acceptance and pickup

- This handoff is prepared on a separate docs branch based on merged #413.
- LATEST and the Arc Codex brief point here; §7 hard stops remain unchanged.
- Classify this file `unrelated` in the repository-knowledge manifest; pass
  `git diff --check` and the committed-manifest pytest on a clean committed tree.
- Commit, push immediately with the explicit branch refspec, and report the
  final tip. Do not call priority #1 implemented or reviewed-PASS.
- The receiving model reads this entire document and the arc brief, confirms
  its design assignment with Ryan, and does not execute live acknowledgment
  using the previous deployment or cleanup grant.

**TL;DR:** [Arc Codex] No existing reset can clear this boot-scoped crash.
Priority #1 needs a fresh-model acknowledgment design and independent review;
it is not implemented. Leave the watcher running and retain the product queue.

<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md, ./LATEST.md — current arc state and pickup routing -->
<!-- src: ../../cpu_tripwire.py, ../../doctor.py, ../../convmem.py, ../../tests/test_cpu_tripwire.py — existing behavior and integration points -->
<!-- src: ./KIRO-2026-10-17-cpu-tripwire-advisory-userspace-handoff.md — historical policy rationale -->
