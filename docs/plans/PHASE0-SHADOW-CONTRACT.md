# Phase 0 Shadow Ledger Contract

**Who:** Cursor Execute of approved
[`EXECUTION-shadow-ledger-phase0.md`](EXECUTION-shadow-ledger-phase0.md).
**What:** Human-readable mirror of locked Architecture decisions for Phase 0.
**When:** Created during Execute (T1).
**Why:** Freeze the provisional envelope, activation rules, and non-authority
language before wiring sinks.
**How:** Implementers and VERIFY use this alongside Architecture; this document
is **not** a canonical observation-schema proposal and does **not** authorize
production activation.

## Authority

| Claim | Phase 0 status |
|---|---|
| Chroma `knowledge_units` | Tier-1 / authoritative |
| Shadow JSONL | Non-authoritative diagnostic / candidate evidence |
| Backup / restore source | Chroma-first unchanged; shadow is never a restore source |
| Cutover / schema freeze | Out of scope |
| Production activation | Separate Ryan grant after Execute + VERIFY |

## Configuration (disabled by default)

```toml
[shadow_ledger]
enabled = false
ledger_path = "~/.local/share/convmem/shadow_ledger.jsonl"
activation_manifest_path = "~/.local/share/convmem/shadow_activation.json"
health_path = "~/.local/share/convmem/shadow_health.json"
```

- Absent `[shadow_ledger]` ≡ `enabled = false` → no sink constructed or injected.
- `enabled = true` only permits an activation **attempt**; sink injection requires
  a complete matching activation manifest, valid shadow file identity, and exact
  resolved Chroma root match.
- Live `~/.config/convmem/config.toml` is not modified by this Execute arc.
- Shadow ledger and sidecars are mode `0600`.

## Activation baseline

Machine-readable activation manifest fields include: manifest version; unique
baseline ID; completion status; UTC activation timestamp; code commit; resolved
Chroma root and collection identity; active and total unit counts; per-entity
document/metadata/state hashes; configured vs observed embedding identity and
dimensions; shadow identity and starting sequence; hashing rules/version.

Incomplete manifests cannot enable the sink. Writes use temp → flush/`fsync` →
atomic rename → parent-directory `fsync`.

## Envelope (provisional)

Schema label: `shadow_schema_version` (Phase 0 uses `1`). Operations:
`create`, `replace`, `metadata_update`, `supersede`, `restore`, `delete`.
Hashes: SHA-256 over UTF-8 canonical JSON (`sort_keys=true`, compact separators,
no NaN). Raw embeddings never enter the ledger. Unknown embed provenance is
`UNVERIFIABLE`, never equality PASS.

## Scope of proof

Phase 0 proves **post-activation delta** for touched stable entity IDs only —
not historic corpus rebuild, migration readiness, or authority transfer.

## Stop / non-goals

No production read-path change; no Neutral/Office; no Restic/restore doctrine
change; no `conversation_summaries` shadowing; no quarantine-and-continue on
corruption (fail-closed).


## Strict validation API (C1)

Single shared entry point (implemented in `shadow_validation.py`):

```text
validate_shadow_activation(config_path, chroma_dir, mode)
  -> ShadowValidationResult(
       state, inject_eligible, activation_id, refusals, facts)
```

Modes: `writer`, `prepare`, `doctor`, `inventory`, `verify`. Mode selects
additional checks; it never changes the meaning of a refusal code. Refusals are
deterministic, deduplicated, stably ordered, redacted, and carry
`code` / `artifact` / `blocking` / `detail`.

Malformed manifests, corrupt ledgers, invalid counts/hashes/sequences, unsafe
paths, and permission failures never return `inject_eligible=true`. Production
writer wiring to this API is a later slice; C1 validates the contract directly.

### Path and permission policy (Ryan-resolved)

- Shadow artifacts live in a dedicated Shadow directory under the convmem data
  root.
- That directory is a sibling of, and outside, the Chroma root.
- Shadow directory ownership: effective production user; exact mode `0700`.
- The shared data-root parent is **not** required to be `0700`.
- Ledger, manifest, and health files: exact mode `0600`, regular files, link
  count one.
- Symlinked leaf or ancestor components are refused.
- Artifact paths and device/inode identities must be pairwise distinct.
- No Shadow artifact may be inside the Chroma root.
- C1 validation does not create or modify live directories or artifacts.

### Ledger identity header

Committed ledgers begin with a non-payload `ledger_header` JSONL record binding
`activation_id`, `ledger_identity`, schema version, UTC, and `starting_sequence`.
Events after the header must be contiguous starting at `starting_sequence + 1`.

## Secure ledger I/O (C2)

Header-only ledger creation (`create_shadow_ledger_header`) opens the private
`0700` Shadow parent with `O_DIRECTORY|O_NOFOLLOW`, creates the leaf with
`O_CREAT|O_EXCL|O_NOFOLLOW` mode `0600`, `fchmod`/`fstat`-verifies the
descriptor **before** any bytes, writes the C1 `ledger_header` record, then
fsyncs the file and parent. No mutation payload is written at create time.

`JsonlUnitMutationSink` does not create a missing ledger. Append opens an
existing private ledger, validates the header, allocates the next sequence from
a bounded header/tail read (no whole-ledger scan), appends one complete event
line, and measures the complete path through health-sidecar persistence.
Duplicate event IDs may appear as distinct contiguous sequences; replay keeps
the first valid occurrence. The 500 ms marker remains a degradation signal, not
an activation SLO.

## Activation transaction (C5)

C5 implements the merge-disabled activation and rollback mechanism. It does
not authorize a live activation, control services, mutate Chroma, or satisfy
the later C6 performance gate.

The durable state order is:

```text
disabled -> preparing -> quiesced -> baseline_captured
-> artifacts_validated -> committed -> first_event_observed -> verified
```

State skips are refused. Before the config commit, failures remain disabled;
after the config commit, failures compensate by disabling Shadow only. Chroma
writes are never reversed. A crash after nonce consumption but before config
commit is `prepared_not_committed` and requires activation-ID/path/inode-scoped
recovery under the exclusive writer gate.

### One-shot authorization

`shadow-activate` refuses without an exact current-user `0600` JSON token. The
token schema binds the operation, activation ID, nonce, issue/expiry timestamps,
code revision, config and artifact paths, writer census and gate paths, fixed
target config, the 300-second first-event window, the 30-second quiesce timeout,
the approved local filesystems, and named baseline/manifest derivations. Its
`request_hash` is SHA-256 over canonical JSON excluding `request_hash` itself.

The token is validated before gate acquisition and revalidated byte-for-byte
under the gate. Its lifetime cannot exceed 3600 seconds. The nonce is consumed
through a locked, append-only, current-user `0600` JSONL store and fsynced before
the config commit. No human or network wait occurs while the gate is held.

### Quiescence and commit

The implementation verifies a census generated for the exact runtime revision,
requires every listed service to already be inactive/failed, scans matching
`/proc` command lines and open Chroma file descriptors, and requires exact C3
PID/start-time/revision/protocol/executable attestation. It never stops or
starts services itself.

Two canonical baseline snapshots must match while the exclusive C3 gate is
held. The ledger and manifest are installed without replacing existing files.
The existing `[shadow_ledger]` TOML table is then replaced byte-preservingly;
all other parsed config must remain semantically identical. The temp and config
must be same-device on ext4, xfs, btrfs, or tmpfs. `os.replace`, file fsync, and
parent-directory fsync are required; network, unknown, and cross-device mounts
have no fallback. This config replacement is the sole commit point.

After release, the first real event must be sequence 1, hash-valid, and equal
to the successful Chroma post-state. Absence or mismatch within 300 seconds
causes an atomic disable while retaining ledger, manifest, journal, and the
explicit Shadow gap. Synthetic traffic requires separate authorization.

`shadow-rollback` only disables the exact activation ID. Its
`--recover-prepared` mode removes only journal-recorded artifacts whose current
device/inode identities still match. Both commands remain non-authority until
the separate C6 canary, review, and Ryan live-activation grant are complete.

## C6 scratch performance canary

C6 remains merge-disabled and is a measurement/evidence gate, not an
activation command. `shadow-canary` refuses unless the operator supplies a
new, private scratch directory, the intended ledger path, the production Chroma
root for overlap refusal only, a current read-only unit count, redacted
synthetic event lengths plus their evidence SHA-256, and refreshed
writer-census concurrency/open-frequency inputs plus their census SHA-256. It
never opens the production Chroma root for write, changes live configuration,
creates live Shadow artifacts, or activates Shadow.

The scratch directory must be new, `0700`, disjoint from both the intended
ledger and Chroma paths, and on the same mount ID, filesystem, and mount options
as the intended ledger parent. Each cell uses a disposable scratch Chroma root
and private Shadow ledger/health/config/manifest only. The cold-open measurement
uses the same strict writer validation API as production; steady append timing
uses the real sink after a scratch Chroma mutation. All documents are synthetic
length-controlled `x` data; no production payload is read or retained.

Ryan-approved C6 limits are:

```text
A_p99_ms=100          A_max_ms=500
D_p99_factor=2.0      O_p99_ms=500
R_p99_ms=300           R_factor=3.0
R_window=60 seconds with at least 100 complete samples
H_events=50,000
```

Every matrix cell requires three fresh runs, at least 100 untimed appends or
one second of warm-up (whichever produces more), and at least 1,000 timed
samples. The matrix covers 1 KiB/P50/P95/maximum synthetic event lengths,
header-only/N/2N/50,000-event ledgers, and one/census-peak/above-peak writers.
The report retains private raw timings and emits only redacted metrics:
lock wait, ledger append path, health persistence, complete append, throughput,
errors, cold-open percentile, and cumulative daily cold-open cost.

Any canary error, path/mount refusal, strict-validation failure, or breach of
the absolute/degradation/cold-open budget is a C6 FAIL and leaves Shadow
disabled. A later live performance rollback may occur only when a rolling
60-second window contains at least 100 complete append samples and its p99
exceeds 300 ms or its degradation exceeds 3.0x. Lower-volume windows are
telemetry-only; corruption, privacy, lost-event, and validation failures remain
immediate rollback conditions under the separately authorized activation flow.
