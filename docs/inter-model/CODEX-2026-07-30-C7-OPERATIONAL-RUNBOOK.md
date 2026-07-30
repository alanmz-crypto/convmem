# C7 operational runbook — writer census

**Author:** Codex planning lane (reassigned from Kiro)  
**Reviewed implementation:** merged `main` `869aec7431b600ed7602a7a64ff98502340be066` (C7 writer-census)  
**Status:** Runbook only. It does not authorize C7 arm, C6, or Shadow activation.

## Purpose and boundary

C7 collects seven complete UTC days of payload-free writer-session evidence.
Its final private report is the sole source of C6 writer concurrency and
open-frequency inputs. C7 does not enable Shadow, create Shadow artifacts, or
write Chroma.

The C6 event-size-evidence policy remains separately held. A valid C7 report
does not authorize C6 or activation.

## 1. Deployment proof — Ryan must perform on the production host

Run from the deployed checkout that production writers actually import, not a
worktree or a remote-tracking ref:

```bash
git rev-parse HEAD
git show HEAD:writer_census.py >/dev/null
git show HEAD:chroma_write_store.py | rg 'record_writer_open|record_writer_close'
python -B -c 'from chroma_write_store import WRITER_GATE_PROTOCOL_VERSION; print(WRITER_GATE_PROTOCOL_VERSION)'
python -B -c 'import config as c; from pathlib import Path; cfg=c.load_config(c.CONFIG_PATH); print(Path(cfg["index"]["chroma_dir"]).expanduser().resolve())'
python -B -c 'from chroma_write_store import DEFAULT_WRITER_LOCK; print(DEFAULT_WRITER_LOCK.expanduser().resolve())'
```

Required result: the deployed revision contains C7; the protocol, canonical
Chroma root, and canonical writer-gate path are recorded in the operator
evidence. The deployed revision must remain unchanged through report creation.

Before arm, run the existing C3 writer census from that same deployed checkout:

```bash
python -B -c '
from chroma_write_store import generate_writer_census, classify_legacy_writer_pids
census = generate_writer_census()
print(census)
print(classify_legacy_writer_pids(census["open_fd_writer_pids"]))
'
```

Proceed only when no legacy/unattested writer refusal is returned. A local or
sandboxed process scan cannot prove another host's writers; it is not a
substitute for this production-host check.

## 2. Pre-arm decision

Confirm Shadow remains disabled and inspect, but do not delete, any existing
census path:

```bash
convmem doctor
ls -ld ~/.local/share/convmem/writer-census 2>/dev/null || true
```

`writer-census-start` takes the C3 **exclusive** writer gate for at most 30
seconds before it creates the census header and journal. It does not control
services. A successful arm creates a `0700` census directory with these `0600`
files:

- `census-header.json`
- `session-events.jsonl`
- `census-status.json`

Ryan alone may arm C7 after the deployment proof and a separate authorization:
Use the canonical Chroma path printed in Section 1 as `--chroma-root`; the
path below is only the current default.


```bash
python convmem.py writer-census-start \
  --chroma-root ~/.local/share/convmem/chroma
```

Expected result is JSON with `"verdict":"ARMED"`, the exact revision,
protocol, hashed Chroma/gate identities, and `window_start_utc` /
`window_end_utc`. The window begins at the next UTC midnight and ends seven
complete UTC days later.

Stop on any refusal, especially `writer_quiesce_timeout`, `census_revision_mismatch`,
`census_permission_invalid`, `census_owner_invalid`, `census_symlink_refused`,
`census_path_unsafe`, or `census_telemetry_write_failed`. Do not delete or
repair an existing census artifact to retry; inspect and classify it first.

## 3. Observation rules

For the entire observation interval:

- Keep the exact deployed Git revision unchanged. C7 validates its runtime
  revision at every recorded writer open and close.
- Keep the C3 protocol, canonical Chroma path, and writer-gate path unchanged.
- Do not hand-edit, move, copy, change permissions on, or delete census files.
- Keep Shadow disabled. Do not attempt C5 activation.
- Do not stop, restart, or otherwise control services as a census operation.

The only permitted observation command is read-only:

```bash
python convmem.py writer-census-status
```

It returns the immutable header, event count, and current UTC time. The status
file itself is not an operational source of truth; header plus journal are.

Before the first UTC boundary, C7 records opens to establish the armed state,
but excludes them from daily-open counts. After `window_end_utc`, new sessions
create no census event. A session opened before the end still needs its normal
close record. Wait for those tail sessions to finish naturally; do not stop a
service to force closure.

## 4. Final-report decision

After `window_end_utc`, first run the read-only status command. If the census
has unmatched pre-end opens, wait and try later. Then Ryan may run:

```bash
python convmem.py writer-census-report
```

The command validates contiguous sequence numbers, event pairing, the runtime
revision/protocol, and the elapsed seven-day window. It writes one private
`census-report.json` only after these checks pass.

Result handling:

| Signal | Meaning | Action |
|---|---|---|
| `census_window_incomplete` | Window has not elapsed. | Wait; no artifact is written. |
| `census_incomplete` | A pre-end open has no durable close yet. | Wait for natural close; if impossible, discard this census as unusable. |
| sequence/pair/corruption/privacy refusal | Evidence cannot be trusted. | Hold; do not repair the journal; begin a fresh authorized census only after root cause review. |
| `PASS` | Report was written. | Capture identity evidence and request independent review. |

On `PASS`, capture without exposing journal contents:

```bash
sha256sum ~/.local/share/convmem/writer-census/census-report.json
stat -c '%a %U %n' ~/.local/share/convmem/writer-census/census-report.json
python -B -c '
import json
from pathlib import Path
report=json.loads(Path("~/.local/share/convmem/writer-census/census-report.json").expanduser().read_text())
assert report["payloads"] == "none"
for key in ("code_revision", "writer_gate_protocol", "chroma_root_identity", "writer_gate_identity", "max_concurrent_writer_sessions", "conservative_short_lived_opens_per_day"):
    print(f"{key}={report[key]}")
'
```

The independent reviewer must name the exact report SHA-256 and confirm: file
mode/owner, no payload-bearing fields, revision/protocol/root/gate bindings,
seven-day interval, and plausible aggregate writer metrics. This report is
then the only permitted C6 source for writer concurrency and open frequency.

## 5. C6 boundary and stop conditions

C7 completion does **not** authorize C6. Before a C6 request, Ryan still needs:

1. an independent C7 evidence PASS naming the report SHA-256;
2. a separately approved payload-free source of fresh event-size evidence;
3. a fresh read-only unit count;
4. a new private scratch directory on the intended-ledger mount; and
5. a separate, named C6 authorization.

Do not use or create a live Shadow ledger to generate event-size evidence.
That question is explicitly held for policy/architecture review.

## Ryan may proceed / must stop

| Gate | May proceed when | Must stop when |
|---|---|---|
| C7 arm | deployed C7 proof, no legacy writer refusal, Shadow disabled, separate Ryan authorization | deployed identity cannot be proven; census artifacts unsafe or pre-existing without review |
| Observation | exact revision/root/gate/protocol remain frozen | any bound identity changes or journal/privacy integrity issue |
| Report | seven days elapsed and all pre-end opens closed | report refuses for corruption, pairing, privacy, revision, or protocol |
| C6 request | independent C7 PASS and all five C6 boundary inputs exist | event-size-evidence policy remains unresolved or any evidence is stale |
| Activation | never from this runbook | always requires later, separate authorization |

## Verdict

```text
C7 OPERATIONAL RUNBOOK READY
```

The C7 operational path is mechanically grounded in merged code. C6 remains
held on the separate event-size-evidence policy decision.
