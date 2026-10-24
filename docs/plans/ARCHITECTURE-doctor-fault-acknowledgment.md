# Architecture — Scoped CPU-Tripwire Fault Acknowledgment

**Arc:** Codex (priority #1: the deployment's doctor-acceptance criterion)
**Date:** 2026-10-22
**Updated:** 2026-10-24
**Authors:** Claude (initial design); Codex (review corrections and implementation)
**Branch:** `feat/2026-10-22-doctor-fault-ack-takeover` (from merged design `3d24c75`)
**Current review target:** `1a7676b75bb287d9ca1fc0eb53c7176e06c7b922`
**Companion:** [`EXECUTION-doctor-fault-acknowledgment.md`](EXECUTION-doctor-fault-acknowledgment.md)
**Input handoff:** [`CODEX-2026-10-22-doctor-ack-next-model-handoff.md`](../inter-model/CODEX-2026-10-22-doctor-ack-next-model-handoff.md)

```
Planning Status

Phase:        G2 PASS; PR #416 open for Ryan's G3 decision
Lanes:        Ryan G3–G6
Authority:    Ryan directed Codex to take over on 2026-10-22: "You take over,
              beginning, now, then." Claude reviews the resulting work.
              This grants implementation and hermetic checks; merge, promotion,
              live acknowledgment and acceptance remain separate. G0 remains FAIL
              at 2a138be9b0a12ae8849665435ab7ba1674154853 as historical evidence.
```

Claude's static review of `4d1aedd8e213b2201f2fb0e0ff9df5e5efd2c30c` found
two reader defects under §5.1: Unicode record splitting and uncaught decoding
errors. They are corrected in this takeover candidate. The existing
[review packet](../inter-model/KIRO-2026-10-22-doctor-fault-ack-design-review-handoff.md)
records the historical result, new corrections, advisories and lane comparison.
Claude's full review at `132658d` verified the fault behavior and diff coverage,
then required mechanical inventory repair, a consistent retry exit-code
contract, and a portable shell test. These were corrected at `e419810`.
Claude's exact-SHA delta re-review returned PASS there. After
Copilot reached its limit, Ryan directed Codex to choose another agent; a
separate Codex safety reviewer found two required fixes at `e419810`. File
mode/owner load validation and accurate post-commit CLI reporting are corrected
at `49d9d67`, which the safety reviewer PASSed. Claude's final delta review
then found a stale scoped-proof inventory, repaired at `1a825d0`. The
replacement safety reviewer and Claude's R4 recheck PASSed that revision.
A first Opus implementation review at `1a825d0` was restricted to static
reading. It identified post-replace cleanup and existing-record retry defects
that Codex reproduced and corrected at the current target. Ryan assigned a
fresh Claude Opus-class session to the original Kiro G2 implementation-review
slot. Its shell-capable independent review PASSed the corrected content SHA,
and the separate safety reviewer PASSed the final delta. G2 is complete;
PR #416 is open for Ryan's G3 merge decision.

---

## 1. Consequence (what changes for Ryan)

Today `convmem doctor` exits 1 for the rest of this boot because of one
investigated event: the Timeshift segfault at `2026-10-22 13:01:22 CDT`.
Doctor rereads the kernel log on every run and stores no failure flag, so there
is nothing to reset. Without a reboot, the only ways to get exit 0 are to
weaken the policy (forbidden) or to add a way to acknowledge one event.

After this design is implemented and separately deployed, Ryan can acknowledge
exactly that one kernel log entry from his own terminal. Doctor then reports
`cpu_tripwire` as **WARN**, not PASS. The detail names the acknowledged event,
who acknowledged it, when, and why, and says hardware health is unproven.
Doctor exits 0 unless something else fails. Any other fault that the current
policy treats as FAIL still FAILs, including:

- a second Timeshift crash, even on CPU 13,
- a crash with the same message text in a different boot,
- a machine check, and
- a known-bad CPU coming back online.

The acknowledgment stops matching at the next reboot, and revoking it restores
the FAIL on the next doctor run.

This changes what doctor reports. It does not decide whether the deployment is
accepted (§10).

## 2. Problem statement and evidence

Event evidence, re-read read-only on 2026-10-22 from `journalctl -k -b 0 -o json`
and `coredumpctl list --json=short` (this design's session); it matches the
input handoff:

| Field | Value |
|---|---|
| `_BOOT_ID` | `7f8e9d592ecc46c7aeb599df6b9457b2` (`/proc/sys/kernel/random/boot_id` renders it with dashes: `7f8e9d59-2ecc-46c7-aeb5-99df6b9457b2`) |
| `__REALTIME_TIMESTAMP` | `1792692082959438` µs (`2026-10-22T13:01:22-05:00`) |
| `_SOURCE_MONOTONIC_TIMESTAMP` | `216789351540` µs, kernel `CLOCK_BOOTTIME` under its legacy field name |
| `__CURSOR` | `s=e02dcabee64b4080b72afc4344ccf25d;i=56398d5;b=7f8e9d592ecc46c7aeb599df6b9457b2;m=327a1c130d;t=65e71a6cbe44e;x=81580ac8b8a26341` |
| `_TRANSPORT` / host | `kernel` / `archlinux` |
| `MESSAGE` | `timeshift[835726]: segfault at 0 ip 0000557bdb8648da sp 00007ffe1ccb1ff0 error 4 in timeshift[168da,557bdb854000+40000] likely on CPU 13 (core 33, socket 0)` |
| SHA-256 of `MESSAGE` (UTF-8) | `5bcabab44b0af36b045e40b9371cfee06c04ae670e201f25a2494a28225b518d` |
| Corresponding coredump | `time=1792692083077653` (118 ms later), `pid=835726`, `sig=11`, `uid=0`, `exe=/usr/bin/timeshift`, `corefile=inaccessible` |

Context, not identity: this is the only kernel fault line this boot. The other
two coredumps this boot are Chromium `SIGTRAP` (signal 5), which the tripwire
ignores. Online CPUs were `0-3,6-7,10-19`, and the configured
`known_bad_cpus` list is `[4, 5, 8, 9]`. Ryan unplugged the backup USB volume
at `13:01:18`, four seconds before the crash. Losing the storage is the leading
explanation, but no root cause and no CPU defect is proven. The earlier triage
found no machine-check event in this boot's log.

Current code ([`cpu_tripwire.py`](../../cpu_tripwire.py)):

- `read_kernel_faults()` runs `journalctl -k -b 0 -o short-iso`, which keeps
  only a second-precision timestamp, the process name, the PID and the CPU.
  None of these identifies one kernel entry uniquely.
- `evaluate()` puts any fault the kernel pinned to a CPU outside
  `known_bad_cpus` into the FAIL bucket. When it FAILs, the detail text leaves
  out all the WARN notes.
- `check()` reads everything again on each run, so there is no stored flag to
  clear.

## 3. Options considered (design it twice)

| Option | Mechanism | Verdict |
|---|---|---|
| 0. Governance only | Ryan accepts doctor exit 1 as a documented, known FAIL until the next reboot. No code changes. | **Rejected as the mechanism; kept as the fallback.** Doctor exits 1 on every run and every agent session starts on a failed check. A FAIL that everyone has learned to skip is exactly how a *new* fault gets missed. It needs no code, so Ryan can still choose it (§11). |
| A. High-water mark | Doctor ignores every fault logged before a recorded journal cursor. | **Rejected.** It acknowledges a whole period of the log, not one event: a machine check or a second crash written before the mark would be hidden too. This is the "blanket exception" the handoff forbids. |
| B. Allowlist by process or CPU | Treat `timeshift` faults, or faults on CPU 13, as WARN. | **Rejected.** It is forbidden by the handoff, and the next real CPU 13 failure would be hidden. |
| C. Decision-ledger record | Doctor reads a `convmem record` decision that carries the event key. | **Rejected.** Doctor would depend on the ledger's prose records and how they are approved. That is the wrong owner for host state that only lasts one boot, and the schema checks would be weaker. |
| **D. Per-event acknowledgment file plus operator CLI** | A strictly validated file under `~/.config/convmem/` holds acknowledgments keyed to one exact kernel journal entry. A read-only `show` command prints the exact `ack` command. Only an interactive `ack` writes the file. Doctor turns a matched FAIL into a visible WARN. | **Chosen.** Each acknowledgment matches one entry and cannot carry over to another boot. It fails closed when anything is wrong, and Ryan can inspect and revoke it. Putting the file in the live-configuration directory means the existing "agents do not edit live configuration" rule covers it, so no new rule is needed. |

## 4. System boundary

**In scope**

- Event identity for kernel fault entries (§5), using one JSON journal read in
  place of the current `short-iso` read.
- An acknowledgment store under `~/.config/convmem/`: its file format, strict
  validation, atomic writes, and revocation (§6–§8).
- How `evaluate()` treats acknowledged faults, and how doctor reports them (§9).
- A Typer group `convmem tripwire` with three commands: `show` (read-only),
  `ack` (interactive), and `revoke` (§7).
- Hermetic tests for all of the above (execution plan, §T).

**Out of scope (each needs its own authority)**

- Changing any other FAIL/WARN policy for unacknowledged faults: machine checks,
  userspace faults and orphan dumps retain their current classification.
- `known_bad_cpus`, CPU offlining, rebooting, and clearing journals or
  coredumps.
- Acknowledging machine checks, known-bad CPUs coming back online, kernel oops
  entries, or orphan coredumps. None of these can be acknowledged.
- Any change to the watcher, ingest, transform contract, or checkpoint code.
  The diff must not touch `distill.py`, `llm.py`,
  `incremental_transform_contract.py`, `incremental_checkpoint_migration.py`,
  `ingest.py`, `incremental_jsonl*.py`, or `watch.py`.
- Adding acknowledgment data to `DoctorCheck`, `doctor_payload` or `brief`.
  Doctor reports it through the `detail` text only. Structured output belongs
  to `convmem tripwire show --json`.
- The Arc Codex queue: #286 evidence reconciliation, Crush #393, and retrieval
  #320/#263.

Implementation boundaries (one-way dependencies):

- `cpu_tripwire_events.py`: classification, raw message decoding and event keys.
- `cpu_tripwire_ack.py`: validation, matching, atomic storage and writer rules.
- `cpu_tripwire.py`: evidence collection and verdict policy; retains the legacy
  `Fault` and `parse_kernel_faults` import surface for existing callers/tests.
- `cpu_tripwire_cli.py`: operator presentation and orchestration.
- `convmem.py`: thin Typer handlers and command registration.

This separates parsing and CLI orchestration from persistence without introducing
an import cycle. These modules, their tests, the existing planning/routing docs,
and repository-knowledge classifications are the implementation scope.

**Decision (Ryan, 2026-10-23):** Invalid `[hardware] known_bad_cpus` cannot short-circuit to WARN; a detected CPU-attributed fault FAILs.
**Decision (Ryan, 2026-10-23):** An unreadable journal together with a known-bad CPU online FAILs.

## 5. Event identity

### 5.1 Reading the journal

`read_kernel_faults()` switches to **one** read:

```text
journalctl -k -b 0 -o json --all --output-fields=MESSAGE,_SOURCE_MONOTONIC_TIMESTAMP,_HOSTNAME --no-pager -q
```

`journalctl` always adds `__CURSOR`, `__REALTIME_TIMESTAMP`,
`__MONOTONIC_TIMESTAMP` and `_BOOT_ID` to JSON output. On this host the JSON
read took 44 ms for 2,588 entries (1.3 MB); the text read took 17 ms. Each
entry's `MESSAGE` goes through the **existing** classifier, unchanged. The
`when` field is rendered from `__REALTIME_TIMESTAMP` in local time,
truncated to whole seconds with integer arithmetic (`datetime.fromtimestamp(us // 1_000_000).astimezone().isoformat(timespec="seconds")`; no float division),
so `Fault.describe()` prints the same text as before. With no acknowledgment
file and complete readable input, the T1 fixtures retain today's classification,
verdict and detail byte-for-byte. Incomplete reads follow the correction below.

A second read for identity was rejected: if a new fault were logged between
the two reads, the classified list and the identity list would disagree.

Decoding rules (each an explicit test; corrected after G0):

- Request `--all` so journalctl does not replace fields larger than 4096 bytes
  with JSON `null`. A `MESSAGE` string is UTF-8 encoded; a byte array retains
  its raw bytes. Classification uses replacement-decoded text, hashing uses
  raw bytes. `evidence.message` stores a UTF-8 string or a byte array losslessly.
- Malformed JSON, non-object entries, null/invalid messages, or repeated
  `MESSAGE` values make the read incomplete. Keep every decodable fault,
  disable **all** acknowledgments for that read, and add a blindness note.
  A detected CPU-attributed fault, machine check, or known-bad CPU online
  remains FAIL. In the absence of detected FAIL evidence, blindness is WARN.
  Do not return early before evaluating the online-CPU signal.
- Repeated `MESSAGE` values are classified individually when decodable;
  their entry has no acknowledgeable identity. Duplicate JSON object members
  also mark the read incomplete; preserve every decodable `MESSAGE` rather than
  accepting only the last duplicate. No error clears earlier or later faults.
- A nonzero journalctl exit or timeout marks the read incomplete. Parse any
  captured stdout first, including complete lines before a truncated tail.
  These conditions never discard already available positive fault evidence.
- Split JSON records on LF only; Unicode separators within `MESSAGE` belong to
  the same entry. A journal or coredump decoding error marks that reader
  unreadable while preserving independently observed failures.
- If a numeric CPU/PID field cannot be converted, retain the fault kind and
  other usable fields and mark the read incomplete. An unusable CPU number
  cannot erase a machine-check classification. Malformed coredump rows make
  that auxiliary signal unreadable; they never discard kernel evidence or
  skip the independent online-CPU check.
- Missing or invalid identity fields make that fault unacknowledgeable while
  preserving classification. Invalid timestamps render as `unknown time`.
  All observed entry boot IDs, including noise entries, participate in the
  boot cross-check. A missing/invalid boot ID disables acknowledgments.
- `JournalRead` carries faults, observed boot IDs and decoding problems together;
  this avoids using `None` to discard a partially successful read.

### 5.2 The event key

An acknowledgment matches one journal entry, and only if **all five** of these
match exactly:

| Component | Normalization | Why it is in the key |
|---|---|---|
| `boot_id` | 32 lowercase hex characters, no dashes | Limits the key to one boot. It is a random 128-bit UUID, unique across boots and hosts. |
| `realtime_us` | integer | The time journald received the entry. Stored with the entry and stable. |
| `source_monotonic_us` | integer | Journald stores the kernel's `CLOCK_BOOTTIME` timestamp under the legacy `_SOURCE_MONOTONIC_TIMESTAMP` name. It is not the reception clock `__MONOTONIC_TIMESTAMP` (`CLOCK_MONOTONIC`), and must not be derived from realtime or interpreted as a cursor. |
| `message_sha256` | 64 lowercase hex characters | Covers the PID, IP, SP, error code, CPU and mapping offsets. Changing one byte breaks the match. |
| `cursor` | The `__CURSOR` string, compared byte for byte; never parsed | Identifies this entry's position in the journal. The other four fields could in principle be shared by a second entry (same boot, microsecond and message). The cursor is what systemd documents as the value that uniquely identifies an entry, so a record cannot silently move to a different entry if the original is vacuumed and a look-alike remains. Revised after the G0 review (finding 3). |

`ack_id = sha256("cpu_tripwire_ack_v1|" + boot_id + "|" + realtime_us + "|" + source_monotonic_us + "|" + message_sha256 + "|" + cursor)`,
lowercase hex. Commands and doctor display the first 12 characters. For this
event:

- `ack_id` is `bab67b49aa4f5178700bbab29af53533a3bc4da7a74c6bdde16c051c2902675b`.
- The short form is `bab67b49aa4f`.

Fields that are **not** in the key:

- The process name or PID: a PID can be reused within one boot.
- The CPU: another real fault can land on CPU 13.
- Coredumps: see §5.3.

**How the cursor is used.** The design never parses it, because its format is
opaque; it only tests two strings for equality. If journald rewrites an entry
into another journal file (for example when it moves runtime logs to
persistent storage), the entry's cursor may change. The record then no longer
matches, the fault returns to FAIL, and `show` reports `inert (entry not
present)`. That failure direction is safe: Ryan can revoke the record and
acknowledge the entry again under its new key.

### 5.3 Matching kernel entries to coredumps

Coredumps are evidence, not part of the key.

- At `ack` time, the command records a matching coredump in the record's
  `evidence` block if there is one: same PID, a hardware signal, and within 5 s
  after `realtime_us`. Finding no dump does not block `ack`.
- At doctor time, the orphan-dump calculation keeps using the PIDs of **all**
  kernel faults, acknowledged or not. The acknowledged event's coredump
  (PID 835726, SIGSEGV) therefore stays explained, and acknowledging the kernel
  line cannot turn it into a new "orphan dump" WARN.

Requiring the coredump to match was rejected. systemd-coredump cleans up dumps
on a separate schedule. Once it removed this one, the acknowledgment would
stop working even though the event had not changed. The kernel entry already
identifies the event.

One older weakness stays as it is: if a PID is reused within one boot, an
orphan dump can be treated as explained by an earlier kernel line. That WARN
logic already exists and is not changed here. Acknowledgment neither widens
nor narrows it (§12).

### 5.4 Boot boundaries

- Doctor reads the current boot ID from `/proc/sys/kernel/random/boot_id` and
  normalizes it. Tests inject this path.
- An acknowledgment whose `boot_id` is not the current boot never applies. It
  is reported as **inert (previous boot)**.
- **Boot cross-check:** if any entry from `journalctl -b 0` has a `_BOOT_ID`
  that differs from the current boot ID, or the boot ID cannot be read, then
  no acknowledgments apply and the detail says why. The underlying verdict
  stands. It is never improved.
- A record for the current boot whose entry is no longer in the journal (for
  example, journald vacuumed it during a long uptime) is reported as
  **inert (entry not present)**. That fault is gone from the classified input
  anyway.

## 6. Acknowledgment store

**Path:** `~/.config/convmem/cpu-tripwire-acknowledgments.json`. There is no
config key for it; tests and CLI internals pass the path as a parameter.

- The file is in the live-configuration directory on purpose. Agents are
  already forbidden to edit live configuration (Arc Codex §7 and the lane
  rules), so the same rule covers this file.
- Mode `0600`.
- On load, verify mode `0600` and ownership by the effective user on the opened
  file descriptor. A mismatch invalidates the whole document, so no stored
  acknowledgment applies.
- When the file is missing, behavior is exactly today's.

**Schema version 1.** Unknown keys at any level make the file invalid.

```json
{
  "schema": "convmem.cpu_tripwire.acknowledgments",
  "version": 1,
  "acknowledgments": [
    {
      "ack_id": "bab67b49aa4f5178700bbab29af53533a3bc4da7a74c6bdde16c051c2902675b",
      "event": {
        "boot_id": "7f8e9d592ecc46c7aeb599df6b9457b2",
        "realtime_us": 1792692082959438,
        "source_monotonic_us": 216789351540,
        "message_sha256": "5bcabab44b0af36b045e40b9371cfee06c04ae670e201f25a2494a28225b518d",
        "cursor": "s=e02dcabee64b4080b72afc4344ccf25d;i=56398d5;b=7f8e9d592ecc46c7aeb599df6b9457b2;m=327a1c130d;t=65e71a6cbe44e;x=81580ac8b8a26341",
        "kind": "segfault",
        "cpu": 13,
        "process": "timeshift",
        "pid": 835726
      },
      "evidence": {
        "message": "timeshift[835726]: segfault at 0 ip 0000557bdb8648da sp 00007ffe1ccb1ff0 error 4 in timeshift[168da,557bdb854000+40000] likely on CPU 13 (core 33, socket 0)",
        "hostname": "archlinux",
        "coredump": {"time_us": 1792692083077653, "pid": 835726, "sig": 11, "exe": "/usr/bin/timeshift"}
      },
      "acknowledged_by": "<operator-entered>",
      "acknowledged_at": "<UTC ISO-8601, Z>",
      "reason": "<operator-entered, 1-500 chars>",
      "authority_ref": "<optional repo-relative path or null>",
      "operator_tty": "<os.ttyname(0) at ack time>",
      "revoked_at": null,
      "revoked_by": null,
      "revocation_reason": null
    }
  ]
}
```

The values above are illustrative. The field names, types and checks are
binding.

**Load-time validation.** If any check fails, the whole file is rejected
(fail closed); no records apply even if most are valid:

1. The file is UTF-8 JSON, ≤ 1 MiB, and `schema` and `version` match exactly.
   A higher version is rejected.
2. Every record has exactly the keys above, with the right types. Hex fields
   are lowercase and the right length; `boot_id` has no dashes; timestamps and PIDs are positive integers (booleans rejected); CPUs are
   non-negative integers; `cursor` is a non-empty printable-ASCII string of at most 256
   characters; operator text is printable and non-empty, reasons are at most
   500 characters, timestamps use UTC ISO-8601 ending in `Z`, and
   `authority_ref` is null or a relative repository path without traversal.
   Duplicate JSON fields are rejected, as are non-regular files and symlinks.
3. `ack_id` equals the hash of the key fields (§5.2).
4. `sha256(raw bytes of evidence.message)` equals `event.message_sha256`, **and** running
   the current classifier on `evidence.message` gives exactly the stored
   `kind`, `cpu`, `process` and `pid`. A file that claims `cpu: 13` for a
   different message, or that is hand-edited to say `machine_check`, fails
   this check.
5. The stored `kind` can be acknowledged: it is not `machine_check` or
   `kernel_oops`, and `pid` and `cpu` are not null.
6. `ack_id`s are unique, and at most one non-revoked record exists per key.
7. Revocation fields are either all null or all set: `revoked_at`,
   `revoked_by`, and a non-empty `revocation_reason`.

A rejected file appears in doctor's detail as `acknowledgment file invalid:
<first reason>; no acknowledgments applied` (§9.3).

## 7. Operator commands and authority

A Typer group `convmem tripwire`. Each handler in `convmem.py` only parses
arguments and calls a function in the acknowledgment module (Ousterhout's
limit for `convmem.py`: ≤ 15 lines of logic per handler).

| Command | Writes? | Who may run it | Behavior |
|---|---|---|---|
| `convmem tripwire show [--json]` | No | Anyone, agents included | Lists this boot's classified faults with their full keys and current classification, and every stored acknowledgment with its state: `applied`, `inert (previous boot)`, `inert (entry not present)`, `inert (not needed: no longer a FAIL contributor)`, `revoked`, or `file invalid`. For each eligible, unambiguous fault with no stored record for its key, it prints a shell-quoted `ack` command. Revoked same-key records are not eligible. Decoding/boot failures disable commands and appear as an explicit problem. |
| `convmem tripwire ack --boot-id … --realtime-us … --source-monotonic-us … --message-sha256 … --cursor … --by … --reason … [--authority-ref …]` | Yes | **Ryan, in his own interactive terminal** | All key fields are required. There is no "latest" or by-process selector, so a fault that has just appeared cannot be acknowledged by accident. Steps are listed below. |
| `convmem tripwire revoke <ack-id ≥12 hex> --by … --reason …` | Yes | Ryan, or an agent Ryan explicitly instructs | Sets the revocation fields and keeps the record. It does not require a TTY, because it can only bring back a FAIL. |

`ack` runs these steps:

1. It refuses unless stdin and stdout are both TTYs.
2. It rereads the live journal and requires **exactly one** entry with the key.
3. It requires that entry to be an acknowledgeable FAIL contributor: a CPU is
   attributed, that CPU is not in `known_bad_cpus`, the entry has a PID, and
   its kind is not `machine_check` or `kernel_oops`.
4. It shows the event and asks the operator to type the 12-character short
   `ack_id`. Anything else aborts without writing.
5. It writes the record (§8).
6. It prints the new `cpu_tripwire` verdict.

If an active record for the key already exists, `ack` prints its ID and exits
0 without rewriting after confirming file and directory durability (§8). This
idempotent retry uses the validated stored record and does not need to reread
the journal; a new acknowledgment still requires the live-journal checks above.
If a record for that **same five-field key** is revoked,
`ack` refuses with exit 1 and preserves the file byte-for-byte. Revocation is
terminal for that key; it is never overwritten or deleted by the CLI. A changed
cursor produces a different key and ID, so a fresh acknowledgment can coexist
with the retained revoked record. An ambiguous revoke ID prefix is refused.

**How strong the authority is (honest statement):** this is a single-user host,
and any process running as `lauer` could write the file. The TTY check and the
typed ID slow an agent down; they are not authorization. Authority rests on
three things:

1. **Procedure.** Agents do not edit live configuration, and acknowledgment is
   a Ryan action named in the execution plan.
2. **Attribution.** `acknowledged_by`, `reason`, `authority_ref` and
   `operator_tty` are stored in the record.
3. **Visibility.** Every doctor run shows the active acknowledgment with its
   author, so a quiet edit by someone else is noticed. `show` lets anyone
   check what is stored.

This is the same model as the repo's other local-only guards, such as
`CONVMEM_SKIP_MAIN_HOOK`, which is an audit marker and not access control.

## 8. Persistence, concurrency and interrupted writes

- **Writers:** `ack` and `revoke` take an exclusive non-blocking `flock` on
  `~/.config/convmem/.cpu-tripwire-acknowledgments.lock`. If the lock is
  busy, they refuse with exit 1 and write nothing.
- **Write steps:** the writer loads and validates the current file. An
  invalid or unreadable file blocks both *ack* and *revoke* without rewriting
  it; the emergency alternative remains moving the file aside (§10.3).
  The writer then builds the new document and writes a temp file in the same
  directory (`O_EXCL`, mode `0600`). It fsyncs the file, runs `os.replace()`,
  then fsyncs the directory. Before replacement, failure leaves the old document
  unchanged (or absent). After replacement, a directory-open/fsync failure
  leaves a complete new document and returns exit 3, reporting that durability
  is unconfirmed;
  it does not claim the old document survived. The writer removes its temp
  file only if replacement did not consume it; cleanup cannot mask a
  post-replacement durability error.
- **Retry:** after a post-replacement error, `show` reports the visible state,
  not crash durability. Retry the same command. Under the writer lock, an
  already-active `ack` or already-revoked `revoke` validates the file, fsyncs
  the existing file and then its directory, preserving all bytes and attribution.
  An already-active `ack` does this even if the journal entry has since been
  vacuumed or the journal is temporarily unreadable.
  Success is reported only after both syncs succeed. Another sync failure
  returns exit 3, saying the existing document is visible but durability is
  unconfirmed; the retry did not write it. It never says "refused" or claims
  that nothing changed. A revoked-key `ack` still refuses unchanged.
- **Reader (doctor):** opens only the exact path and takes no lock, because
  replacement is atomic. Stray `*.tmp` files are ignored.
- **Post-commit display:** after a durable `ack` or `revoke`, the CLI attempts
  to refresh the current doctor verdict. If that read fails, the command still
  exits 0 for the completed operation and says the current verdict is
  unavailable. It never calls the committed operation a refusal or claims a
  WARN/FAIL verdict it could not read.
- **Interruption:** whatever point an `ack` dies at, the path holds either the
  old document or the complete new one. With the old document, the FAIL is
  still there; that is the safe direction. With the new one, the record is
  complete, attribution included. There is no separate audit log that could
  disagree with the file: the record is the history, and revocation sets
  fields on it without deleting it.
- **Retention:** records are never pruned automatically. Inert records cost
  one short note in doctor's detail (§9.2). Deleting old records by hand is
  housekeeping and always narrows what is acknowledged.

## 9. Verdict and reporting

### 9.1 Changes to `evaluate()`

The signature gains keyword-only acknowledgment context: `acks`,
`current_boot_id` and `ack_problem`.
With `acks=None` the behavior is today's.

1. Compute `hardware_faults` exactly as today.
2. Split it in two:
   - `acknowledged`: the fault has a complete key, the key equals an active,
     applicable record's key, `fault.boot_id == current_boot_id`, and that
     key occurs **exactly once** in this read.
   - `unacknowledged`: everything else.
   If a key occurs more than once, nothing is acknowledged for it and the
   detail says so.
3. Only `unacknowledged` adds to `problems` (FAIL). The check for a known-bad
   CPU back online and the machine-check rule never consult acknowledgments.
   A machine-check fault cannot be in `acknowledged`, because records of that
   kind are invalid at load (§6.5) and refused at `ack` (§7).
4. `acknowledged` adds a **WARN** note. Acknowledged faults never yield PASS.
5. Orphan-dump PIDs still come from all faults (§5.3).
6. FAIL still overrides WARN. When the result is FAIL, the detail gets a
   suffix counting acknowledged faults, so an active acknowledgment is visible
   even then.

### 9.2 Detail text (contract; exact wording may be polished in review)

- **Only acknowledged:** `WARN`:
  `1 acknowledged CPU-attributed fault, not cleared (hardware health unproven): timeshift[835726] segfault on CPU 13 at 2026-10-22T13:01:22-05:00 [ack bab67b49aa4f by <by> <acknowledged_at>: <reason, first 80 chars>]`
  The other WARN notes follow, separated by `; `.
- **New fault as well:** `FAIL`: today's message for the unacknowledged
  faults, then `; plus 1 acknowledged fault (ack bab67b49aa4f)`, followed by
  the full acknowledged note above, including author, time, reason and
  `hardware health unproven`. This applies to mixed machine-check and
  online-CPU failures too; the author is never omitted when a record applies.
- **Inert records:** status is unchanged; the suffix is
  `; N inert acknowledgment(s) (previous boot / entry not present / revoked) -- see: convmem tripwire show`.
  A PASS stays PASS, and the `0 native faults this boot` text is kept only
  when there really are none.
- **Invalid or unreadable file:** PASS becomes WARN. WARN and FAIL keep their
  status. The suffix is
  `; acknowledgment file invalid: <reason>; no acknowledgments applied`
  (or `unreadable: <errno name>`).
- **Boot cross-check failed:** the same treatment, with the suffix
  `; boot identity mismatch; no acknowledgments applied`.
- **Journal unreadable without a detected fault:** the WARN begins with
  `kernel fault count unknown this boot`, then names the blindness; it does not
  claim zero native faults.

`doctor.py` keeps `_check_cpu_tripwire()` as one line that maps the verdict.
`check()` gains the parameters `ack_path` and `boot_id_path`, with production
defaults. `DoctorCheck`, `doctor_payload` and `doctor_exit_code` do not
change.

### 9.3 Failure handling: no failure can widen an acknowledgment

| Condition | Acknowledgments applied | Status effect |
|---|---|---|
| File missing | none | today's verdict, no note |
| File unreadable (permissions, a directory at the path, I/O error, > 1 MiB) | none | PASS→WARN; otherwise unchanged, with a note |
| Invalid JSON, wrong schema or version, unknown keys, wrong types, bad hash, classifier mismatch, a non-acknowledgeable kind, duplicates, partial revocation | none | PASS→WARN; otherwise unchanged, with a note |
| Record for another boot | that record: none | unchanged, with an inert note |
| Record whose entry is gone | that record: none | unchanged, with an inert note |
| Record revoked | that record: none | the fault FAILs again, with an inert note |
| Key appears in > 1 entry | that key: none | FAIL stands, with a note |
| Journal unreadable, incomplete or malformed | none | Preserve detected FAILs and online-CPU failures; otherwise WARN, with a blindness note |
| Invalid `[hardware] known_bad_cpus` with a detected CPU-attributed fault | none | FAIL, with a configuration note (Ryan, 2026-10-23) |
| Journal unreadable and a known-bad CPU online | none | FAIL, with a blindness note (Ryan, 2026-10-23) |
| Boot ID unreadable or mismatched | none | unchanged or PASS→WARN, with a note |
| Writer interrupted before replacement | the previous file | the previous verdict |
| Directory durability fails after replacement | complete new document (durability unconfirmed) | writer reports uncertainty; next read evaluates the complete document |

**Decision (Ryan, 2026-10-23):** Invalid `[hardware] known_bad_cpus` cannot short-circuit to WARN; any detected CPU-attributed fault FAILs.
**Decision (Ryan, 2026-10-23):** An unreadable journal plus a known-bad CPU online FAILs.

## 10. Deployment, live use, rollback

### 10.1 Separate authorizations (no gate implies the next)

1. G0 re-review of `2a138be9b0a12ae8849665435ab7ba1674154853` returned FAIL:
   C1 cursor identity was resolved; C2–C5 and A1–A3 needed correction.
2. Ryan explicitly handed Codex implementation on 2026-10-22, including the
   remaining decoding and revocation corrections described above.
3. Exact-tip hermetic author verification by Codex, Claude's diff-coverage
   verification and assigned independent review, Copilot audit lane's targeted
   safety audit, and Kiro's implementation review. These original G2
   requirements remain separate; no author verification or single review
   substitutes for the others without Ryan's explicit reassignment or waiver.
   Ryan later assigned a separate Codex reviewer to the capacity-limited
   Copilot slot and a fresh Claude Opus-class session to the Kiro implementation
   slot. Each assignment preserves that slot's independent review obligation.
4. Ryan's PR and merge decision.
5. Ryan's **runtime promotion grant** at an exact SHA. The `convmem` CLI and
   the watcher's index children both run from
   `.worktrees/runtime-main`. The grant must list everything the promotion
   carries from `1a68675` to the target and confirm that the four
   checkpoint-safety files from Arc Codex §3 are unchanged. The tripwire is
   not imported by the watcher, so no watcher restart is needed. The promotion
   step must check this with grep and must not restart the watcher.
6. Ryan's **one-event live acknowledgment**. Ryan runs it himself after
   re-validating, read-only, that:
   - the current boot ID is still `7f8e9d592ecc46c7aeb599df6b9457b2`,
   - the exact entry is present once, and
   - there are no other FAIL contributors.
   If Ryan has rebooted by then, step 6 is moot: the event belongs to the old
   boot and doctor no longer sees it.
7. Ryan's **acceptance decision**. A doctor exit 0 that includes an
   acknowledged WARN is evidence for Ryan to weigh. It does not by itself
   satisfy the deployment's doctor-exit-0 criterion, which was written before
   this mechanism existed.

### 10.2 Verification after live use

These checks are read-only for any lane:

- `convmem tripwire show --json` lists exactly one `applied` record, with key
  `bab67b49aa4f`.
- `convmem doctor` lists `cpu_tripwire` as WARN with the §9.2 text, and exits
  0 if no other check fails.
- The file is mode `0600`, is owned by the effective user, and passes load
  validation.

### 10.3 Rollback

Each of these takes effect on the next doctor run. None needs a restart,
because nothing caches the file:

- **Revoke the acknowledgment:** `convmem tripwire revoke bab67b49aa4f …`.
- **Emergency:** Ryan moves the file aside, for example to
  `cpu-tripwire-acknowledgments.json.disabled-<UTC>`. The FAIL comes back
  immediately. Code from before this change ignores the file entirely.
- **Code rollback:** promote `runtime-main` back to the previous SHA. This
  needs its own grant.

## 11. Decisions made here, and those left to Ryan

**Specified by this design** (Claude may challenge any of them):

- WARN, never PASS, for acknowledged faults.
- A five-part key per journal entry, with the boot boundary built in.
- One JSON journal read.
- A whole file rejected if any part is invalid.
- Machine checks and known-bad CPUs online cannot be acknowledged.
- The file lives in the live-configuration directory.
- Interactive `ack` only.
- Revoke allowed without a TTY.
- No separate audit log.
- No cap on the number of records. Visibility and the per-entry key are the
  controls, and any cap would be an arbitrary number that adds no specificity.

**Left to Ryan:**

1. Whether to merge and deploy the implemented candidate, or continue the
   no-code fallback (option 0): accept doctor exit 1 as a known FAIL until reboot.
2. The remaining PR/merge, promotion and live-use decisions in §10.1. Ryan
   already granted branch-only implementation; each later gate remains separate.
3. Whether an exit 0 that includes the acknowledged WARN satisfies the
   deployment's acceptance criterion (§10.1 step 7).
4. Whether this stays a priority-#1 sub-deliverable of Arc Codex, as drafted,
   or becomes its own arc with a STATUS file.

## 12. Residual risks and limits

- **A rewritten journal entry can strand an acknowledgment.** If the cursor
  changes (§5.2), the record goes inert and the FAIL returns; this is the safe
  direction, and the fix is a revoke and a fresh `ack`.
- **Same-user writes.** A process running as `lauer` can write the file. This
  is mitigated by visibility and attribution (§7), not prevented.
- **Unreadable evidence remains uncertain.** Blindness is WARN only when no
  retained FAIL contributor is detected. Acknowledgments are disabled on an
  incomplete read; this can restore an already acknowledged FAIL.
- **PID reuse within one boot can explain away an orphan dump.** This
  weakness already exists and is not changed here.
- **The acknowledgment does not:**
  - prove the hardware is healthy,
  - repair Timeshift,
  - validate the `13:03:52` replacement snapshot, or
  - supply Stage 1/Stage 2 or residual-burn evidence.

<!-- ref: ./EXECUTION-doctor-fault-acknowledgment.md, ./STATUS-codex-jsonl-production-integration.md, ../inter-model/KIRO-2026-10-22-doctor-fault-ack-design-review-handoff.md — execution plan, arc brief, review pickup -->
<!-- src: ../inter-model/CODEX-2026-10-22-doctor-ack-next-model-handoff.md, ../../cpu_tripwire.py, ../../doctor.py, ../../convmem.py, ../../tests/test_cpu_tripwire.py — event evidence and current behavior -->
<!-- src: ../builder-reference/ousterhout-builder-digest.md, ../builder-reference/hard-parts-builder-digest.md, ../builder-reference/zeller-builder-digest.md — design-it-twice, define errors out of existence, data ownership -->
<!-- src: /home/lauer/.codex/sessions/2026/10/22/rollout-2026-10-22T23-40-11-01a1670f-3005-75e0-8be1-f37f0c9d9955.jsonl — review findings and Ryan's takeover/reviewer assignment -->
