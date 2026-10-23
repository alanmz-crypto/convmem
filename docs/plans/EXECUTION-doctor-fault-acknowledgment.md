# Execution Plan — Scoped CPU-Tripwire Fault Acknowledgment

**Arc:** Codex (priority #1)
**Date:** 2026-10-22
**Author:** Claude (Opus 5.5), design lane
**Architecture:** [`ARCHITECTURE-doctor-fault-acknowledgment.md`](ARCHITECTURE-doctor-fault-acknowledgment.md) (the binding spec; section numbers below such as §5.2 refer to it)
**Resume state:** `NOT_STARTED`. Waiting for Kiro's design review. No Execute grant exists.

```
Planning Status

Phase:        Execution plan drafted; awaiting Kiro design review
Lanes:        Kiro review -> Ryan Execute grant -> Cursor (hermetic implementation)
Authority:    None granted. Every gate in §G is separate; none implies another.
```

---

## G. Gates (in order, each Ryan- or reviewer-owned)

| # | Gate | Owner | What it permits | What it does NOT permit |
|---|---|---|---|---|
| G0 | Design review of this packet at an exact commit | Kiro | Moving to an Execute decision | Any code |
| G1 | Execute grant | Ryan | Cursor implements E1–E5 hermetically on a feature branch | Promotion, live use, a PR without a request, merge |
| G2 | Exact-tip verification | Claude (diff coverage) + Copilot audit lane (targeted safety audit) + Kiro (implementation review) | A PR decision | Promotion |
| G3 | PR and merge | Ryan | The code lands on `main` | Runtime promotion |
| G4 | Runtime promotion grant at an exact SHA | Ryan | A fast-forward of `.worktrees/runtime-main`, **with no watcher restart** | Live acknowledgment |
| G5 | One-event live acknowledgment | Ryan runs it himself | One `convmem tripwire ack` for key `4c6debf6cee1` | Any other event; any acceptance claim |
| G6 | Acceptance decision | Ryan | Deciding whether the deployment's doctor criterion is satisfied | n/a |

If Ryan reboots before G5, G5 is moot (architecture §10.1, step 6). E1–E5
remain valid for future events if Ryan still wants the mechanism.

## E. Implementation steps (Cursor, after G1 only)

Branch: `feat/YYYY-MM-DD-cpu-tripwire-fault-ack` from current `origin/main`,
created with `convmem work start feat cpu-tripwire-fault-ack --worktree`.
Push every commit with an explicit refspec. Do not open a PR unless Ryan asks.

**E1. Identity-bearing journal read** in `cpu_tripwire.py`:

- Add optional fields to `Fault`, all defaulting to `None` so positional
  construction in the existing tests keeps working: `boot_id`, `realtime_us`,
  `source_monotonic_us`, `message_sha256`, `message`, `cursor`.
- Factor the message classification in `parse_kernel_faults` into one helper.
  `parse_kernel_faults(lines)` (short-iso) keeps its exact behavior for the
  existing tests.
- Add `parse_kernel_journal(lines) -> list[Fault] | None`. It parses
  `-o json` lines through the same helper and returns `None` if any line is
  malformed (architecture §5.1).
- `read_kernel_faults()` switches to the JSON argv in §5.1.
- Add `read_boot_id(path=Path("/proc/sys/kernel/random/boot_id")) -> str | None`.
  It strips dashes, lowercases, and requires 32 hex characters.

**E2. Acknowledgment store**, a new module `cpu_tripwire_ack.py` with no
imports from `doctor`, `convmem`, or any ingest or watcher module:

- `ACK_SCHEMA`, `ACK_VERSION = 1`, `DEFAULT_ACK_PATH`. The default path is
  resolved at call time from `Path.home()`.
- `ack_id(boot_id, realtime_us, source_monotonic_us, message_sha256) -> str`.
- `load_acks(path) -> AckSet`. An `AckSet` holds the records and a
  `problem: str | None` (`invalid: …` or `unreadable: …`). It never raises
  for file content. It enforces all seven checks in §6, rejecting the whole
  file on any failure.
- `write_ack(...)` and `revoke_ack(...)`: flock, temp file, fsync, replace,
  fsync of the directory (§8). They take `path`, `now`, `runner` and
  `tty_check` parameters so they can be tested.
- `ackable(fault, known_bad) -> bool`: the rule in §7, step 3.

**E3. Policy integration** in `cpu_tripwire.evaluate()` and `check()`:

- Implement architecture §9.1 exactly.
- Add the parameters `acks: AckSet | None = None` and
  `current_boot_id: str | None = None`.
- `check()` gains the keyword parameters `ack_path` and `boot_id_path`, with
  production defaults. It loads acknowledgments only when the file exists.
- The detail text follows §9.2.
- `doctor._check_cpu_tripwire` does not change. If a test needs to inject
  paths, monkeypatching `cpu_tripwire.check` is enough.

**E4. CLI**: a Typer sub-app `tripwire` in `convmem.py` with `show`, `ack` and
`revoke` (§7):

- Handlers only delegate, with ≤ 15 lines of logic each.
- `show` prints the copyable `ack` command.
- `ack` enforces the TTY check, requires exactly one matching entry, refuses
  anything that cannot be acknowledged, and requires the operator to type the
  ID.
- Exit codes: 0 when written or already present; 1 when refused or the lock is
  busy; 2 for bad usage or no TTY.
- Add the three commands to the usage block at the top of `convmem.py`.

**E5. Repository hygiene**:

- Classify `cpu_tripwire_ack.py` and any new test files in
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
| T4 | The Timeshift entry with a valid acknowledgment for the same boot | Status `warn` (never `pass`). The detail contains `acknowledged`, `4c6debf6cee1`, the `by` value, and `hardware health unproven`. `doctor_exit_code` is 0 when this is the only finding. |
| T5 | T4 plus the acknowledged event's coredump (PID 835726, signal 11) | No orphan-dump note (architecture §5.3) |

Group 3: recurrence, and faults that must still FAIL.

| ID | Case | Expected |
|---|---|---|
| T6 | T4 plus a second Timeshift segfault on CPU 13: new PID, later times | `fail`. The detail names the new fault and adds `plus 1 acknowledged fault (ack 4c6debf6cee1)`. |
| T7 | A recurrence that reuses PID 835726 and the identical message text, with different `realtime_us` and `source_monotonic_us` | `fail` |
| T8 | The same timestamps with a one-byte change to the message (the `ip`) | `fail` |
| T9 | The acknowledged entry **and** an exact duplicate entry with the same key in one read | `fail` with an ambiguity note |
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
| T40 | Interrupted write: `os.replace` (and separately `os.fsync`) patched to raise | The original file is byte-identical (or still absent), and the writer's temp file is removed |

Group 8: integration, decoding and the CLI.

| ID | Case | Expected |
|---|---|---|
| T41 | `doctor._check_cpu_tripwire` with `check` patched to return the T4 verdict | `ok=True`, `status="warn"`; `doctor_exit_code([that check])` is 0 |
| T42 | A `MESSAGE` given as a byte array with invalid UTF-8 | Classified from the replacement-decoded text; `message_sha256` taken over the raw bytes |
| T43 | One malformed JSON line among valid ones | The blind WARN (`kernel log unreadable`); no acknowledgment applied |
| T44 | `show --json` against the T4, T14 and T31 states | The states `applied`, `inert (previous boot)` and `revoked`, each with full keys. The copyable `ack` line appears only for an acknowledgeable fault with no active record. |

**Mutation sanity (verification lane, G2):** each of these mutations must make
at least one test fail:

1. Removing `boot_id` from the key.
2. Matching on `process` instead of the key.
3. Letting acknowledged faults yield PASS.
4. Skipping a bad JSON line instead of going blind.
5. Rejecting only the bad record instead of the whole file.

## A. Acceptance criteria (for G2)

- [ ] T0–T44 pass. The existing `tests/test_cpu_tripwire.py` and
      `tests/test_doctor.py` pass unchanged, except for additions.
- [ ] Every changed line is covered by a test (diff coverage), including the
      error branches in `load_acks`, `write_ack` and the boot cross-check.
- [ ] With no acknowledgment file, doctor's `cpu_tripwire` detail is
      byte-identical to `main` for every T1 fixture.
- [ ] The diff touches only `cpu_tripwire.py`, `cpu_tripwire_ack.py`,
      `convmem.py`, the tests, and the manifest. It touches none of the
      §4 out-of-scope files.
- [ ] ruff, the pylint gate, `git diff --check`, and the committed-manifest
      pytest pass on a clean committed tree.
- [ ] No test writes outside `tmp_path`, and no real `journalctl` or
      `coredumpctl` runs (T0).

## P. Live-use runbook (G4–G6; listed for review, not authorized)

G4 promotion, run by the lane Ryan names, with his exact SHA:

1. `git -C ~/Projects/convmem/.worktrees/runtime-main status --short` is
   empty.
2. `git diff --stat 1a68675 <SHA>` lists only expected files. The four
   checkpoint-safety files are unchanged:
   `distill.py`, `llm.py`, `incremental_transform_contract.py`,
   `incremental_checkpoint_migration.py`.
3. `git -C <runtime-main> grep -n "cpu_tripwire" -- '*.py' ':!tests/'`
   lists only `cpu_tripwire.py`, `cpu_tripwire_ack.py`, `convmem.py` (CLI)
   and the lazy import inside `doctor._check_cpu_tripwire`. Evidence at
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
   `--authority-ref` pointing at the G5 grant. Type the ID `4c6debf6cee1`.
4. Run `convmem doctor` and record the result.

Any lane may then verify, read-only: architecture §10.2.

If the result is wrong, roll back as in architecture §10.3: revoke the record,
move the file aside, or promote back. G6 remains Ryan's alone.

<!-- ref: ./ARCHITECTURE-doctor-fault-acknowledgment.md, ./STATUS-codex-jsonl-production-integration.md — binding spec and arc brief -->
<!-- src: ../../tests/test_cpu_tripwire.py, ../../config/repository-knowledge/openclaw-watch-scope-v1.json — existing fixtures and manifest classification -->
