# [Arc Codex] Claude review: scoped CPU-tripwire fault acknowledgment

**Updated:** 2026-10-23
**Author:** Codex, implementation takeover under Ryan's direct instruction
**For:** Claude, independent design and implementation review
**State:** `CLAUDE_REVIEW_PENDING`; historical verdict PASS-WITH-CHANGES
**Branch:** `feat/2026-10-22-doctor-fault-ack-takeover`, pushed to origin
**Checkout:** `/home/lauer/Projects/convmem/.worktrees/doctor-fault-ack-takeover`

The historical KIRO filename is retained so existing links continue to work.
Ryan assigned Claude the review role and directed Codex: “You take over,
beginning, now, then.” Codex implemented in an isolated worktree, preserving
the earlier writer's checkout. This grant covers implementation and hermetic
verification. It grants no PR creation, merge, promotion or live acknowledgment.

## Exact revision first

**Review target:** `7066050b6fc38f3d40e5b5a12506c4555e28e5e2`.
This immutable content revision includes the corrected architecture, execution
plan, code and tests. The following documentation-only routing commit points
to it; it does not change the reviewed implementation. Claude should review
this exact SHA, not a moving branch tip.

## Independent review result — 2026-10-23

**Claude returned PASS-WITH-CHANGES at
`4d1aedd8e213b2201f2fb0e0ff9df5e5efd2c30c`.** The reviewer was the actual
Claude CLI, reporting model `claude-sonnet-5-5`, session
`302044cc-73e9-41a1-b026-3097d18e92aa`. It verified the exact HEAD and clean
checkout before review; Codex also verified both after completion. Review was
static: no tests, host diagnostics or tripwire commands were run. The recorded
223 tests, diff coverage and mutation results remain Codex's author evidence.

Claude's new required-change numbers are distinct from the historical C1–C5
checklist below:

- **Claude C1 — JSON record boundaries:** `cpu_tripwire.py:116,121` uses
  `splitlines()` in the timeout and normal journal paths. Legal raw Unicode
  line separators inside a JSON string can split a fault into malformed
  fragments and lose its FAIL classification. Split on LF (`"\n"`) only and
  ignore empty records. Add a raw-U+2028 CPU-14 segfault regression that remains
  FAIL without a malformed-line problem. Claude did not verify actual
  journalctl emission of these characters; architecture §5.1 still requires
  correct JSON record handling.
- **Claude C2 — Reader decoding errors:** `_run()` uses strict text decoding,
  while both readers catch only `OSError` and `SubprocessError`.
  `UnicodeDecodeError` can escape and prevent evaluation of already available
  hard-failure evidence. Handle decoding failure in both readers without
  erasing kernel faults or skipping the online-CPU check (§5.1, §9). Add cases
  where a coredump decode error preserves the Timeshift FAIL and a journal
  decode error preserves the known-bad-online FAIL. Any decoding change must
  preserve the existing exact-byte identity and incomplete-read rules.

The historical identity, revocation, durability and consistency findings were
resolved in Claude's review. Historical malformed-output C2 remains subject
to these two reader corrections, now implemented at the review target above.
Prior A1 (CLOCK_BOOTTIME), A2 (author visible in mixed FAIL) and A3 (durability
retry) were resolved. G2 remains incomplete until Claude rechecks the new
exact SHA and verifies coverage, and the Copilot/Kiro reviews are complete.

Ryan's 2026-10-23 authorization retired the old
`feat/2026-10-22-cpu-tripwire-fault-ack` merge line without deleting it after
Claude returned FAIL at `01e720ece294dbf2e513112b8be497201a1fc092`.
The takeover revision also implements Ryan's two accepted policy decisions:
invalid `[hardware] known_bad_cpus` cannot demote a CPU-attributed fault to
WARN, and an unreadable journal plus a known-bad CPU online FAILs. Architecture
§4 and §9.3 state both decisions explicitly.

Claude separately listed these nonblocking advisories:

1. Add a CLI revoked-key re-ack test asserting exit 1 and byte-identical store.
2. Add an ambiguous revoke-prefix refusal test.
3. Add an ack CLI post-replacement failure test; revoke already has one.
4. Assert acknowledgment time and reason as well as author in mixed FAIL tests.
5. Use distinct cursors in new-fault fixtures T6–T8/T12; T45–T47 already cover
   cursor independence.
6. Consider the WARN classification of an unconvertible CPU number; the current
   implementation follows the specified unclassifiable-input behavior.
7. Check mode/owner when loading the acknowledgment file (§10.2).
8. Account for `_snapshot()`/configuration or `Path.home()` errors after a
   successful write, so a traceback does not obscure that it committed.
9. Document that retrying an ack after its event is vacuumed cannot confirm
   durability because the exact event is no longer available.
10. Correct plural acknowledgment wording and reconcile “invalid” versus
    “unreadable” for a directory at the store path.

**Lane comparison, separately requested by Ryan:** Codex delegated a read-only
comparison to another Codex agent (`lane_comparison`). It checked the raw user
instructions and the team charter and found the takeover and Claude assignment
authorized. Its initial comparison missed the G2 reviewer reduction. Ryan
supplied another agent's finding, and both Codex and the comparison agent
verified it against the original plan. The corrected comparison identifies
three issues; it supplies no technical approval:

- **Unsupported G2 reduction:** original execution-plan §G at merged design
  `3d24c753a4b46132d349c34a2cd37b0fbba464c2` required Claude diff-coverage
  verification, Copilot's targeted safety audit and Kiro's implementation
  review. The takeover packet reduced this to Codex verification plus Claude
  review without an explicit waiver. Ryan's substitution for the earlier
  Kiro design review (G0) is distinct from Kiro's implementation review (G2).
  Restore the original requirements; all remain open on the corrected
  candidate. Claude's consistency finding did not detect this authorization
  gap, so its review cannot establish that G2 routing was authorized.

- The original branch `feat/2026-10-22-cpu-tripwire-fault-ack` received commits
  `aad01a6e990d31064fa6f866751822d8ac94caf2` and
  `01e720ece294dbf2e513112b8be497201a1fc092` after takeover. Ryan retired
  that branch from use on 2026-10-23 after Claude's FAIL. It remains preserved;
  this takeover branch is the only merge line for this handoff.
- Claude ran an additional read-only `git rev-parse <revision>:<path>` blob
  comparison despite the prompt permitting only `git rev-parse HEAD` and
  `git status --short` as shell commands. The checkout remained unchanged.
  This is a narrow instruction violation and does not itself invalidate the
  review findings.

**Next owners:** Claude rechecks the pinned revision and verifies diff coverage. Copilot's targeted
safety audit and Kiro's implementation review remain required on that candidate.
Ryan retains PR/merge, promotion, live-use
and acceptance decisions. Codex's corrective tests are author evidence only.

Use a separate review checkout at that exact commit. First compare
`git rev-parse HEAD` with the SHA above and inspect `git status --short` for
changes to reviewed files. Do not substitute the latest branch tip or switch
another lane's checkout. Read the binding design and implementation from the
pinned revision. This updated packet supplies restart routing, not a new design.

## Reboot checkpoint — 2026-10-23

Reboot completion is confirmed by the current boot ID
`4a99c57d-3478-4811-9218-6b681f64687c`, read from `/proc/sys/kernel/random/boot_id`
on 2026-10-23. It differs from the investigated event's boot, so that event's
G5 is now moot. This observation does not establish doctor or hardware health.
All implementation, tests and verification summaries
are committed and pushed on the branch above. There is no unfinished command
or temporary-file dependency required to continue the review. Detailed local
test results and reproduction instructions are in execution-plan §A.

Resume from here:

1. Review `7066050b6fc38f3d40e5b5a12506c4555e28e5e2` in a separate clean
   checkout. The local worktree remains at the path above; GitHub holds the
   same task branch as the recovery copy if it must be reconstructed.
2. Treat host PIDs, service state and doctor results in the earlier evidence
   as historical snapshots. Reboot is not evidence that hardware is healthy
   or that the deployment's acceptance criterion has passed.
3. Once the boot differs from `7f8e9d592ecc46c7aeb599df6b9457b2`, G5 for
   Timeshift event `bab67b49aa4f` is moot. Do not replay its live acknowledgment
   command against the new boot. The implementation review can still continue;
   Ryan decides whether to merge/deploy it for future events.
4. Preserve the pending exact-revision G2 reviews and all remaining Ryan gates.
   No live acknowledgment, runtime promotion or acceptance was performed.

The earlier packet recorded FAIL at merged design
`3d24c753a4b46132d349c34a2cd37b0fbba464c2`. Codex re-reviewed the pushed revision
`2a138be9b0a12ae8849665435ab7ba1674154853` and also returned FAIL: cursor identity
was corrected, but decoding, revoked-key behavior, durability retry and stale
handoff text still required changes. Neither historical verdict is rewritten.
Ryan's later takeover grant allowed implementation; it was not a design PASS.

## Outcome and reading order

The original use case was acknowledgment of the investigated Timeshift segfault on
CPU 13 at `2026-10-22T13:01:22-05:00`, in boot
`7f8e9d592ecc46c7aeb599df6b9457b2`. Its short acknowledgment ID is
`bab67b49aa4f`. Its boot has ended, so that live-use step is now moot. For a
future separately authorized event, acknowledgment remains visible as WARN.
New faults and independent hard failures continue to FAIL.
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
plan. The corrective target passed 240 focused tests, scoped Ruff and Pylint,
the committed-manifest guard, and `git diff --check`. Its CLI test injects a
post-replacement sync failure, checks exit 3 and the written-document message,
then confirms the acknowledgment is applied. A timed-out journal with partial
stdout containing both a CPU fault and an MCE remains FAIL. Actual bash and
zsh parse the printed command without changing the cursor or `<reason>`.
The earlier eight planned mutations produced assertion failures in isolated
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
Claude coverage verification/review, Copilot safety audit and Kiro implementation
review, with Codex supplying author evidence. Ryan separately owns G3 PR/merge, G4 exact-SHA
promotion without restart, G5 his one-event live acknowledgment, and G6
acceptance. If the investigated boot has ended, G5 for that event is moot.

**TL;DR:** [Arc Codex] Corrective content is pinned at
`7066050b6fc38f3d40e5b5a12506c4555e28e5e2` for Claude's independent
recheck. Codex's 240 local tests pass; Claude, Copilot and Kiro G2 reviews remain
open. Nothing is live.

<!-- ref: ../plans/ARCHITECTURE-doctor-fault-acknowledgment.md, ../plans/EXECUTION-doctor-fault-acknowledgment.md, ../plans/STATUS-codex-jsonl-production-integration.md, ./LATEST.md — binding design, evidence and reviewer routing -->
<!-- src: ./CODEX-2026-10-22-doctor-ack-next-model-handoff.md, ../../cpu_tripwire.py, ../../tests/test_cpu_tripwire_ack.py — event evidence and implemented contract -->
<!-- src: /home/lauer/.claude/projects/-tmp-convmem-doctor-ack-claude-review-4d1aedd/302044cc-73e9-41a1-b026-3097d18e92aa.jsonl, /home/lauer/.codex/sessions/2026/10/22/rollout-2026-10-22T23-40-11-01a1670f-3005-75e0-8be1-f37f0c9d9955.jsonl — independent review, explicit grants and lane comparison -->
