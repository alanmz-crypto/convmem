# Execution Plan — Scoped CPU-Tripwire Fault Acknowledgment

**Arc:** Codex (priority #1)
**Date:** 2026-10-22
**Authors:** Claude (initial plan); Codex (review corrections and implementation)
**Architecture:** [`ARCHITECTURE-doctor-fault-acknowledgment.md`](ARCHITECTURE-doctor-fault-acknowledgment.md) (the binding spec; section numbers below such as §5.2 refer to it)
**Resume state:** `G4_COMPLETE`. Independent G2 reviews PASSed the immutable content revision. Ryan merged PR #416 as `4b4796b6a667509f94475a5a14424204947fbb12` (G3), then directed the exact-SHA runtime fast-forward (G4), completed 2026-10-25 without a watcher restart. Post-promotion doctor exited 0 with zero native faults. The old-event G5 is moot after reboot; Ryan owns G6 acceptance. Earlier G0 and corrective review findings remain historical.
**Current review target:** `1a7676b75bb287d9ca1fc0eb53c7176e06c7b922` (immutable corrective content revision; later routing edits are documentation only).

```
Planning Status

Phase:        G4 complete; G5 old event moot; G6 pending Ryan's decision
Lanes:        Ryan G6; future live acknowledgments need separate grants
Authority:    G3 merge and G4 promotion are complete, not reusable grants.
```

---

## G. Gates (in order, each Ryan- or reviewer-owned)

| # | Gate | Owner | What it permits | What it does NOT permit |
|---|---|---|---|---|
| G0 | Prior exact-revision design review | Codex, substituting for Kiro | Historical FAIL at `2a138be9b0a12ae8849665435ab7ba1674154853`; Claude's later PASS-WITH-CHANGES at `4d1aedd` led to reader fixes at the current target | No self-issued PASS |
| G1 | Ryan's explicit 2026-10-22 takeover instruction | Ryan; Codex executes | Correct the design and implement E1–E5 hermetically; Claude reviews the result | Promotion, live use, a PR without a request, merge |
| G2 | Exact-tip verification and independent reviews | Claude (diff coverage and assigned review) + independent Codex safety reviewer (Ryan-directed replacement after Copilot limit) + fresh Claude Opus-class session (Ryan-assigned original Kiro implementation-review slot); Codex implementation owner supplies author verification | A PR decision only after the required evidence and reviews are complete on the corrected exact revision | Merge, promotion, live use or acceptance |
| G3 | PR and merge | Ryan | The code lands on `main` | Runtime promotion |
| G4 | Runtime promotion grant at an exact SHA | Ryan | A fast-forward of `.worktrees/runtime-main`, **with no watcher restart** | Live acknowledgment |
| G5 | One-event live acknowledgment | Ryan runs it himself | One `convmem tripwire ack` for key `bab67b49aa4f` | Any other event; any acceptance claim |
| G6 | Acceptance decision | Ryan | Deciding whether the deployment's doctor criterion is satisfied | n/a |

If Ryan reboots before G5, G5 is moot (architecture §10.1, step 6). E1–E5
remain valid for future events if Ryan still wants the mechanism.

**Review-routing correction (2026-10-23):** the takeover packet incorrectly
reduced G2 to Codex verification plus Claude review. Original §G at merged
design `3d24c753a4b46132d349c34a2cd37b0fbba464c2` required Claude diff coverage,
Copilot's targeted safety audit and Kiro's implementation review. Ryan assigned
Codex implementation and Claude review, but no explicit waiver of the other
G2 requirements was found. They remain required. Claude's static
PASS-WITH-CHANGES at the earlier SHA was evidence for its own review only.
Claude's later exact-SHA PASS applies to `e419810`. Ryan then delegated the
choice of a replacement after Copilot reached its limit. A separate read-only
Codex reviewer found two safety/correctness gaps at that SHA. The fixes at
`fb1d251`, with the regenerated writer inventory at `49d9d67`, PASSed the
replacement safety review. Claude later PASSed the R4 repair at `1a825d0`.
Ryan assigned a fresh Claude Opus-class session to the original Kiro G2
implementation-review slot. Its first pass at `1a825d0` was static because
shell permissions were denied. It exposed two retry/durability issues that
Codex reproduced and corrected at the current target. An independent,
shell-capable implementation recheck and a separate safety delta recheck
both PASSed the corrected content at `1a7676b`; G2 is complete.

## E. Implementation steps (Codex, under Ryan's takeover grant)

Branch: `feat/2026-10-22-doctor-fault-ack-takeover`, created and pushed with
`convmem work start feat doctor-fault-ack-takeover --worktree`. The inherited
implementation was copied into an isolated checkout without modifying its source.
Push every commit with an explicit refspec. Do not open a PR unless Ryan asks.

**E1. Identity-bearing journal read** in `cpu_tripwire_events.py` and
`cpu_tripwire.py` (the latter retains existing public imports):

- Add optional fields to `Fault`, all defaulting to `None` so positional
  construction in the existing tests keeps working: `boot_id`, `realtime_us`,
  `source_monotonic_us`, `message_sha256`, raw-byte `message`, `cursor`;
  `hostname` defaults to `unknown`.
- Factor the message classification in `parse_kernel_faults` into one helper.
  `parse_kernel_faults(lines)` (short-iso) keeps its exact behavior for the
  existing tests.
- Add `parse_kernel_journal(lines) -> JournalRead`: faults, observed boot IDs
  and problems travel together. Parse every decodable MESSAGE, including
  repeated fields, and retain faults before and after malformed input. Any
  incomplete read disables acknowledgments; it never overrides a detected FAIL.
- `read_kernel_faults()` switches to the JSON argv with `--all` in §5.1.
  Nonzero exits and timeouts retain captured stdout and mark the read incomplete.
- Add `read_boot_id(path=Path("/proc/sys/kernel/random/boot_id")) -> str | None`.
  It strips dashes, lowercases, and requires 32 hex characters.

**E2. Acknowledgment store**, a new module `cpu_tripwire_ack.py` with no
imports from `doctor`, `convmem`, or any ingest or watcher module:

- `ACK_SCHEMA`, `ACK_VERSION = 1`, `DEFAULT_ACK_PATH`. The default path is
  resolved at call time from `Path.home()`.
- `EventKey.ack_id` hashes all five fields; the shared event module owns
  classification and identity so the store and evaluator cannot form an import cycle.
- `load_acks(path) -> AckSet`. An `AckSet` holds the records and a
  `problem: str | None` (`invalid: …` or `unreadable: …`). It never raises
  for file content. It enforces all seven checks in §6, rejecting the whole
  file on any failure.
- `write_ack(...)` and `revoke_ack(...)`: flock, temp file, fsync, replace,
  fsync of the directory (§8). Inject `path`, `now`, confirmation, TTY check
  and a callable supplying an `AckContext` from one fresh evidence read.
  Revoked keys refuse re-acknowledgment without rewriting the file. Idempotent
  retries fsync the current file and directory, preserving attribution.
  Post-replacement failures raise `DurabilityUnconfirmed`, not a no-change refusal.
- `ackable(fault, known_bad) -> bool`: the rule in §7, step 3.

**E3. Policy integration** in `cpu_tripwire.evaluate()` and `check()`:

- Implement architecture §9.1 exactly.
- Add keyword-only `acks`, `current_boot_id` and `ack_problem`.
- Share `read_signals()` and `evaluate_signals()` between doctor and the CLI.
  Always evaluate online CPUs and retained faults, including incomplete reads.
- `check()` gains the keyword parameters `ack_path` and `boot_id_path`, with
  production defaults. It loads acknowledgments only when the file exists.
- The detail text follows §9.2.
- `doctor._check_cpu_tripwire` does not change. If a test needs to inject
  paths, monkeypatching `cpu_tripwire.check` is enough.

**E4. CLI**: thin Typer registration in `convmem.py` delegates to
`cpu_tripwire_cli.py`, with `show`, `ack` and `revoke` (§7):

- Handlers only delegate, with ≤ 15 lines of logic each.
- `show` prints the copyable `ack` command.
- `ack` enforces the TTY check, requires exactly one matching entry, refuses
  anything that cannot be acknowledged, and requires the operator to type the
  ID.
- Exit codes: 0 when durable or durably confirmed already present; 1 when
  refused or the lock is busy; 2 for bad usage or no TTY; 3 when a replacement
  or existing-document retry sync leaves durability unconfirmed. After a new
  replacement, the message says the document was written and the next read
  evaluates it. On retry, the message says the existing document is visible
  without claiming that invocation wrote it. A failed verdict refresh after a
  completed operation still exits 0, names the completed action, and says the
  current verdict is unavailable; it does not say "refused" or invent a verdict.
- Copyable commands use shell quoting for the opaque cursor. Revoked records
  do not receive an `ack` command. Mixed FAIL output includes the ack author.
- Add the three commands to the usage block at the top of `convmem.py`.

**E5. Repository hygiene**:

- Classify `cpu_tripwire_ack.py`, `cpu_tripwire_events.py`,
  `cpu_tripwire_cli.py` and any new test files in
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
| T6 | T4 plus a second Timeshift segfault on CPU 13: new PID, later times | `fail`. Detail names the new fault and the acknowledgment ID, author, time and reason. |
| T7 | A recurrence that reuses PID 835726 and the identical message text, with different `realtime_us` and `source_monotonic_us` | `fail` |
| T8 | The same timestamps with a one-byte change to the message (the `ip`) | `fail` |
| T9 | The acknowledged entry **and** an exact duplicate entry with the same key in one read | `fail` with an ambiguity note |
| T45 | The acknowledged entry is gone (vacuumed) and a different entry with the same boot, `realtime_us`, `source_monotonic_us` and message remains, with a different `cursor` | `fail`; the survivor is not acknowledged and `show` reports `inert (entry not present)` (G0 finding 3) |
| T46 | The acknowledged entry unchanged, same cursor, in a read where the original is the only match | `warn` (control for T45) |
| T47 | An entry with no `__CURSOR` field that otherwise matches a record | `fail`; it can never be acknowledged |
| T10 | T4 plus a machine-check line | `fail` with machine-check text and acknowledgment attribution |
| T11 | T4 plus a known-bad CPU online (`online = 0-23`, known-bad `[4, 5, 8, 9]`) | `fail` with `ONLINE again` and acknowledgment attribution |
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
| T38 | Run again for the same active key, including when the journal is unavailable | Fsync existing file and directory under lock without rereading the journal; exit 0, "already acknowledged", with byte-identical content. Sync failure exits 3 with existing-document visibility and uncertainty, without claiming a write. |
| T39 | Lock held by another file descriptor | Exit 1, and the file is unchanged |
| T40 | Failure at file fsync or replacement, before replacement succeeds | The original file is byte-identical (or still absent), and the writer's temp file is removed; test ack and revoke. Post-replacement failures are T50. |

Group 8: integration, decoding and the CLI.

| ID | Case | Expected |
|---|---|---|
| T41 | `doctor._check_cpu_tripwire` with `check` patched to return the T4 verdict | `ok=True`, `status="warn"`; `doctor_exit_code([that check])` is 0 |
| T42 | A `MESSAGE` byte array with invalid UTF-8, then ack/store/reload | Classified from replacement-decoded text; hash and persisted evidence preserve raw bytes; valid reload applies only to that exact entry. |
| T43 | Malformed/non-object/null/invalid MESSAGE before or after valid new CPU-attributed faults or MCE, with an existing ack | Retain each hard-fault description and FAIL, disable acknowledgments, add incompleteness note. With no detected FAIL, incompleteness is WARN. |
| T44 | `show --json` against the T4, T14 and T31 states | The states `applied`, `inert (previous boot)` and `revoked`, each with full keys. The copyable `ack` line appears only for an acknowledgeable fault with no stored same-key record and complete matching boot evidence. |

Group 9: review corrections beyond T45–T47.

| ID | Case | Expected |
|---|---|---|
| T48 | Re-ack the same key after revocation, including CLI/show | Exit 1, file byte-identical and still valid, FAIL remains, no copyable re-ack command |
| T49 | An oversized MESSAGE; repeated MESSAGE values or duplicate JSON members; journal timeout/nonzero exit with partial stdout | Long messages are fully classified. Numeric conversion failures retain the other known fault fields; malformed coredumps do not erase kernel faults. Retain all decodable FAIL evidence; ambiguous/incomplete input disables acknowledgments. Timeout tests cover bytes and string stdout. |
| T50 | Directory open/fsync failure after replace, for ack and revoke; cleanup would fail on a read-only directory; retry while sync failure persists, then retry successfully | Complete valid new document remains visible; exit 3 states durability uncertainty even if temp-path cleanup would fail. Retry also exits 3 while sync fails, keeps identical bytes/attribution without claiming a new write, and returns success only after file and directory fsync. |
| T51 | Journal unreadable and a known-bad CPU online, with or without acknowledgments | FAIL with `ONLINE again`; the independent check always runs |
| T52 | Valid acknowledgment file changed to mode `0666`, or owned by another effective user | Load rejects the whole file without applying the record; the fault remains FAIL |
| T53 | Current-verdict refresh raises after a durable ack or revoke | CLI exits 0, names the completed action and says the verdict is unavailable; the stored ack/revocation remains effective |

**Mutation sanity (verification lane, G2):** each of these mutations must make
at least one test fail:

1. Removing `boot_id` from the key.
2. Matching on `process` instead of the key.
3. Letting acknowledged faults yield PASS.
4. Clearing the incomplete-read condition so acknowledgments apply despite malformed input.
5. Rejecting only the bad record instead of the whole file.
6. Removing cursor equality from the key.
7. Allowing a revoked key to become active again.
8. Returning idempotent success without retrying durability.

## A. Acceptance criteria (for G2)

- [x] T0–T53 pass. Existing policy assertions remain unchanged; the fake
      journal runner serves JSON to the new reader and fixtures isolate HOME.
      `tests/test_doctor.py` also passes.
- [x] Every changed executable production line is covered by a test (diff
      coverage), including the error branches in `load_acks`, `write_ack` and the boot cross-check.
- [x] With no acknowledgment file, doctor's `cpu_tripwire` detail is
      byte-identical to `main` for every T1 fixture.
- [x] The diff touches only `cpu_tripwire.py`, `cpu_tripwire_ack.py`,
      `cpu_tripwire_events.py`, `cpu_tripwire_cli.py`, `convmem.py`, the tests,
      the manifest, and the existing architecture/plan/review/status/routing
      docs. It touches none of the §4 out-of-scope files.
- [x] Scoped Ruff (and no new CLI findings), the pylint gate,
      `git diff --check`, and the committed-manifest pytest pass
      on a clean committed tree.
- [x] Injected runtime inputs and outputs use `tmp_path`; no host log, live
      config or network access occurs, and no real `journalctl` or
      `coredumpctl` runs (T0).

### Verification evidence (Codex, 2026-10-23)

Implementation and test code at `1768b4a94241853f12cb3fb19676178a9530ed14`
was verified locally. The final review commit also carries documentation
corrections and this evidence. Claude's fixed review candidate is
  `4d1aedd8e213b2201f2fb0e0ff9df5e5efd2c30c`, now a historical review
  target. The 2026-10-23 corrective candidate requires a new immutable SHA.

- Focused tests: **223 passed** across `tests/test_cpu_tripwire.py`,
  `tests/test_cpu_tripwire_ack.py` and `tests/test_doctor.py` (Python 3.13.12,
  pytest 9.1.1). Reproduce from the takeover checkout with the project virtual
  environment and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, running `python -m pytest
  -q -p no:cacheprovider tests/test_cpu_tripwire.py tests/test_cpu_tripwire_ack.py
  tests/test_doctor.py`.
- Committed-manifest guard: **1 passed**, not skipped, on the clean committed
  tree. The existing `convmem.py` include hash matches its content.
- Diff coverage: **639/639 changed executable production lines**, compared
  with merged design `3d24c753a4b46132d349c34a2cd37b0fbba464c2`:
  `convmem.py` 18, `cpu_tripwire.py` 97, `cpu_tripwire_ack.py` 304,
  `cpu_tripwire_cli.py` 70, `cpu_tripwire_events.py` 150. Coverage was measured
  during the focused suite with branch measurement enabled. This is line
  coverage of the diff, not a claim that every possible branch is covered.
- All **8 mutation checks were caught** by test assertions in temporary
  copies: boot hash → T2; process-only/cursor-free matching → T45; false PASS
  → T4/T5; incomplete-read acknowledgments → T43; partial store acceptance
  → mixed-invalid-store; revoked-key reactivation → T31/T32; skipped durability
  retry → post-replacement retry tests for both ack and revoke.
- Ruff passes on the four tripwire modules and two tripwire test files.
  The changed `convmem.py` lines have **0 Ruff findings**; that legacy file
  retains 73 pre-existing findings. It was not broadly reformatted.
- Scoped Pylint reports no findings in those tripwire modules/tests.
  Repository-wide serial Pylint 4.0.6 regression gate: **PASS**, 437 findings
  and 223 fingerprints, with no new/increased findings versus the base SHA.
  CI's baseline remains unchanged. Local Python is 3.13.12; hosted CI uses
  Python 3.12, so this is local verification, not a hosted-CI result.
- `git diff --check` passes. No watcher, ingest, transform, checkpoint or
  `doctor.py` code changed. The new manifest classifications grant no watch
  scope. Six redundant CLI-local import statements were removed after added
  usage text changed line-number-bearing Pylint fingerprints.

### Reader-correction verification at `132658d` (Codex, 2026-10-23)

- Focused hermetic suite: **249 passed** across the two tripwire test files and
  `tests/test_doctor.py` with Python 3.13.12 and pytest 9.1.1. It includes LF-only
  parsing of raw U+2028/U+2029/U+0085 in a JSON `MESSAGE`, both reader decoding
  errors, invalid known-bad CPU configuration, blind-journal wording, and a
  timeout whose partial stdout holds both a CPU segfault and an MCE.
- The preserved reader-fix branch was compared read-only. Its production fixes
  are already present here; its additional 9-case Unicode-separator matrix now
  checks complete reads, text timeouts and byte timeouts with exact fault
  identity preserved.
- A CLI-level post-replacement directory-sync failure returns exit **3**, says
  the document was written but durability is unconfirmed, and leaves the
  acknowledgment applied on the next read. A refusal remains exit 1.
- The printed command passes through actual bash and zsh parsers with its
  opaque cursor and `<reason>` placeholder intact. A non-dict coredump row
  does not interrupt acknowledgment evidence capture; control characters in
  `Fault.describe()` are escaped.
- Scoped Ruff lint and format, scoped Pylint, and `git diff --check` passed.
  The committed-manifest guard passed **1 test** on the pushed content commit.

The author did not run full-repository pytest, a host tripwire invocation,
hardware/power-loss test, runtime promotion, watcher restart or live
acknowledgment. A fresh independent Opus reviewer later compared the full
test tree with main and PASSed the corrected content. G2 is complete.

### Claude R1–R3 follow-up (Codex, 2026-10-23)

Claude's independent full review at `132658d` verified the requested fault
behavior and measured **654/655** changed executable lines against `origin/main`;
the one unexecuted branch was probed directly. Its verdict was
PASS-WITH-CHANGES: six stale shadow/R2b inventory tests, contradictory retry
exit-code text and missing CLI coverage, and a zsh test that assumed the shell
was installed. This is historical coverage evidence for that SHA, not a claim
of final-delta coverage.

- The shadow inventory now names the five shifted `convmem.py` writer call
  sites. The unchanged R2b generator refreshed its derived identity and digest
  under isolated HOME/XDG/config paths; both inventory verifiers returned no
  errors. The three affected test files passed **25 tests** on the committed
  corrective content revision, including all six previously failing cases.
- An existing-document retry sync failure now exits **3** and says the document
  is visible without claiming the retry wrote it. New CLI tests cover retry
  failures for ack and revoke, plus a post-replacement revoke failure. The
  existing post-replacement ack test still verifies that the new document is
  effective. Architecture §8 and E4/T38/T50 now use the same exit-code contract.
- The bash/zsh command test skips an absent shell with an explicit reason;
  both arms passed locally. The focused tripwire/doctor suite passed **252**
  tests. Scoped Ruff, format and Pylint passed; `git diff --check` passed.
  The committed-manifest guard passed **1 test** on the clean pushed content
  revision.

Claude's exact-SHA delta re-review at `e419810` returned PASS with no new
required changes. On Python 3.12.13, Claude reports 252 focused tests, 72
inventory tests and 541 wider regression tests passing; every changed delta
line was covered. That selection omitted the scoped-proof inventory test; this
is historical evidence for that revision, not proof that R4 was absent.

### Safety-audit correctives (Codex, 2026-10-23)

After Copilot reached its limit, Ryan directed Codex to choose another agent.
An independent, read-only Codex safety reviewer returned PASS-WITH-CHANGES at
`e419810`: C1 accepted a world-writable acknowledgment file as authority; C2
reported exit 1 after a durable ack/revoke when the later verdict refresh
raised. Both were reproduced in hermetic tests before correction.

At `fb1d251`, the loader checks mode `0600` and current effective-user
ownership on the opened inode, invalidating the whole file on mismatch. A
failed post-commit verdict refresh exits 0 for the completed operation and
reports that the current verdict is unavailable. CLI tests exercise both ack
and revoke, verify stored effect, and prevent a false refusal. The four-file
focused suite passed **257 tests**. Coverage reports **100% line and branch**
for `cpu_tripwire_ack.py` and **100% line**, one pre-existing partial branch,
for `cpu_tripwire_cli.py`. Scoped Ruff, format and Pylint passed; 27 doc tests
and 120 subtests passed; the clean-tree manifest guard passed **1 test**.
Those module changes rotated the R2b implementation identity. The existing
inventory writer regenerated its committed JSON at `49d9d67`; all **25**
affected inventory tests passed, with the route count unchanged at **39**.

The replacement safety reviewer PASSed `49d9d67` after independently matching
all 39 inventory routes and rerunning 25 inventory and 255 focused tests.
Claude's later final-delta review at `49d9d67` was PASS-WITH-CHANGES for R4:
the scoped-proof inventory was stale after the shadow writer-coordinate
update. The generated file alone was refreshed at `1a825d0` (nine lines,
three route sites). Codex reproduced the machine-check test failure before
regeneration, then ran the scoped-proof, shadow, R2b and committed-manifest
selection on the clean content commit: **44 passed**, including
`tests/test_issue_286_scoped_proof_shadow.py::test_c_sh2_cc1_writer_inventory_machine_checked`.
The R2b inventory is unchanged by this correction. The replacement safety
reviewer PASSed `1a825d0`, matching all 38 scoped-proof routes against the
generator and passing 255 focused tests. Claude independently PASSed the R4
recheck at the same SHA: 391 targeted tests passed, and its whole-tree
comparison against `origin/main` found no branch-introduced failure. The
target had 110 failures and 32 errors; main had 111 failures and 32 errors,
with only a known ext4 inode-reuse flake failing on main. Both runs shared
142 environment failures/errors without torch or the Safe Harbor launcher.
The fresh implementation review and final safety delta recheck PASSed
`1a7676b`. Hosted CI was not run. No
runtime or live acknowledgment action was performed.

## P. Historical G4–G5 runbook; G6 pending

**Current state (2026-10-25):** Ryan merged PR #416 as `4b4796b`, then
directed G4 promotion. Codex fast-forwarded the clean runtime from `1a68675`
to that exact SHA; the watcher stayed at PID 1149 with `NRestarts=0` and was
not restarted. Post-promotion doctor exited 0 with zero native faults this
boot. The investigated event belongs to an earlier boot, so the G5 steps
below are historical and must not be run for it. Any future event requires a
separate live-use grant. Ryan alone decides G6 acceptance.

G4 promotion, run by the lane Ryan names, with his exact SHA:

1. `git -C ~/Projects/convmem/.worktrees/runtime-main status --short` is
   empty.
2. `git diff --stat 1a68675 <SHA>` lists only expected files. The four
   checkpoint-safety files are unchanged:
   `distill.py`, `llm.py`, `incremental_transform_contract.py`,
   `incremental_checkpoint_migration.py`.
3. `git -C <runtime-main> grep -n "cpu_tripwire" -- '*.py' ':!tests/'`
   lists only `cpu_tripwire.py`, `cpu_tripwire_ack.py`, `cpu_tripwire_events.py`,
   `cpu_tripwire_cli.py`, `convmem.py` (CLI)
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
   `--authority-ref` pointing at the G5 grant. Type the ID `bab67b49aa4f`.
4. Run `convmem doctor` and record the result.

Any lane may then verify, read-only: architecture §10.2.

If the result is wrong, roll back as in architecture §10.3: revoke the record,
move the file aside, or promote back. G6 remains Ryan's alone.

<!-- ref: ./ARCHITECTURE-doctor-fault-acknowledgment.md, ./STATUS-codex-jsonl-production-integration.md — binding spec and arc brief -->
<!-- src: ../../tests/test_cpu_tripwire.py, ../../config/repository-knowledge/openclaw-watch-scope-v1.json — existing fixtures and manifest classification -->
