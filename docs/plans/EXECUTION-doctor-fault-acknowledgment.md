# Execution Plan — Scoped CPU-Tripwire Fault Acknowledgment

**Arc:** Codex (priority #1)
**Date:** 2026-10-22
**Author:** Claude (Opus 5.5), design lane
**Architecture:** [`ARCHITECTURE-doctor-fault-acknowledgment.md`](ARCHITECTURE-doctor-fault-acknowledgment.md) (the binding spec; section numbers below such as §5.2 refer to it)
**Resume state:** `IMPLEMENTED_PENDING_REVIEW` on
`feat/2026-10-22-cpu-tripwire-fault-ack`. Ryan assigned Codex implementation
and Claude independent review on 2026-10-22. G3–G6 remain separate.

```
Planning Status

Phase:        Codex implementation and hermetic verification; Claude review next
Lanes:        Codex -> Claude -> Ryan
Authority:    Ryan's explicit implementation handoff on 2026-10-22 supersedes
              the earlier wait-for-Execute routing. No live authority is granted.
```

---

## G. Gates (in order, each Ryan- or reviewer-owned)

| # | Gate | Owner | What it permits | What it does NOT permit |
|---|---|---|---|---|
| G0 | Earlier review FAIL; cursor finding corrected, remaining rules amended here | Codex reviewer | Historical review evidence | Self-issued PASS or live authority |
| G1 | Explicit takeover grant, 2026-10-22 | Ryan | Codex implements E1–E5 and the review corrections hermetically | Promotion, live use, a PR without a request, merge |
| G2 | Exact-tip tests and independent review | Codex tests; Claude review, per Ryan | A PR decision after review | Promotion or acceptance |
| G3 | PR and merge | Ryan | The code lands on `main` | Runtime promotion |
| G4 | Runtime promotion grant at an exact SHA | Ryan | A fast-forward of `.worktrees/runtime-main`, **with no watcher restart** | Live acknowledgment |
| G5 | One-event live acknowledgment | Ryan runs it himself | One `convmem tripwire ack` for key `bab67b49aa4f` | Any other event; any acceptance claim |
| G6 | Acceptance decision | Ryan | Deciding whether the deployment's doctor criterion is satisfied | n/a |

If Ryan reboots before G5, G5 is moot (architecture §10.1, step 6). E1–E5
remain valid for future events if Ryan still wants the mechanism.

## E. Implementation steps (Codex, under Ryan's takeover grant)

Branch: `feat/YYYY-MM-DD-cpu-tripwire-fault-ack` from current `origin/main`,
created with `convmem work start feat cpu-tripwire-fault-ack --worktree`.
Push every commit with an explicit refspec. Do not open a PR unless Ryan asks.

**E1. Identity-bearing journal read** in `cpu_tripwire_events.py`,
collected by `cpu_tripwire.py`:

- Add optional fields to `Fault`, all defaulting to `None` so positional
  construction in the existing tests keeps working: `boot_id`, `realtime_us`,
  `source_monotonic_us`, `message_sha256`, `message`, `cursor`.
- Factor the message classification in `parse_kernel_faults` into one helper.
  `parse_kernel_faults(lines)` (short-iso) keeps its exact behavior for the
  existing tests.
- `parse_kernel_journal(lines) -> JournalRead` retains faults, all observed
  boot IDs, and decoding problems. Malformed/null/repeated messages disable
  acknowledgments without discarding any decodable FAIL evidence (§5.1).
- `Fault` and `parse_kernel_faults` remain importable from `cpu_tripwire`.
  No cycle is introduced between classification, storage and collection.
- `read_kernel_faults()` switches to the JSON argv in §5.1.
- Add `read_boot_id(path=Path("/proc/sys/kernel/random/boot_id")) -> str | None`.
  It strips dashes, lowercases, and requires 32 hex characters.

**E2. Acknowledgment store**, a new module `cpu_tripwire_ack.py` with no
imports from `doctor`, `convmem`, or any ingest or watcher module:

- `ACK_SCHEMA`, `ACK_VERSION = 1`, `DEFAULT_ACK_PATH`. The default path is
  resolved at call time from `Path.home()`.
- `EventKey.ack_id` in the event module hashes all five identity fields.
- `load_acks(path) -> AckSet`. An `AckSet` holds the records and a
  `problem: str | None` (`invalid: …` or `unreadable: …`). It never raises
  for file content. It enforces all seven checks in §6, rejecting the whole
  file on any failure.
- `write_ack(...)` and `revoke_ack(...)`: flock, temp file, fsync, replace,
  fsync of the directory (§8). They accept injected `path`, `now`, confirmation,
  TTY check and a fresh evidence callback. A revoked same-key acknowledgment
  is refused without writing. Post-replacement durability errors are reported
  distinctly from pre-replacement failures.
- `ackable(fault, known_bad)` in the event module requires complete identity
  and the rule in §7, step 3.

**E3. Policy integration** in `cpu_tripwire.evaluate()` and `check()`:

- Implement architecture §9.1 exactly.
- Add the parameters `acks: AckSet | None = None` and
  `current_boot_id: str | None = None`, plus an `ack_problem` inhibition reason.
- `check()` gains the keyword parameters `ack_path` and `boot_id_path`, with
  production defaults. It loads acknowledgments only when the file exists.
- The detail text follows §9.2.
- `doctor._check_cpu_tripwire` does not change. If a test needs to inject
  paths, monkeypatching `cpu_tripwire.check` is enough.

**E4. CLI**: a Typer sub-app `tripwire` in `convmem.py` with `show`, `ack` and
`revoke` (§7):

- Handlers delegate to `cpu_tripwire_cli.py`, with ≤ 15 lines of logic each.
- Register `tripwire` in `_SUBCOMMANDS` so the CLI does not treat it as search.
- `show` prints a shell-quoted `ack` command, including the opaque cursor.
  Existing revoked records are shown, but no command offers to reactivate them.
- `ack` enforces the TTY check, requires exactly one matching entry, refuses
  anything that cannot be acknowledged, and requires the operator to type the
  ID.
- Exit codes: 0 when written or already present; 1 when refused or the lock is
  busy; 2 for bad usage or no TTY.
- Add the three commands to the usage block at the top of `convmem.py`.

**E5. Repository hygiene**:

- Classify `cpu_tripwire_ack.py`, `cpu_tripwire_events.py`, `cpu_tripwire_cli.py`
  and any new test files in
  `config/repository-knowledge/openclaw-watch-scope-v1.json`. Use
  `unrelated`, matching `cpu_tripwire.py`.
- **Refresh the `include` sha256 for `convmem.py`.** It is an `include`
  entry, so editing it makes the committed-manifest guard fail until the hash
  is current.
- Pass `git diff --check`, ruff, and the repo's pylint gate.
- The diff must not touch the files listed under "Out of scope" in
  architecture §4. Check with `git diff --stat origin/main...HEAD`.

## T. Hermetic test specification

Put the tests in `tests/test_cpu_tripwire.py` (extended) and a new
`tests/test_cpu_tripwire_ack.py`. Every test must use:

- the existing `_FakeRunner` pattern, extended to serve JSON lines,
- `tmp_path` for the acknowledgment file, `boot_id`, `online` and `stat`, and
- a pinned timezone (`monkeypatch.setenv("TZ", "America/Chicago")` and
  `time.tzset()`, restored afterwards).

**Hermeticity guard (T0):** an autouse fixture in the new file sets `HOME` to
`tmp_path`, and a fail-fast runner raises if any argv runs a real
`journalctl` or `coredumpctl`. No test reads host logs, `~/.config`, `/proc`
or `/sys`.

Fixture constants, copied from architecture §2:

- `TS_MSG`: the Timeshift message.
- `TS_BOOT`: `7f8e9d592ecc46c7aeb599df6b9457b2`.
- `TS_RT`: `1792692082959438`.
- `TS_MONO`: `216789351540`.
- `TS_SHA`: `5bcabab4…b518d`, computed in the test rather than pasted.
- `OTHER_BOOT`: any other 32-hex value.

Group 1: no regression.

| ID | Case | Expected |
|---|---|---|
| T1 | Every existing message fixture (`SEGV_CPU8`, `SEGV_CPU4`, `GP_NO_CPU`, `INVALID_OPCODE`, `MCE`, `TYPORA_GPF`, `NOISE`), sent through the JSON path, with no acknowledgment file | The same `Fault` classification fields and the same `evaluate()` status **and detail**, byte-for-byte, as the short-iso path |
| T2 | The Timeshift JSON entry | `Fault(kind="segfault", cpu=13, process="timeshift", pid=835726, when="2026-10-22T13:01:22-05:00")` with exact identity fields. The verdict is FAIL with today's detail. |
| T3 | No acknowledgment file | No acknowledgment note anywhere in the detail; `check()` never opens the default path (asserted with a guard) |

Group 2: the intended acknowledgment.

| ID | Case | Expected |
|---|---|---|
| T4 | The Timeshift entry with a valid acknowledgment for the same boot | Status `warn` (never `pass`). The detail contains `acknowledged`, `bab67b49aa4f`, the `by` value, and `hardware health unproven`. `doctor_exit_code` is 0 when this is the only finding. |
| T5 | T4 plus the acknowledged event's coredump (PID 835726, signal 11) | No orphan-dump note (architecture §5.3) |

Group 3: recurrence, and faults that must still FAIL.

| ID | Case | Expected |
|---|---|---|
| T6 | T4 plus a second Timeshift segfault on CPU 13: new PID, later times | `fail`. The detail names the new fault and adds `plus 1 acknowledged fault (ack bab67b49aa4f)`. |
| T7 | A recurrence that reuses PID 835726 and the identical message text, with different `realtime_us` and `source_monotonic_us` | `fail` |
| T8 | The same timestamps with a one-byte change to the message (the `ip`) | `fail` |
| T9 | The acknowledged entry **and** an exact duplicate entry with the same key in one read | `fail` with an ambiguity note |
| T45 | The acknowledged entry is gone (vacuumed) and a different entry with the same boot, `realtime_us`, `source_monotonic_us` and message remains, with a different `cursor` | `fail`; the survivor is not acknowledged and `show` reports `inert (entry not present)` (G0 finding 3) |
| T46 | The acknowledged entry unchanged, same cursor, in a read where the original is the only match | `warn` (control for T45) |
| T47 | An entry with no `__CURSOR` field that otherwise matches a record | `fail`; it can never be acknowledged |
| T10 | T4 plus a machine-check line | `fail` with the machine-check text |
| T11 | T4 plus a known-bad CPU online (`online = 0-23`, known-bad `[4, 5, 8, 9]`) | `fail` with `ONLINE again` |
| T12 | T4 plus a segfault pinned to CPU 14 (healthy, unrelated) | `fail` |
| T13 | T4 plus the Typora GPF (no CPU) | `warn`, and the detail carries both the acknowledged note and the userspace advisory |

Group 4: boots.

| ID | Case | Expected |
|---|---|---|
| T14 | An acknowledgment for `TS_BOOT`, current boot `OTHER_BOOT`, and an entry with the same message and timestamps but `_BOOT_ID = OTHER_BOOT` | `fail`. The acknowledgment is reported as inert (previous boot). |
| T15 | "After reboot": current boot `OTHER_BOOT`, no faults, the old acknowledgment still stored | `pass` with an inert note. The status is never `warn` or `fail` because of a stale record. |
| T16 | A journal entry's `_BOOT_ID` differs from `/proc` boot ID; or the boot-ID file is missing or malformed | No acknowledgment applied. FAIL stays FAIL; PASS becomes WARN with `boot identity mismatch`. |
| T17 | A current-boot acknowledgment whose entry is absent (vacuumed) | `pass` with `inert (entry not present)` |

Group 5: malformed, stale or interrupted state. Each case applies no
acknowledgment: FAIL stays FAIL, PASS becomes WARN, and the detail says why.

| ID | Case |
|---|---|
| T18 | Empty file; truncated JSON; a file that is not an object; a file > 1 MiB |
| T19 | Wrong `schema`; `version: 2`; `version: "1"` |
| T20 | Unknown top-level key; unknown record key; missing record key |
| T21 | Wrong types: a string `realtime_us`, a negative integer, `cpu: null` |
| T22 | A non-lowercase-hex `message_sha256`; a `boot_id` with dashes or in uppercase |
| T23 | `ack_id` does not equal the key hash |
| T24 | `evidence.message` does not hash to `message_sha256` |
| T25 | The stored `kind`, `cpu`, `process` or `pid` disagrees with the classifier's reading of `evidence.message` (for example, a record edited to say `cpu: 14`) |
| T26 | A record for a `machine_check` or `kernel_oops` kind, or with `pid: null` |
| T27 | A duplicate `ack_id`; two non-revoked records with the same key |
| T28 | Partial revocation fields (only `revoked_at` set) |
| T29 | The path is a directory; a file with mode `000` (skip when running as root) |
| T30 | A stray `cpu-tripwire-acknowledgments.json.tmp…` next to a valid file is ignored; one next to a missing file has no effect |

Group 6: revocation.

| ID | Case | Expected |
|---|---|---|
| T31 | Revoke an applied acknowledgment | The record is kept with revocation fields set. The next `check()` gives `fail` with an inert note. |
| T32 | Revoke when the file is invalid | Refuse, exit 1, and the file is byte-identical afterwards |

Group 7: the writer (`ack`, run in-process through Typer's `CliRunner` or the
module function, with an injected runner, path and TTY check).

| ID | Case | Expected |
|---|---|---|
| T33 | Not a TTY | Exit 2, and no file is created |
| T34 | Key matches 0 entries; key matches 2 entries | Exit 1, no file |
| T35 | Key names an MCE, a fault pinned to a known-bad CPU, a fault with no CPU, or a `kernel_oops` | Exit 1, no file |
| T36 | Wrong typed short ID | Exit 1, no file |
| T37 | Success | Exit 0. The file has mode `0600`, passes `load_acks` with no problem, and `check()` then gives the T4 verdict. The coredump evidence is filled in when the fake coredump list has a match, and null otherwise. |
| T38 | Run again for the same key | Exit 0, "already acknowledged", and the file is byte-identical |
| T39 | Lock held by another file descriptor | Exit 1, and the file is unchanged |
| T40 | Failure at file fsync or replacement | Original file byte-identical (or absent); own temp removed. A failure at directory fsync after replacement instead leaves a complete new document and reports uncertain durability. |

Group 8: integration, decoding and the CLI.

| ID | Case | Expected |
|---|---|---|
| T41 | `doctor._check_cpu_tripwire` with `check` patched to return the T4 verdict | `ok=True`, `status="warn"`; `doctor_exit_code([that check])` is 0 |
| T42 | A `MESSAGE` given as a byte array with invalid UTF-8 | Classified from the replacement-decoded text; `message_sha256` taken over the raw bytes |
| T43 | Malformed/non-object/null/invalid MESSAGE among valid entries | No acknowledgment applies; detected CPU faults/MCEs and online known-bad CPUs remain FAIL. With no detected FAIL, report blind WARN. |
| T44 | `show --json` against the T4, T14 and T31 states | The states `applied`, `inert (previous boot)` and `revoked`, each with full keys. The shell-quoted `ack` line appears only for an eligible, unambiguous fault with no stored same-key record. |

**Mutation sanity (verification lane, G2):** each of these mutations must make
at least one test fail:

1. Removing `boot_id` from the key.
2. Matching on `process` instead of the key.
3. Letting acknowledged faults yield PASS.
4. Discarding detected FAILs on a bad JSON line, or applying acknowledgments during an incomplete read.
5. Rejecting only the bad record instead of the whole file.
6. Omitting the cursor from identity/hash comparison (T2, T45–T47).

Additional correction tests:

- **T48:** `ack → revoke → ack` on the same key refuses, preserves bytes and
  revocation attribution; a different cursor can be acknowledged separately.
- **T49:** `--all` is requested, large valid messages still classify, and
  repeated MESSAGE values retain every decodable fault without gaining identity.
- **T50:** failed journal commands (including partial nonzero output) cannot
  erase a detected fault or the independent known-bad-CPU-online alarm.
- **T51:** post-replacement directory fsync failure leaves a complete validated
  new document, reports uncertain durability and does not claim rollback.
- **T52:** CLI quoting, typed confirmation, idempotence, no-TTY refusal, revoked
  command omission and JSON states use only injected host evidence.
- **T53:** booleans, duplicate JSON fields, symlinks, malformed attribution and
  out-of-range timestamps are rejected or made unacknowledgeable safely.
- **T54:** invalid UTF-8 message evidence survives a write/load round trip with
  the same raw-byte hash.
- **T55:** one invalid record disables the otherwise valid records too.

## A. Acceptance criteria (for G2)

- [x] T0–T55 pass. Existing policy assertions remain intact; the old fake
      runner now supplies JSON for the JSON argv and isolates acknowledgment HOME.
- [x] Every changed executable source line is covered by a test (diff coverage), including the
      error branches in `load_acks`, `write_ack` and the boot cross-check.
- [x] With no acknowledgment file, doctor's `cpu_tripwire` detail is
      byte-identical to `main` for every T1 fixture.
- [x] The runtime diff touches only `cpu_tripwire.py`, `cpu_tripwire_events.py`,
      `cpu_tripwire_ack.py`, `cpu_tripwire_cli.py`, `convmem.py`, tests and the manifest.
      Existing architecture, execution, STATUS and routing docs reflect the change. It touches none of the
      §4 out-of-scope files.
- [x] ruff, the pylint gate and `git diff --check` pass.
- [x] The committed-manifest pytest passes on a clean committed tree.
- [x] Test acknowledgment/configuration writes stay under `tmp_path`, and no real `journalctl` or
      `coredumpctl` runs (T0).
- [ ] Claude independently reviews the exact pushed implementation tip.

### Implementation verification (Codex, 2026-10-23)

Local checks use Python 3.13.12, pytest 9.1.1 and pylint 4.0.6. CI uses
Python 3.12; that environment and Claude's independent review remain pending.

- **204 passed:** `python -m pytest tests/test_cpu_tripwire.py
  tests/test_cpu_tripwire_ack.py tests/test_doctor.py
  tests/test_expand_cli_registration.py -q`.
- **43 passed:** `python -m pytest tests/test_shadow_writer_gate_c3.py
  tests/test_write_gate_effect.py tests/test_watch_subprocess_memcap.py
  tests/test_openclaw_watch_coverage.py -q`.
- **1 passed:** `python -m pytest
  tests/test_repository_knowledge_committed_manifest.py -q`, on the clean
  implementation commit `aad01a6`. The implementation is pushed; the remaining
  changes in this handoff only record verification and routing.
- Coverage 7.17.0, installed only under `/tmp`, reports **100% statements and
  branches** across the four tripwire modules: 655 executable lines and 150
  branches. All 18 added executable lines in `convmem.py` are covered too.
- All six mutation controls above fail tests in disposable module copies:
  respectively 1, 2, 6, 2, 28 and 5 failing cases. The reviewed tree is unchanged
  by those mutations.
- Ruff passes for the four tripwire modules and their two test files.
  The pylint regression gate passes against `origin/main` at `3d24c75`:
  443 findings, 223 fingerprints, no new or increased findings. This uses a
  scan of all 658 tracked Python files, refreshed with a final `convmem.py`
  scan after removing redundant imports whose embedded line numbers shifted.
  Neither the baseline nor lint configuration changed.
- The staged-addition secret scan and the complete branch diff secret scan pass.
- No live acknowledgment/configuration file was written, no watcher was
  restarted, and no runtime checkout was promoted. The complete repository
  pytest suite was not run locally.

Claude should review the cursor-change failure direction, partial journal
decoding, retained revocation semantics and atomic-write failure boundaries
against the implementation, rather than treating coverage as design approval.

## P. Live-use runbook (G4–G6; listed for review, not authorized)

G4 promotion, run by the lane Ryan names, with his exact SHA:

1. `git -C ~/Projects/convmem/.worktrees/runtime-main status --short` is
   empty.
2. `git diff --stat 1a68675 <SHA>` lists only expected files. The four
   checkpoint-safety files are unchanged:
   `distill.py`, `llm.py`, `incremental_transform_contract.py`,
   `incremental_checkpoint_migration.py`.
3. `git -C <runtime-main> grep -n "cpu_tripwire" -- '*.py' ':!tests/'`
   lists only `cpu_tripwire.py`, `cpu_tripwire_events.py`, `cpu_tripwire_ack.py`,
   `cpu_tripwire_cli.py`, `convmem.py` (CLI), and the lazy import inside
   `doctor._check_cpu_tripwire`. Evidence at
   `5c0a01b`: `watch.py` reaches `doctor` only through the opt-in
   `live_diagnosis` path, and the MCP `brief` imports only
   `doctor.standing_register_status`. Neither calls the tripwire, and
   `doctor.py` does not change. The watcher therefore needs no restart.
4. Fast-forward with `git merge --ff-only <SHA>`. **Do not restart the
   watcher.**
5. Check that the service PID and `NRestarts` are unchanged.

G5, Ryan in his own terminal:

1. `cat /proc/sys/kernel/random/boot_id` shows
   `7f8e9d59-2ecc-46c7-aeb5-99df6b9457b2`. If not, stop: G5 is moot.
2. `convmem tripwire show`. Confirm that:
   - exactly one fault is listed,
   - its key matches architecture §2, and
   - no other FAIL contributor exists.
   If any of these is wrong, stop.
3. Paste the printed `ack` command with `--by ryan`, a reason, and
   `--authority-ref` pointing at the G5 grant. Type the ID `bab67b49aa4f`.
4. Run `convmem doctor` and record the result.

Any lane may then verify, read-only: architecture §10.2.

If the result is wrong, roll back as in architecture §10.3: revoke the record,
move the file aside, or promote back. G6 remains Ryan's alone.

<!-- ref: ./ARCHITECTURE-doctor-fault-acknowledgment.md, ./STATUS-codex-jsonl-production-integration.md — binding spec and arc brief -->
<!-- src: ../../tests/test_cpu_tripwire.py, ../../tests/test_cpu_tripwire_ack.py, ../../config/repository-knowledge/openclaw-watch-scope-v1.json — executable contracts and manifest classification -->
