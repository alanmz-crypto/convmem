# [Arc Codex] G2 review: scoped CPU-tripwire fault acknowledgment

**Updated:** 2026-10-25 (routing state; G2 evidence remains dated)
**Author:** Codex, implementation takeover under Ryan's direct instruction
**For:** G2 review evidence and Ryan's remaining G6 acceptance decision
**State:** `G2_PASS`; G3 merged; G4 promoted; old-event G5 moot; G6 pending
**Branch:** `feat/2026-10-22-doctor-fault-ack-takeover`, pushed to origin
**G3 PR:** [#416](https://github.com/alanmz-crypto/convmem/pull/416), Ryan squash-merged as `4b4796b6a667509f94475a5a14424204947fbb12`
**Checkout:** `/home/lauer/Projects/convmem/.worktrees/doctor-fault-ack-takeover`

The historical KIRO filename is retained so existing links continue to work.
On 2026-10-25, Codex fast-forwarded the clean `.worktrees/runtime-main` to
the merged SHA under Ryan's G4 direction. The watcher stayed at PID 1149 with
`NRestarts=0`; post-promotion doctor exited 0 with zero native faults, and no
acknowledgment was made. The investigated boot has ended, making its G5 moot.
Historical review sections below describe evidence and gates as they stood
before the merge. Ryan alone decides G6 acceptance.
Ryan assigned a fresh Claude Opus-class session to the original Kiro G2
implementation-review slot. This is a separate review from Claude's completed
delta and R4 checks.
Ryan assigned Claude the review role and directed Codex: “You take over,
beginning, now, then.” Codex implemented in an isolated worktree, preserving
the earlier writer's checkout. This grant covers implementation and hermetic
verification. It granted no PR creation, merge, promotion or live
acknowledgment. Ryan subsequently assigned Codex the bounded PR Steward task
for this branch; that grant opened PR #416 and does not grant merge or live use.

## Exact revision first

**Review target:** `1a7676b75bb287d9ca1fc0eb53c7176e06c7b922`.
This immutable content revision corrects two retry/durability defects found
by a first, shell-restricted Opus implementation review: post-replacement
temp-path cleanup could mask exit 3 with "Refused", and an existing-record
retry required a readable journal before syncing the stored file. It includes
new regressions, the aligned §7–§8 contract, and a regenerated R2b inventory.
The preceding `1a825d0` candidate passed Claude's R4 recheck and the
replacement safety review. A fresh shell-capable Opus implementation review
and a separate safety delta recheck both PASSed the current content revision.
Later documentation-only routing commits point to this target; review the
immutable SHA, not a moving tip.

## Final G2 reviews at `1a7676b` — 2026-10-24

Fresh Claude Opus 5.5 session `4ba750ba-982f-454e-909e-ddf376ad7025`
reviewed the exact clean content revision with shell access and returned
**PASS**, with no required findings. Its independent checks included 66 real
CLI pseudo-terminal probes (65 passed; one assertion was a reviewer wording
mistake), reproduction of both prior defects, 365 passing focused tests,
7/7 changed executable lines covered in the corrective delta, current
inventory identity, and a whole-tree comparison with no failure ID introduced
against `origin/main`. The target and main shared 148 environment-related
failure/error IDs; hosted CI and live operations were not run.

The separate read-only safety reviewer rechecked `1a825d0..1a7676b` and
returned **PASS** with no required findings or new advisories. It passed 258
focused and 25 inventory tests, verified the 39-route R2b inventory, and
confirmed both retry/durability fixes preserve the safety contract. Together
with Claude's preceding diff-coverage and R4 reviews, these complete G2 on
the final immutable content SHA. PR #416 was subsequently opened for G3;
Ryan owns merge and G4–G6. No promotion, watcher restart or live
acknowledgment was performed.

## First Opus implementation review at `1a825d0` — 2026-10-24

Claude Opus 5.5 session `fa887e6b-03fc-4398-b340-2dc5b3b18533` returned a
static **PASS** but its restricted CLI permissions denied every shell command,
including its own SHA/clean-tree check, tests, and `/tmp/tangles` notice.
It identified two issues as advisories. Codex reproduced both against the
documented §8 retry contract: three new regression cases failed at `1a825d0`
and passed after correction. A post-replace cleanup error had caused real
Typer ack and revoke commands to exit 1 with "Refused" after the new document
was visible. An idempotent ack retry could not finish durability once its
journal read failed. The corrected content and regenerated R2b inventory are
at the target above. Author checks: 262 focused tests plus 5 subtests, 43
shadow/R2b/scoped-proof tests, 27 documentation tests plus 120 subtests, the
clean-tree manifest guard, Ruff and scoped Pylint passed. The first static
PASS is not final G2 approval; a fresh shell-capable independent recheck is
required on the new exact SHA.

## Claude R4 recheck at `1a825d0` — 2026-10-24

Claude returned **PASS** with no required findings. The one-file inventory
change regenerates byte-identically across 38 routes. Its machine-check test
failed at `ca6aa04` and passed at the target; the R2b identity is unchanged.
Claude passed 391 targeted tests. In a whole-tree comparison against
`origin/main` at `3d24c75`, the target introduced no failing test ID or
traceback line; the only failure-set difference was a known ext4 inode-reuse
flake on main. Both runs shared 142 failures/errors in the no-torch and CG-2
test environment. Hosted CI and the Safe Harbor launcher were not run. This
PASS completes Claude's delta/R4 G2 leg; it does not substitute for the fresh
implementation review.

## Claude final delta review at `49d9d67` — 2026-10-24

Claude returned **PASS-WITH-CHANGES**. Independent probes verified the C1
mode/owner boundary, C2 post-commit reporting, the R2b inventory, and
architecture conformance. It found no production-code defect. **R4** was a
stale derived `SCOPED-PROOF-WRITER-INVENTORY.json`: the shadow inventory's
shifted writer coordinates had not propagated. The committed-file test failed
at `49d9d67` and passed after regeneration. Codex reproduced the failure and
committed only the generated JSON at `1a825d0`; its nine changed lines update
three sites to `1920`, `507`, and `611`. On the clean content commit, the scoped
proof, shadow, R2b and manifest-guard selection passed **44 tests**. The
specific guard is
`tests/test_issue_286_scoped_proof_shadow.py::test_c_sh2_cc1_writer_inventory_machine_checked`.
The replacement safety reviewer independently matched all **38** scoped-proof
routes to the generator, passed its idempotence test and **255 focused tests**,
and returned **PASS** on `1a825d0`. Claude subsequently PASSed the R4 recheck;
the fresh implementation review subsequently PASSed at `1a7676b`.

Claude reported a wider 541-test selection from its previous round had missed
the scoped-proof test. That result is historical, not evidence for R4.

## Replacement safety audit at `e419810` — 2026-10-23

Copilot reached its limit, and Ryan directed Codex to choose another agent.
Codex selected a separate, read-only Codex safety reviewer. Its exact-SHA
verdict was **PASS-WITH-CHANGES**, with two required findings:

1. **C1 — Store authority:** `load_acks` applied a valid record from a file
   changed to mode `0666`; it checked regular-file type but not mode or owner.
   The new target validates `0600` and effective-user ownership on the opened
   inode. On mismatch it invalidates the whole file, so the fault remains FAIL.
2. **C2 — Post-commit result:** a failed verdict refresh after a durable write
   could produce an uncaught exit 1 even though the ack/revoke took effect.
   The new target reports the completed operation, says the current verdict is
   unavailable, and exits 0. CLI tests cover ack and revoke and verify the
   resulting store state.

The reviewer passed **252 focused tests** and reproduced both defects in a
disposable checkout. Codex first observed three new regression cases fail on
`e419810`, then pass after correction. The current content revision passed
**257 focused tests**, **25 affected inventory tests**, 27 documentation tests
with 120 subtests, scoped Ruff, format and Pylint, and the committed-manifest
guard. The R2b inventory was regenerated with its existing writer after the
module edits rotated the implementation identity; the route count stays 39.
Coverage is 100% line and branch for the store, and 100% line for the CLI.
The safety reviewer PASSed `49d9d67` after an independent inventory and
C1–C2 recheck: 25 inventory and 255 focused tests passed in its disposable
checkout, which was clean. Its one-file safety recheck of `1a825d0` also PASSed.
Ryan's fresh-Claude implementation-review slot subsequently PASSed at `1a7676b`.

## Claude exact-SHA delta review at `e419810` — 2026-10-23

Claude returned **PASS** with no new required changes. It verified R1–R3 in
clean separate clones on Python 3.12.13: **252 focused** and **72 inventory**
tests passed; a 36-file regression selection passed **541 tests**. Regenerating
the R2b inventory was
byte-identical to the committed file. Its injected fsync probes confirmed exit
3 and the distinct post-write versus retry messages for ack and revoke. Every
changed line in the delta was covered; 13 of 14 targeted mutants were killed.
The surviving mutant exposed an existing inventory-body digest test gap, not a
new production finding. Claude listed only nonblocking advisories. Its review
did not include hosted CI or the full run-ci launcher. Its PASS applies to
`e419810`, before the safety-audit corrections at the current target.

Claude's nonblocking advisories were: make architecture §8's post-replacement
exit-3 wording self-contained; label the 249-test evidence as historical;
recompute the R2b inventory digest from its committed body in a later test;
note that hosted CI may skip the zsh arm; qualify the retry message if a
post-load file open fails; and cover two pre-existing reader branches. The
historical 249-test section is now labeled by revision. The later safety
correctives are isolated in `fb1d251` and require delta review.

## Claude full review at `132658d` — 2026-10-23

Claude independently verified the post-replacement exit-3 behavior, blind-journal
wording, both of Ryan's policy decisions, and preservation of a CPU fault plus
MCE from timed-out partial stdout. Its earlier C1/C2 reader findings were
resolved. It measured **654/655** changed executable lines against `origin/main`
and directly probed the one unexecuted branch. This evidence applies to
`132658d`; the next delta was reviewed at `e419810` with PASS. The replacement
safety reviewer later PASSed the preceding `49d9d67` content revision.

The verdict was **PASS-WITH-CHANGES**, with three required corrections:

1. **R1:** five shifted `convmem.py` writer coordinates left the shadow
   inventory stale and the R2b derived inventory identity mismatched. Six
   affected tests failed. The shadow coordinates were corrected, then the R2b
   inventory was regenerated with its existing writer; all 25 tests in the
   three affected files now pass, as does the committed-manifest guard.
2. **R2:** architecture §8 and execution T38/T50 said exit 1 for retry sync
   failure while the CLI returned exit 3, and the retry message claimed a
   write that did not occur. The contract now consistently uses exit 3. New
   CLI tests check retry failures for ack and revoke, post-replacement revoke,
   messages, byte preservation and visible effect.
3. **R3:** the bash/zsh test assumed both shells exist, but CI does not install
   zsh. An absent shell now skips with an explicit reason; both arms pass
   locally. Hosted CI has not been run on this branch.

**At the 2026-10-24 G2 handoff:** Ryan still had to decide G3 merge disposition
for the G2-PASSed content revision. The independent implementation and safety
rechecks were complete. Those reviews alone granted no merge, promotion or
live use. The current G3/G4 state is recorded at the top of this packet.

## Earlier independent review at `4d1aedd` — 2026-10-23

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
retry) were resolved. Claude rechecked `e419810` and verified coverage there.
That historical G2 gap is closed by the final Opus review above.

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

**At the 2026-10-24 G2 handoff:** Ryan still had to decide whether to merge
PR #416. Final independent Opus and safety PASSes cover `1a7676b`; Codex's
corrective tests remain separate author evidence. G3/G4 were decided later,
as recorded at the top of this packet.

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

1. Use the completed G2 reviews of
   `1a7676b75bb287d9ca1fc0eb53c7176e06c7b922` for Ryan's G3 decision.
   The local worktree remains at the path above; GitHub holds the task branch
   as the recovery copy if it must be reconstructed.
2. Treat host PIDs, service state and doctor results in the earlier evidence
   as historical snapshots. Reboot is not evidence that hardware is healthy
   or that the deployment's acceptance criterion has passed.
3. Once the boot differs from `7f8e9d592ecc46c7aeb599df6b9457b2`, G5 for
   Timeshift event `bab67b49aa4f` is moot. Do not replay its live acknowledgment
   command against the new boot. The implementation review can still continue;
   Ryan decides whether to merge/deploy it for future events.
4. Preserve the completed exact-revision G2 evidence and all remaining Ryan gates.
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
2. [Execution plan](../plans/EXECUTION-doctor-fault-acknowledgment.md), including T0–T53, mutation checks and verification evidence.
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
plan. The preceding `1a825d0` code passed 257 focused and 44 scoped-proof,
shadow, R2b and manifest tests. The current target passed 262 focused tests
plus 5 subtests, 43 scoped-proof/shadow/R2b tests, and the clean-tree manifest
guard. Scoped Ruff, Pylint and `git diff --check` passed on the new code.
Its CLI tests inject post-replacement and retry sync failures for both verbs,
check exit 3 and distinct written-versus-visible messages, then confirm the
acknowledgment or revocation is effective. The preserved reader-fix branch
was compared read-only; its only useful unique coverage was the 9-case matrix
for Unicode separators through complete and timed-out journal reads, now on
this target. A timed-out journal with partial stdout containing both a CPU
fault and an MCE remains FAIL. Actual bash and zsh parse the printed command
without changing the cursor or `<reason>`.
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
Claude coverage verification/review, Ryan's selected independent safety-audit
replacement after Copilot's limit, and the implementation-review slot that
Ryan assigned to a fresh Claude Opus-class session, with Codex supplying
author evidence. Ryan separately owns G3 PR/merge, G4 exact-SHA
promotion without restart, G5 his one-event live acknowledgment, and G6
acceptance. If the investigated boot has ended, G5 for that event is moot.

**TL;DR:** [Arc Codex] Independent G2 reviews PASSed content `1a7676b`;
Ryan merged PR #416 as `4b4796b`, and Codex promoted that exact SHA without
restarting the watcher. The old-event G5 is moot; Ryan decides G6 acceptance.

<!-- ref: ../plans/ARCHITECTURE-doctor-fault-acknowledgment.md, ../plans/EXECUTION-doctor-fault-acknowledgment.md, ../plans/STATUS-codex-jsonl-production-integration.md, ./LATEST.md — binding design, evidence and reviewer routing -->
<!-- src: ./CODEX-2026-10-22-doctor-ack-next-model-handoff.md, ../../cpu_tripwire.py, ../../tests/test_cpu_tripwire_ack.py — event evidence and implemented contract -->
<!-- src: /home/lauer/.claude/projects/-tmp-convmem-doctor-ack-claude-review-4d1aedd/302044cc-73e9-41a1-b026-3097d18e92aa.jsonl, /home/lauer/.codex/sessions/2026/10/22/rollout-2026-10-22T23-40-11-01a1670f-3005-75e0-8be1-f37f0c9d9955.jsonl — independent review, explicit grants and lane comparison -->
