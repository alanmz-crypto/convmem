# [Arc Codex] Kiro design review: scoped CPU-tripwire fault acknowledgment

**Date:** 2026-10-22
**Author:** Claude (Opus 5.5), fresh design model for priority #1
**For:** Kiro, design review (non-implementing; review documents only)
**Authorization:** Ryan dispatched a fresh design model for priority #1 on
2026-10-22. The scope was design only: implementation and live use were not
authorized.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `BLOCKED_ON_RYAN` for dispatching the review; the design is `READY_FOR_REVIEW` |
| **Review target** | `origin/main` at `3d24c753a4b46132d349c34a2cd37b0fbba464c2` (squash merge of #415) |
| **PR** | [#415](https://github.com/alanmz-crypto/convmem/pull/415), merged by Ryan on 2026-10-22 CDT |
| **Ryan GATE** | Send this packet to Kiro. After a PASS, Ryan decides on a separate Execute grant (G1). |
| **Track A** | The Claude transcript for this session, under `~/.claude/projects/-home-lauer-Projects-convmem/` |

## What to review

Read these three documents in full. The architecture is the binding spec:

1. [`docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md`](../plans/ARCHITECTURE-doctor-fault-acknowledgment.md)
2. [`docs/plans/EXECUTION-doctor-fault-acknowledgment.md`](../plans/EXECUTION-doctor-fault-acknowledgment.md)
3. The input handoff, for evidence and constraints:
   [`CODEX-2026-10-22-doctor-ack-next-model-handoff.md`](CODEX-2026-10-22-doctor-ack-next-model-handoff.md)

The current code is [`cpu_tripwire.py`](../../cpu_tripwire.py) (268 lines),
[`doctor.py`](../../doctor.py) `_check_cpu_tripwire` (line 900), and
[`tests/test_cpu_tripwire.py`](../../tests/test_cpu_tripwire.py).

**Product outcome under review:** Ryan can acknowledge only the investigated
`timeshift[835726]` segfault on CPU 13 at `2026-10-22T13:01:22-05:00`, in
boot `7f8e9d592ecc46c7aeb599df6b9457b2`, without rebooting. Doctor then shows
it as a visible WARN. Every new fault that would FAIL today still FAILs.

## Design summary (to orient you; the architecture governs)

- **Key** (architecture §5.2): four fields from one journal entry: `_BOOT_ID`,
  `__REALTIME_TIMESTAMP`, `_SOURCE_MONOTONIC_TIMESTAMP`, and the SHA-256 of
  `MESSAGE`. The process name, PID, CPU, cursor and coredump are evidence
  only, never part of the key.
- **Read** (§5.1): one `journalctl -k -b 0 -o json` read in place of
  `short-iso`. The message classifier is unchanged, and output must be
  byte-identical when no file exists. A malformed line puts the tripwire into
  its existing blind WARN.
- **Store** (§6, §8): `~/.config/convmem/cpu-tripwire-acknowledgments.json`,
  in the live-configuration directory, mode `0600`. Strict schema version 1;
  the whole file is rejected if any part is invalid. Writes are atomic
  (flock, temp file, fsync, replace, fsync of the directory). Revocation is a
  field on the record, so the record is kept.
- **Authority** (§7): `convmem tripwire show` is read-only. `ack` needs a
  TTY, requires exactly one matching entry and an acknowledgeable FAIL
  contributor, and makes the operator type the short ID. `revoke` does not
  need a TTY, because it can only bring back the FAIL. The design says plainly
  that the TTY check slows an agent down and is not authorization.
- **Verdict** (§9): an acknowledged fault turns into WARN, never PASS. Machine
  checks and known-bad CPUs coming back online never consult acknowledgments.
  Inert records (from a previous boot, whose entry is gone, or revoked) never
  change the status. A broken file or boot mismatch never widens anything and
  turns PASS into WARN.
- **Gates** (execution plan §G): G0 Kiro → G1 Execute → G2 verify, audit and
  review → G3 merge → G4 promotion without a watcher restart → G5 Ryan's live
  acknowledgment of one event → G6 Ryan's acceptance decision.

## Review questions (answer each)

1. **Identity sufficiency:** Does the four-part key identify exactly one
   kernel entry and nothing else? Are leaving out the cursor and the coredump
   from the key (§5.2, §5.3) sound choices?
2. **Boundary completeness:** Can any input or state make an acknowledgment
   apply to a fault other than the one acknowledged? Look at duplicate
   entries, other boots, reused PIDs, an edited file, and a boot-ID mismatch.
   Can any input or state stop a machine check or a known-bad CPU being online
   from FAILing?
3. **Fail-closed behavior:** Does every row of the §9.3 table avoid widening
   an acknowledgment? Is rejecting the whole file (instead of one record) the
   right strictness?
4. **No-regression claim:** With no file present, is the byte-identical detail
   requirement (T1, T3) both achievable and enough? Look at the `when`
   rendering and the integer truncation.
5. **Authority honesty:** Is the authority statement in §7 accurate and
   enough, given the team charter? Should revoke require a TTY?
6. **Test adequacy:** Do T0–T44 and the mutation-sanity list cover recurrence,
   other boots, unrelated faults, and malformed, stale or interrupted state?
   Is anything missing?
7. **Scope and gates:** Is the out-of-scope list (§4) enough to keep the
   implementation away from ingest, watcher and transform code? Do the gates
   in §G keep implementation, promotion, live use and acceptance separate?

## What NOT to do

- Do not write code, tests, scripts, configuration, or generated files (Kiro
  is non-implementing).
- Do not run `convmem tripwire …`; the commands do not exist yet. Do not edit
  `~/.config/convmem/`, and do not restart or promote anything.
- Do not treat a PASS as an Execute grant, a promotion grant, a live-use
  grant, or deployment acceptance.
- Do not pull in later queue items: #286 evidence reconciliation, Crush #393,
  retrieval #320/#263.

## Verdict format

Use `PASS`, `PASS-WITH-CHANGES`, or `FAIL`, and quote the exact reviewed
commit. Number each required change C1, C2, … and give the architecture
section it touches. List advisories separately from required changes. Do not
defer or abstain. If you cannot decide a question, say what evidence would
decide it.

## After the verdict

- **PASS or PASS-WITH-CHANGES:** the design lane makes the changes on this
  branch, and Kiro confirms the delta. Ryan then decides G1.
- **FAIL:** the design lane revises the design. No implementation starts.

---

**TL;DR:** [Arc Codex] Please review a design that lets Ryan acknowledge
exactly one kernel journal entry (the 13:01:22 Timeshift crash) so it shows as
a visible WARN. Every new fault, machine check, or known-bad CPU back online
still FAILs, and nothing about the acknowledgment can widen it. Design only:
no grant follows from it.

<!-- ref: ../plans/ARCHITECTURE-doctor-fault-acknowledgment.md, ../plans/EXECUTION-doctor-fault-acknowledgment.md, ../plans/STATUS-codex-jsonl-production-integration.md, ./LATEST.md — review targets and routing -->
<!-- src: ./CODEX-2026-10-22-doctor-ack-next-model-handoff.md — event evidence and constraints -->
