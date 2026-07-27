# Architecture Direction — Complete-data backup audit closure

**Source:** Ryan's Track 1 complete-data backup audit-closure assignment,
revised by the 2026-07-25 DeepSeek and Kiro assessments
**Authority:** Awaiting Ryan HITL; this document does not authorize
implementation or live rollout
**Planning date:** 2026-07-25
**Implementation base:** `origin/main` at
`1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7`
**Historical failed artifact:** PR #120 implementation commit
`492e6e7eacef6cfd64dfc5bb00b25296b5e29288`
**Consistency bar:** Hybrid, locked by Ryan on 2026-07-24
**Historical verdict authority:** Ryan's audit-closure handoff supplies the
corrected `A-FAIL / FAIL` verdict. The repository file
`docs/inter-model/COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md` is the
audit contract, not a filled verdict.

## Human consequence

If Ryan approves this direction, Cursor can implement a narrow correction that
prevents a newer wrongly tagged snapshot from false-greening local, offsite,
integrity, or restore claims; establishes a current-day local restore point
while the host is operating; validates complete restored state in isolation;
and removes the crash-during-truncate window in the derived JSONL export.

| | |
|---|---|
| **Who** | Codex owns this direction; Ryan owns approval; Cursor would implement only after approval; Kiro and Copilot review the new exact implementation SHA |
| **What** | Correct Track 1 complete-data Restic selection, daily coverage, restore validation, and JSONL crash atomicity |
| **When** | New correction from `origin/main` at `1ad9958…`; the failed `492e6e7…` remains historical evidence |
| **Why** | Tag-only downstream selection and incomplete restore validation can report protection for the wrong snapshot |
| **How** | One path-bound resolver, explicit snapshot IDs, verified copy lineage, an independent daily timer, a bounded restore preflight, and atomic export replacement |

## Problem statement

The failed implementation created complete-data snapshots tagged
`convmem-data-v1`, but only the local write gate consistently bound a snapshot
to the exact normalized `CONVMEM_DATA_ROOT`. Offsite copy, offsite doctor,
integrity, restore, and restore-drill surfaces could select by tag and recency
without proving the snapshot's recorded source path. A newer snapshot of
another root could therefore be copied, restored, or reported as current.

The same implementation did not provide an independent current-day local
snapshot trigger, a complete-data restore-and-reconcile procedure, or a
crash-atomic replacement for `knowledge_units.jsonl`. Broad repository-suite
success cannot prove these missing safety properties.

## System boundary

### In scope

- Correct complete-data snapshot selection in every safety-relevant consumer.
- Exact normalized source-path validation.
- Explicit snapshot-ID handoff and offsite source/destination lineage.
- Independent current-day local snapshot creation while the host is operating.
- Isolated complete-data restore validation and a durable report.
- A bounded reconcile and human-authorized replacement procedure.
- Crash-atomic replacement of the locked derived JSONL export.
- Migration for existing `restic.env` files without `CONVMEM_DATA_ROOT`.
- Focused negative controls and a fresh exact-SHA Hybrid audit.

### Out of scope

- Universal Tier-1 writer coordination or participation.
- Global quiescence, freeze/thaw, or a shared checkpoint protocol.
- Adding the Restic gate to every Chroma mutation.
- A general backup/storage-provider abstraction.
- Neutral Core, Office Team, or Shadow Ledger backup redesign.
- Shadow activation or promotion to restore authority.
- Live repository changes, snapshots, offsite copies, timer installation,
  Restic installation, or production replacement.
- Editing or attempting to rehabilitate `492e6e7…`.

## Invariants

1. A protection claim requires `convmem-data-v1` and exactly one recorded
   snapshot path whose normalized value equals normalized
   `CONVMEM_DATA_ROOT`.
2. `convmem-chroma` remains a compatibility tag but never proves complete-data
   coverage.
3. Safety consumers receive and use a full explicit snapshot ID. No consumer
   independently selects `latest --tag`.
4. Snapshot discovery never calls `restic snapshots --latest`. The resolver
   lists tagged snapshots as JSON, filters exact paths in Python, and sorts
   only validated candidates by timestamp.
5. A Restic copy has two identities: local source snapshot `S` and external
   destination snapshot `D`. Protection requires `D.original == S`; it never
   requires `D == S`.
6. A missing, stale, wrong-path, ambiguous, or unsupported state fails closed.
7. Timer ordering is an operational convenience, never a safety mechanism.
8. Restore validation occurs outside the live data root, performs no automatic
   repair, and persists reports outside the disposable run.
9. Canonical corruption blocks replacement. Derived drift is reported with a
   named repair source and must be repaired and revalidated separately.
10. The existing export flock remains held across the entire atomic JSONL
    replacement.

## Component ownership and interfaces

### `restic_snapshot.py` — authoritative Restic boundary

Add one Python module owned by ConvMem, not a provider framework.

```python
@dataclass(frozen=True)
class SnapshotRef:
    repository: str
    id: str
    original: str | None
    tree: str
    time: datetime
    paths: tuple[str, ...]
    tags: frozenset[str]

def resolve_snapshot(
    repository: str,
    *,
    expected_data_root: Path,
    required_tag: str = "convmem-data-v1",
    require_current_local_day: bool = False,
    requested_id: str | None = None,
) -> SnapshotRef: ...

def resolve_copy_destination(
    destination_repository: str,
    *,
    source: SnapshotRef,
) -> SnapshotRef: ...
```

Python consumers import the module. Shell consumers invoke its CLI and parse a
single JSON object. The CLI accepts repository/password/config inputs
explicitly and prints no secrets. It returns full 64-character IDs.

`resolve_snapshot()` runs the equivalent of:

```text
restic snapshots --json --tag convmem-data-v1
```

It does **not** pass `--latest`. It validates every candidate's paths before
sorting correct-path candidates by timestamp. This makes Restic 0.19.0's
`snapshots --latest` default-grouping regression irrelevant by construction.

When `requested_id` is supplied, the resolver validates that exact full ID
against the same path, tag, and optional freshness contract before returning
it.

`resolve_copy_destination()` requires exactly one destination snapshot whose
JSON `original` field equals `source.id` and whose normalized path, required
tag, timestamp, and tree equal the source. No match, multiple matches, or any
metadata mismatch fails closed.

### Restic version and capability contract

Minimum supported Restic version is **0.19.0**.

Restic 0.19.0 introduced snapshot filters and explicit IDs for `restic check`.
Restic 0.19.1 repaired a `snapshots --latest` grouping regression, but this
design never invokes `--latest`; requiring 0.19.1 would therefore add an
operational dependency without increasing safety.

Setup, doctor, and tests verify:

- semantic version `>= 0.19.0`;
- `restic check <full-id>` with `--read-data-subset` and `--read-data`;
- `restic restore <full-id> --verify`;
- snapshot JSON fields `id`, `original`, `tree`, `time`, `paths`, and `tags`;
- a real copied snapshot has a destination ID and `original == source ID`.

Behavioral tests remain mandatory even when the version string passes. There
is no fallback to tag/path integrity selection or to `snapshots --latest`.

### Shell and Python consumers

All of these surfaces use `SnapshotRef.id`:

- local snapshot gate;
- independent local daily service;
- offsite copy;
- offsite post-copy validation;
- offsite doctor;
- integrity check;
- restore command/helper;
- Chroma restore drill;
- complete-data restore preflight.

The existing `ensure_chroma_snapshot_for_live_write()` name remains as a
compatibility surface, but delegates selection to the authoritative resolver.

## Path normalization and safety

Filesystem paths use `expanduser()`, absolute conversion, and `realpath()`.
After normalization:

- the data root must exist and be a directory;
- `/` and the user's home directory are rejected;
- `CONVMEM_DATA_ROOT == CONVMEM_CHROMA_DIR` is rejected;
- the normalized snapshot path list must equal `[CONVMEM_DATA_ROOT]`;
- required durable paths must be contained by the data root;
- local repositories, the password file, and the data root must not overlap;
- the external local repository must not overlap the local repository or data
  root.

Local paths and `local:` repositories receive filesystem checks. Valid
`sftp:`, `rest:`, `s3:`, `b2:`, `azure:`, `gs:`, `swift:`, and `rclone:`
repository locators remain opaque and are not passed through `realpath()`.

If `CONVMEM_DATA_ROOT` is absent, normalize `CONVMEM_CHROMA_DIR`, derive its
parent, emit a migration warning, and apply the full safety contract. Setup and
the example environment write `CONVMEM_DATA_ROOT` explicitly. An explicit
data-root/chroma-dir equality never enters legacy derivation and fails closed.

## Data and control flow

### Local snapshot path

1. Resolve the newest current-local-day correct-path complete snapshot.
2. If none or stale, call the existing fail-closed snapshot script.
3. The script snapshots exactly the data root with both `convmem-data-v1` and
   `convmem-chroma`.
4. Re-resolve and return the explicit full ID.
5. If creation or re-resolution fails, preserve the resolver/Restic exit code
   and block the protected write.

Protected writes may create the snapshot earlier in the day. They do not
replace the independent timer and are not expanded to every writer.

### Offsite path

1. Resolve current correct-path local source `S`.
2. If the result is stale (`25`), wrong-path, or otherwise invalid, copy
   nothing and return the exact nonzero code.
3. Run `restic copy ... "$S"` against the external repository.
4. List destination snapshots and resolve `D` through `D.original == S`.
5. Verify equal tree, timestamp, exact normalized source path, and required
   tag.
6. Persist `S`, `D`, their relationship, command result, and validation in
   JSON and Markdown.

Repeated copies may be reported by Restic as already copied. They succeed only
if the same unique valid `D` is independently resolved afterward.

Offsite doctor performs the same local-source and destination-lineage
validation. It cannot claim current coverage from a tag-only destination.

### Integrity and restore path

The integrity command uses:

```text
restic check "<validated-full-id>" --read-data-subset=5%
```

The manual deep mode substitutes `--read-data`. It never reselects by tag or
path after resolving the ID.

Restore and both drills validate a requested ID before:

```text
restic restore "<validated-full-id>" --verify --target "<isolated-run>"
```

Repository mutation between selection and use cannot change the immutable ID.
Deletion or pruning during that interval makes the command fail closed.

## Independent daily local trigger

Add example user units with:

```ini
# convmem-restic-local.timer
OnCalendar=*-*-* 00:15:00
Persistent=true
RandomizedDelaySec=300

# convmem-restic-external.timer
OnCalendar=*-*-* 01/2:00:00
Persistent=true
RandomizedDelaySec=300
```

The local service invokes `scripts/restic-ensure-chroma-snapshot.sh`, which
creates or verifies the current-day complete snapshot.

`Persistent=true` runs the missed local event after the host resumes. The
current-day recovery-point claim applies while the host is operating or after
its first persistent catch-up; no snapshot can be claimed for a calendar day
during which the host never runs.

The external service may declare:

```ini
After=convmem-restic-local.service
```

This only orders the jobs when both are already queued. It neither pulls in the
local service nor proves success. The external command independently resolves a
current correct-path local snapshot. A stale result exits `25`, copies nothing,
and remains visible in the user-systemd failed state and journal. A later
external timer invocation retries normally.

## Bounded complete-data restore preflight

The preflight restores into a newly created disposable directory outside the
live root. Durable machine- and human-readable reports go under:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/convmem/backup-audit/
```

That report root must not overlap the restored run, data root, password file,
or either repository.

### Durable-state inventory

| State/path | Authority | Required for restore | Validator | Repair source | Failure class |
|---|---|---:|---|---|---|
| Configured Chroma directory; `knowledge_units`, `conversation_summaries` | Tier-1 authoritative | Yes | Open DB; collections; IDs, counts, pinned hashes, logical fingerprint | None | `BLOCKED` |
| `decisions-approved.jsonl` | Canonical decisions | Yes | Strict JSONL; schema/content hashes; unique IDs; approval linkage; byte hash | None | `BLOCKED` |
| `pending_decision_events.jsonl` | Canonical control state | Yes | Strict JSONL and lifecycle reducer against approvals | None | `BLOCKED` |
| `pending_decisions.jsonl` | Compatibility projection | Conditional | Parse and compare active proposals with event reducer | Pending event log | Repairable |
| `hash_schema_deploy.json`, `hash_schema_migration_report.json` | Canonical when referenced | Conditional | Schema/version and ledger-reference checks | None | Referenced invalid state is `BLOCKED` |
| `knowledge_units.jsonl` | Derived export | No | Strict JSONL; IDs, counts, hashes against Chroma | Chroma | Repairable |
| `processed.json` | Mixed incremental sidecar | Conditional | JSON/schema/path checks; distinguish hashes from exclusion markers | Source rescan for hashes; none for ambiguous exclusions | Ordinary drift repairable; malformed/ambiguous exclusions `BLOCKED` |
| `dedupe_queue.jsonl`, `link_queue.jsonl`, `ingest_duplicate_suppressions.jsonl` | Conditional operational control | Conditional | JSONL and referenced Chroma/unit identities | Chroma only where deterministic | Unrecoverable pending intent `BLOCKED`; stale derived rows repairable |
| `inventory.jsonl`, configured `imports/**` | Source inventory/cache | Conditional | JSONL, configured-path hashes; SQLite `quick_check` | Source rescan/reimport | Corrupt configured sole source `BLOCKED`; stale inventory repairable |
| `authorizations/r2b/**` | Conditional authorization control | Conditional | Manifest, sidecar hash, status, grant/quarantine state | None | Invalid active grant `BLOCKED`; historical/quarantined residue advisory |
| `refine_undo/**/*.jsonl`, `attempts.jsonl`, `index_failures.jsonl`, `synthesis_failures.jsonl` | Operational evidence | No | Parse and inventory | None | Advisory unless active control references it |
| Configured Shadow ledger, activation manifest, health sidecar | Non-authoritative Phase 0 | Only when enabled | Existing manifest identity/root contract, JSONL integrity, health schema | Never a restore source | Disabled/absent valid; invalid active control `BLOCKED`; degraded health advisory |
| Lock files and `worktrees/**`, `restore-drill/runs/**` | Ephemeral/scratch | No | Confirm scratch exclusions; ignore inert lock files | None | Scratch presence fails coverage proof |

Every validator is confined to this matrix. An unknown top-level durable path
produces `BLOCKED_UNCLASSIFIED_STATE`; it does not silently become a restore
authority or trigger an open-ended validator expansion.

### Shadow Phase 0

Current `main` keeps Shadow disabled by default. Its ledger, activation
manifest, and health sidecar may be inside the complete data root, but remain
non-authoritative.

- Missing or disabled Shadow configuration does not block `VALID`.
- Inactive files are inventoried; malformed inactive residue is advisory.
- Enabled Shadow requires the existing complete activation manifest, ledger
  identity, health schema, and expected original Chroma root.
- The manifest's recorded Chroma root is compared with the snapshot's original
  expected path, not the disposable restore path.
- Invalid active configuration/control state blocks replacement.
- Degraded-but-valid health is advisory.
- Shadow never repairs Chroma, ledgers, exports, or queues.

### Classification and action

- `VALID`: persist the report. Production replacement still needs a separate
  Ryan grant.
- `VALID_WITH_REPAIRABLE_DERIVED_DRIFT`: do not replace production. Repair only
  the staged copy from the matrix's named source, record the action separately,
  and rerun from the original snapshot until a clean `VALID` exists.
- `BLOCKED`: do not repair canonical state automatically and do not replace
  production. Retain or discard the isolated run for investigation.

The documented cutover procedure requires a separate live authorization,
stops ConvMem processes for the one-time replacement window, preserves the
pre-cutover root, replaces authoritative state first, regenerates derived
state only from named sources, reruns doctor/preflight, and rolls back to the
preserved root on failure. This is an operator procedure, not new universal
freeze/thaw infrastructure.

## Crash-atomic JSONL replacement

`observe.py::_upsert_jsonl_line()` keeps the existing export flock around:

1. Create a sibling temporary file with exact prefix
   `.<destination>.convmem-upsert.` and suffix `.tmp`.
2. Preserve malformed-line retention, append-if-not-found behavior, UTF-8
   encoding, newline bytes, and the existing destination mode.
3. Write the complete replacement, flush, and `fsync` the file descriptor.
4. Atomically publish with `os.replace()`.
5. `fsync` the parent directory.
6. On a caught pre-replace failure, remove only that invocation's temporary
   file.

No glob cleanup or automatic scavenger is added. An abrupt process death may
leave an inert, exactly prefixed sibling file; readers continue to observe the
previous complete destination.

## Failure semantics

| Exit | Meaning |
|---:|---|
| `0` | Valid selection or completed operation |
| `10`, `11`, `12` | Restic repository, lock, or password failures; preserve unchanged |
| `20` | Invalid or unsafe configuration/path layout |
| `21` | Restic unavailable, below 0.19.0, or missing required capability |
| `22` | Repository invocation or snapshot JSON failure |
| `23` | No `convmem-data-v1` snapshot |
| `24` | Tagged snapshots exist but none matches the exact data root |
| `25` | Correct-path snapshot exists but is stale |
| `26` | Requested ID is absent, abbreviated, ambiguous, or invalid |
| `27` | Destination lineage is absent, ambiguous, or inconsistent |
| `28` | Snapshot, copy, check, or restore action failed outside reserved Restic codes |
| `29` | Durable report could not be written |
| `30` | `VALID_WITH_REPAIRABLE_DERIVED_DRIFT`; not replacement-ready |
| `31` | `BLOCKED` by canonical/control corruption |
| `32` | Restore isolation or validator-internal failure |

Shell and Python wrappers preserve these codes. `convmem doctor` retains its
aggregate command status while reporting the underlying backup code verbatim.
An unconfigured offsite repository may remain an explicit successful
`SKIP_DISABLED`; a configured reachable repository with stale or invalid local
coverage must not silently skip.

## Hybrid Five-part positioning

This correction targets Hybrid bar A. It does not imply Universal Tier-1
closure.

| Dimension | Expected new-SHA score | Basis |
|---|---|---|
| 1. Tier-1 writer census | `PASS` | Execution inventories all durable/derived mutators and classifies authoritative vs reconstructable output |
| 2. Universal snapshot participation | `NOT CLAIMED` | Universal writer gating is explicitly out of scope |
| 3. Snapshot-safe persistence boundary | `NOT CLAIMED` | No global checkpoint/freeze protocol is introduced |
| 4. Adversarial concurrency tests | `NOT CLAIMED` | Focused crash/reconcile tests do not prove universal prohibited mixes |
| 5. Isolated restore invariants | `PASS` | Complete-data preflight validates canonical bytes, Chroma, relationships, queues, markers, and classifications without the live root |

Open Five-part dimensions do not excuse an A-bar data-loss or false-green path.
Any such unresolved path remains overall `FAIL`.

## Options considered

| Option | Decision | Reason |
|---|---|---|
| Keep tag-only `latest` and add more tests | Rejected | Selection remains path-blind and duplicated |
| Use `snapshots --latest` with Restic 0.19.1 | Rejected | Unnecessary dependency; list/filter/sort in Python is simpler and immune to the regression |
| Duplicate selection in shell and Python | Rejected | Semantics would drift across consumers |
| Require source and destination IDs to match | Rejected | Restic copy creates a distinct destination snapshot |
| Make timers depend on ordering | Rejected | `After=` neither pulls in nor proves success |
| Gate every writer or add global quiescence | Rejected | Outside Track 1 and not required for Hybrid A |
| Automatically repair restored state | Rejected | Can hide canonical corruption and turn validation into mutation |
| Generalize to arbitrary backup providers | Rejected | Adds surface without closing a Track 1 blocker |

## Test strategy

- Unit-test normalization, remote/local repository handling, version/capability
  checks, explicit-ID validation, exit codes, and lineage.
- Use an actual Restic 0.19.0+ binary in a temporary harness.
- Create an older current-day correct-path snapshot and a newer current-day
  wrong-path snapshot.
- Assert the discovery argv contains no `--latest` and the resolver selects
  the correct-path snapshot.
- Extend that fixture through every consumer.
- Prove copied destination JSON uses `original`, records both IDs, and retains
  tree/time/path/tag.
- Exercise all seven base negative controls.
- Fault-inject JSONL write, flush, file `fsync`, and pre-replace failures.
- Exercise every restore matrix classification and Shadow state.
- Sentinel-check that no live root, live local repository, removable
  repository, timer, or configuration changes.

## Migration, rollout, and rollback boundaries

- Existing repositories need no format migration.
- Historical Chroma-only snapshots remain readable but cannot establish
  complete protection.
- Existing env files derive the parent of `CONVMEM_CHROMA_DIR` with a warning;
  operators later add `CONVMEM_DATA_ROOT` explicitly.
- Restic 0.19.0 already satisfies the minimum on the planning host; setup and
  doctor still verify capabilities on every target.
- Code, examples, and documentation may merge without installing units or
  touching repositories.
- Timer installation, live snapshot creation, offsite copy, and replacement
  each require later Ryan authorization.
- Code rollback may restore the prior scripts, but the old tag-only behavior
  must not be represented as current complete protection.

## Decision evidence

- Restic 0.19.0 added filtered and explicit-ID `check`:
  <https://github.com/restic/restic/releases/tag/v0.19.0>
- Restic 0.19.1 fixed the `snapshots --latest` default-grouping regression
  that this resolver avoids:
  <https://github.com/restic/restic/releases/tag/v0.19.1>
- Restic copy creates a destination snapshot distinct from its source:
  <https://restic.readthedocs.io/en/stable/045_working_with_repos.html#copying-snapshots-between-repositories>
- Restic snapshot JSON records lineage in `original`:
  <https://github.com/restic/restic/blob/master/doc/design.rst#snapshots>
- Current Shadow Phase 0 authority and activation rules:
  [`PHASE0-SHADOW-CONTRACT.md`](PHASE0-SHADOW-CONTRACT.md)

## Downstream handoff

The companion execution and VERIFY documents are:

- [`EXECUTION-complete-data-backup-audit-closure.md`](EXECUTION-complete-data-backup-audit-closure.md)
- [`VERIFY-complete-data-backup-audit-closure.md`](VERIFY-complete-data-backup-audit-closure.md)

Ryan must approve this Architecture Direction and the Execution Plan before
Cursor receives implementation authority.

Active phase lane must stop here. Await HITL.
