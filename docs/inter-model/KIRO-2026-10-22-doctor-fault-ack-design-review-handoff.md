# [Arc Codex] Claude review: scoped CPU-tripwire fault acknowledgment

**Updated:** 2026-10-23
**Author:** Codex, implementation takeover under Ryan's direct instruction
**For:** Claude, independent design and implementation review
**State:** `READY_FOR_CLAUDE_REVIEW`; no independent PASS is claimed
**Branch:** `feat/2026-10-22-doctor-fault-ack-takeover`, pushed to origin
**Checkout:** `/home/lauer/Projects/convmem/.worktrees/doctor-fault-ack-takeover`

The historical KIRO filename is retained so existing links continue to work.
Ryan assigned Claude the review role and directed Codex: “You take over,
beginning, now, then.” Codex implemented in an isolated worktree, preserving
the earlier writer's checkout. This grant covers implementation and hermetic
verification. It grants no PR creation, merge, promotion or live acknowledgment.

## Exact revision first

**Review target:** `4d1aedd8e213b2201f2fb0e0ff9df5e5efd2c30c`.
This immutable candidate includes the corrected architecture, execution plan,
code, tests and the original review packet. Later reboot-checkpoint commits
only make pickup self-contained; they do not advance the review target.

Use a separate review checkout at that exact commit. First compare
`git rev-parse HEAD` with the SHA above and inspect `git status --short` for
changes to reviewed files. Do not substitute the latest branch tip or switch
another lane's checkout. Read the binding design and implementation from the
pinned revision. This updated packet supplies restart routing, not a new design.

## Reboot checkpoint — 2026-10-23

Ryan has requested preparation for shutdown/reboot; completion of the reboot
has not been observed. All implementation, tests and verification summaries
are committed and pushed on the branch above. There is no unfinished command
or temporary-file dependency required to continue the review. Detailed local
test results and reproduction instructions are in execution-plan §A.

After restart:

1. Resume **Claude's independent review** of the pinned SHA above. The local
   worktree remains at the path above; GitHub holds the same task branch as
   the recovery copy if the local checkout must be reconstructed.
2. Treat host PIDs, service state and doctor results in the earlier evidence
   as historical snapshots. Reboot is not evidence that hardware is healthy
   or that the deployment's acceptance criterion has passed.
3. Once the boot differs from `7f8e9d592ecc46c7aeb599df6b9457b2`, G5 for
   Timeshift event `bab67b49aa4f` is moot. Do not replay its live acknowledgment
   command against the new boot. The implementation review can still continue;
   Ryan decides whether to merge/deploy it for future events.
4. Preserve the pending independent review and all remaining Ryan gates.
   No live acknowledgment, runtime promotion or acceptance was performed.

The earlier packet recorded FAIL at merged design
`3d24c753a4b46132d349c34a2cd37b0fbba464c2`. Codex re-reviewed the pushed revision
`2a138be9b0a12ae8849665435ab7ba1674154853` and also returned FAIL: cursor identity
was corrected, but decoding, revoked-key behavior, durability retry and stale
handoff text still required changes. Neither historical verdict is rewritten.
Ryan's later takeover grant allowed implementation; it was not a design PASS.

## Outcome and reading order

Ryan can eventually acknowledge only the investigated Timeshift segfault on
CPU 13 at `2026-10-22T13:01:22-05:00`, in boot
`7f8e9d592ecc46c7aeb599df6b9457b2`. Its short acknowledgment ID is
`bab67b49aa4f`. After separate deployment and live-use grants, the event remains
visible as WARN. New faults and independent hard failures continue to FAIL.
The mechanism is implemented on this branch only; the recorded live doctor
failure and acceptance state are unchanged by these tests.

Read in this order:

1. [Architecture](../plans/ARCHITECTURE-doctor-fault-acknowledgment.md), the binding specification.
2. [Execution plan](../plans/EXECUTION-doctor-fault-acknowledgment.md), including T0–T51, mutation checks and verification evidence.
3. This packet and the [Arc Codex brief](../plans/STATUS-codex-jsonl-production-integration.md).
4. [Event decoding and identity](../../cpu_tripwire_events.py),
   [strict store and writers](../../cpu_tripwire_ack.py),
   [policy integration](../../cpu_tripwire.py),
   [operator commands](../../cpu_tripwire_cli.py), and the thin registrations in
   [convmem.py](../../convmem.py).
5. Existing [doctor integration](../../doctor.py), unchanged;
   [policy regression tests](../../tests/test_cpu_tripwire.py),
   [acknowledgment tests](../../tests/test_cpu_tripwire_ack.py), and
   [doctor tests](../../tests/test_doctor.py).

The original [input handoff](CODEX-2026-10-22-doctor-ack-next-model-handoff.md)
contains the investigated host evidence and the subsequent work queue. It is
historical evidence, not a fresh runtime check or a grant for another queue item.

## Required findings to recheck

- **C1 — Entry identity (§5.2; T2, T9, T14, T45–T47):** the key is boot ID,
  realtime microseconds, source timestamp microseconds, raw MESSAGE SHA-256,
  and the exact opaque `__CURSOR` string. Never parse or normalize the cursor.
  A look-alike entry with another cursor cannot inherit an acknowledgment,
  including after the original is vacuumed. Duplicate full keys are ambiguous.
- **C2 — Decoding and FAIL preservation (§5.1, §9; T43, T49, T51):** one
  `journalctl -k -b 0 -o json --all` read preserves oversized messages and raw
  bytes. Null/invalid/repeated MESSAGEs, duplicate JSON members, malformed
  lines and partial command failures disable acknowledgments for the whole
  read, retaining every decodable fault. Timeout stdout is retained too.
  Numeric conversion failures preserve known fault fields, including the MCE
  kind. Malformed auxiliary coredumps cannot erase kernel faults. Always check
  known-bad CPUs online, even when the journal is unreadable.
- **C3 — Re-ack after revocation (§7–§8; T31, T48):** a revoked deterministic
  key is terminal in schema v1. Re-ack refuses with exit 1, leaves the valid
  file byte-identical, and keeps FAIL. `show` supplies no re-ack command.
- **C4 — Post-replacement durability (prior A3; §8; T38, T40, T50):** a
  directory open/fsync failure after replacement leaves the complete new
  document visible, with crash durability uncertain. The CLI explicitly
  reports uncertainty, not “nothing changed.” Retrying the same active ack
  or already-revoked revoke fsyncs the existing file and directory under lock;
  it changes no bytes or attribution and cannot report success if sync fails.
  Failure before replacement leaves the original document unchanged.
- **C5 — Packet consistency:** this packet, architecture, execution plan,
  STATUS and LATEST must all describe the same five-field key, decoding rules,
  implementation state, reviewer and remaining gates. Check the complete
  design, not only the listed edits.

## Prior advisories to recheck

- **A1:** `_SOURCE_MONOTONIC_TIMESTAMP` is the legacy field name used here
  for the kernel CLOCK_BOOTTIME timestamp. Do not confuse it with journald's
  reception CLOCK_MONOTONIC timestamp or derive it from realtime.
- **A2:** mixed FAIL output includes acknowledgment ID, author, timestamp
  and reason, while retaining the independent hard-failure description.
- **A3:** covered by required durability finding C4 above.

Also check lossless MESSAGE evidence across ack/store/reload, whole-file
schema rejection, current-boot cross-checks, shell quoting of cursors, TTY
confirmation and visible WARN rather than PASS. TTY is an operator affordance,
not an authorization boundary. The file remains editable by its owning user;
it is not a tamper-proof authority ledger.

## Verification and limits

Codex ran the focused hermetic tests and the checks recorded in the execution
plan. All eight planned mutations produced assertion failures in isolated
copies, not collection errors. Their purpose was to prove that tests detect
cross-boot/process/cursor widening, false PASS, incomplete-read acknowledgment,
partial-file acceptance, revoked-key reactivation and skipped durability retry.

The test fixtures redirect HOME, use temporary evidence/store paths and block
real journalctl/coredumpctl and network access. No real tripwire command or
live acknowledgment was run. No full repository pytest, real hardware test,
power-loss test, production canary, runtime promotion or watcher restart is
claimed. The filesystem failure tests establish handling of injected errors,
not proof of storage-device durability under every crash condition.

The repository manifest classifies new tripwire modules/tests as `unrelated`
and refreshes the existing `convmem.py` content hash; it grants no new watch
scope. Redundant CLI-local imports were removed because the added usage lines
changed line-number-bearing Pylint fingerprints; the lint baseline was not raised.

## Review boundaries and verdict

Review read-only. Do not invoke tripwire commands, edit live configuration,
run host diagnostics, promote runtime, restart the watcher, or acknowledge an
event. Tests are already recorded; any independent rerun must retain their
hermetic inputs. Other Arc Codex queue items remain separate.

Return **PASS**, **PASS-WITH-CHANGES**, or **FAIL**, naming the exact reviewed
SHA. Number required changes C1, C2, … with affected sections or code paths;
list advisories separately. State whether the earlier findings are resolved
and whether the implementation conforms to the corrected architecture.
If a point is undecidable, name the specific missing evidence. A review PASS
does not grant a PR, merge, promotion, live acknowledgment or acceptance.

G0 is historical design review; G1 is Ryan's explicit takeover grant; G2 is
verification and Claude review. Ryan separately owns G3 PR/merge, G4 exact-SHA
promotion without restart, G5 his one-event live acknowledgment, and G6
acceptance. If the investigated boot has ended, G5 for that event is moot.

**TL;DR:** [Arc Codex] Codex implemented exact-entry acknowledgments and the
required design corrections under Ryan's takeover grant. Claude reviews the
pinned exact SHA next; the reboot pickup is saved here. Earlier FAILs remain recorded; nothing is live.

<!-- ref: ../plans/ARCHITECTURE-doctor-fault-acknowledgment.md, ../plans/EXECUTION-doctor-fault-acknowledgment.md, ../plans/STATUS-codex-jsonl-production-integration.md, ./LATEST.md — binding design, evidence and reviewer routing -->
<!-- src: ./CODEX-2026-10-22-doctor-ack-next-model-handoff.md, ../../cpu_tripwire.py, ../../tests/test_cpu_tripwire_ack.py — event evidence and implemented contract -->
