# Architecture — R2b capture authorization

**Date:** 2026-07-20  
**Decision:** Option A — phase-scoped `authorization_phase: "r2b"`  
**Status:** Proposed architecture; implementation and live capture remain unauthorized  
**Supersedes:** [PR #64](https://github.com/alanmz-crypto/convmem/pull/64)

```
Planning Status

Phase:        Architecture Planning (Ryan HITL required)
Characters:   Architect, Scope Guardian, Risk Reviewer
Functions:    Planner
Lanes:        Codex (docs); Cursor (later implementation); Copilot + Kiro (later review)
Authority:    Docs PR only — merge is not an R2b execution grant
```

**Execution plan:** [`EXECUTION-2026-07-20-r2b-capture.md`](EXECUTION-2026-07-20-r2b-capture.md)  
**Verify plan:** [`VERIFY-r2b-capture.md`](VERIFY-r2b-capture.md)  
**Gate 1 harness pin:** `3b2790f50414f0445c35748e52f849c6276839f7`

---

## Decision and compatibility boundary

Choose **Option A**: real R2b capture uses a distinct
`authorization_phase: "r2b"` schema. Reject the placeholder/pre-image design.
`corpus_package_sha256`, `unit_corpus_fingerprint`, and other Gate 2 products
do not exist before capture and therefore cannot honestly authorize R2b.

This is an intentional compatibility break: after the implementation lands,
every `execution_mode == "real"` manifest whose operations contain `capture`
must be R2b and capture-only. The global real schema remains unchanged for
non-capture operations, and R2a remains unchanged.

The architecture follows the existing R2a pattern for consistency, with a
separate binder-issued capability and write-time approval re-verification. It
also makes completion a single, objectively testable property: a valid final
marker, not an operator-facing status string.

### Options considered

| Option | Result | Reason |
|--------|--------|--------|
| A — phase-scoped R2b schema | **Chosen** | Represents only facts available before capture; keeps R2a and global real validation intact |
| B — pre-image placeholders | Rejected | Makes approved fields knowingly untrue and requires a second authority record to reinterpret them |

### Architectural invariants

1. Approval authorizes one exact capture, not a directory or a reusable retry
   loop.
2. No eval-root create or replace is possible from caller-constructible
   `AuthContext`, runtime path equality alone, or a plain `bind_capture` result.
3. The approved manifest and sidecar are the source of truth. Capability fields,
   CLI arguments, and caller-provided snapshots are never independent sources of
   authorization.
4. Source identity is recomputed by trusted code before capability minting and
   at execution. Stable Chroma IDs are insufficient; captured content is bound.
5. A capture is structurally complete only when the last atomic marker validates
   every required prior artifact and the exact inventory.
6. Failure, drift, or interruption never produces a completion marker. Partial
   directories are quarantined; retry requires a fresh directory and grant.

---

## R2b manifest schema

### `REQUIRED_R2B_FIELDS`

| Field | Exact rule |
|-------|------------|
| `authorization_phase` | Exactly `"r2b"` |
| `execution_mode` | Exactly `"real"` |
| `status` | Exactly `"approved"` |
| `operations` | Exactly `["capture"]` |
| `run_id` | Required top-level string satisfying the safe-ID rules below |
| `merged_harness_sha256` | Exactly `3b2790f50414f0445c35748e52f849c6276839f7` |
| `paths` | Object with exactly `export`, `processed`, `capture_dir`, `chroma_dir` |
| `service_policy` | Exactly `"no_service_changes"` |
| `prohibited_actions` | List containing the full minimum set below |
| `source_snapshot` | Object satisfying the complete schema below |

As with R2a, `ryan_approved_manifest_sha256` is outside the required-field
tuple but is mandatory. It must equal the canonical approved-body SHA-256 and
the one-line adjacent sidecar at `<manifest>.approved.sha256`.

R2b must **not** require pre-capture `corpus_package_sha256`,
`unit_corpus_fingerprint`, query, uncertainty, build, comparison, model, or
Gate 2 fields.

### Prohibited actions

`prohibited_actions` must contain all of:

```text
config_generation
adjudicate
baseline_build
challenger_build
compare
model_exec
model_execution
promote
cleanup_external
```

Additional prohibitions are permitted. `operations` remains exactly
`["capture"]`; the prohibited list is defense in depth, not an alternative
allowlist.

### `source_snapshot`

| Field | Rule |
|-------|------|
| `export_sha256` | Lowercase 64-hex SHA-256 of the export bytes |
| `processed_state` | Exactly `"present"` or `"absent"` |
| `processed_sha256` | Lowercase 64-hex when present; `null` when absent |
| `chroma_collection_name` | Nonempty string |
| `chroma_collection_id` | Nonempty, non-null collection identity for real R2b |
| `chroma_extracted_unit_count` | Nonnegative integer for the full extracted set, including superseded IDs |
| `chroma_sorted_id_hash` | Canonical ID-set SHA-256 defined below |
| `chroma_capture_slice_sha256` | Canonical collection + ID + document + superseded-state SHA-256 defined below |
| `snapshot_timestamp` | Timezone-aware ISO-8601; not in the future; no older than one hour at ACCEPT, binder execution, and materialization |

`paths.processed` is always present even when `processed_state == "absent"`.
In that state, the named source and captured `processed.json` must both remain
absent. An empty synthesized `processed.json` is not equivalent to absence.

If the operator claims the snapshot and packet draft were produced in one
operator session, the packet must carry a body-bound
`snapshot_session_evidence_id`. That claim is procedural evidence, not a
substitute for the structural recomputation, content digests, or age gate.

---

## Canonical Chroma source identity

Count plus ID-set hash cannot detect a changed document or superseded flag
under stable IDs. Snapshot generation and capture extraction must therefore use
one shared canonicalization helper and one read-only transaction.

The **extracted set** has the same membership semantics as today's
`extract_chroma_capture_slice`: every ID observed with a captured document or
superseded metadata row, including superseded IDs. It is not described as an
"active" count.

The helper must:

1. Read the collection name and persistent collection ID.
2. Read every extracted ID, whether a document is present, the exact document
   string, and the effective boolean superseded state.
3. Reject IDs containing CR or LF so the required newline-delimited ID hash is
   unambiguous.
4. Sort records by the UTF-8 bytes of the ID, never by Chroma return order.
5. Compute `chroma_sorted_id_hash` over each sorted UTF-8 ID followed by one
   `\n`, including a terminal newline for every record.
6. Compute `chroma_capture_slice_sha256` over canonical UTF-8 JSON containing:
   the collection name and ID; and, for each sorted record, `id_utf8_hex`,
   `document_present`, `document_utf8_hex`, and `superseded`. Canonical JSON uses
   `ensure_ascii=False`, sorted object keys, and separators `(",", ":")`.

Hex encoding makes the document-byte boundary explicit and distinguishes a
missing document from an empty document. The same helper must produce the
pre-approval snapshot, the capture extract, and the post-capture comparison.
Hermetic tests must pin Unicode ID byte-ordering, empty versus missing
documents, superseded rows, and collection-ID changes.

The source-snapshot digest stored in the completion marker is SHA-256 of the
approved `source_snapshot` object serialized with the same canonical JSON
rules. The authorization-body digest uses the existing
`canonical_manifest_body_sha256` contract.

---

## Validation precedence

Validation must reject malformed `operations` before membership testing:

```text
if execution_mode == "real":
    if operations is missing or not a list:
        reject
    if "capture" in operations:
        require authorization_phase == "r2b"
        require operations == ["capture"]
        validate_r2b_manifest_schema(...)
    elif authorization_phase == "r2a":
        validate_r2a_manifest_schema(...)
    elif authorization_phase == "r2b":
        reject
    else:
        validate REQUIRED_REAL_FIELDS
```

Consequences:

- A real manifest cannot mix `capture` with another operation.
- A real capture cannot use R2a or the global real schema.
- An R2b manifest without capture is invalid.
- Malformed or absent `operations` fails closed rather than throwing a Python
  membership/type error.
- Non-R2b real validation is not weakened.

---

## Safe `run_id` and path containment

`run_id` must match:

```text
^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$
```

Empty strings, `.`, `..`, path separators, and control characters are rejected
even if another check would also reject them.

Define:

```text
EVAL_ROOT = ~/.local/share/convmem/eval
AUTH_ROOT = ~/.local/share/convmem/authorizations/r2b
```

For real R2b:

- The manifest path is canonically
  `AUTH_ROOT / run_id / "capture.json"`; its parent resolves exactly to
  `AUTH_ROOT / run_id`.
- The sidecar is exactly `capture.json.approved.sha256` beside it.
- `paths.capture_dir` is canonically
  `EVAL_ROOT / run_id / "capture"` and resolves to exactly that path.
- The resolved capture path and authorization layout each contain a path
  segment byte-equal to the top-level `run_id`.
- Packet source paths are absolute canonical lexical strings. `~`, `.`, `..`,
  redundant separators, and alternate spellings are rejected.
- Runtime path strings must be byte-equal to the packet strings **and** resolve
  to the approved targets. This lexical equality is a new requirement; today's
  `_bind_paths_and_scalars` performs normalized/resolved comparison only.
- No bound path, manifest, sidecar, existing source, or existing parent of an
  absent target may contain a symlink component at bind or materialization.
- `capture_dir` must not exist before materialization. Pre-creating an empty
  directory does not satisfy write-once authorization.

Wrong or swapped `run_id` therefore fails even if someone hand-edits path
strings to point somewhere that otherwise resolves.

---

## Trusted snapshot and staleness gates

Caller-supplied runtime equality is not authorization. The trusted sequence is:

1. `restic_gate: PASS` occurs before any snapshot computation and before any
   eval-root capture write.
2. Trusted snapshot code reads the approved paths and produces the draft
   `source_snapshot` in the same operator session as the packet draft.
3. Ryan ACCEPT occurs only while the timezone-aware timestamp is at most one
   hour old. A future or naive timestamp fails. Any source byte/identity change
   before ACCEPT requires recomputation and a new packet digest.
4. `bind_r2b_capture` independently rejects a future, naive, or more-than-one-
   hour-old approved timestamp at bind time, then recomputes the actual snapshot
   and compares it to the approved manifest before minting a capability.
5. `materialize_r2b_write_authorization`, immediately before `capture_dir`
   creation, rechecks timestamp age, approval, bindings, source identity,
   containment, symlinks, and target absence.
6. `run_capture` compares the copied export/processed state and canonical Chroma
   slice to the approved snapshot, then recomputes final live source state
   before publishing the completion marker.

The one-hour rule applies at ACCEPT, binder execution, and materialization. It
is a staleness bound, not identity proof; matching trusted digests provide the
identity proof.

---

## Write authorization and capability chain

R2b mirrors the hardened R2a capability design:

| Piece | R2b contract |
|-------|--------------|
| Capability | Opaque, immutable, exact-type `_R2bCapability`; HMAC seals resolved manifest path + approved-body digest |
| Binder | `bind_r2b_capture` is the only mint path |
| Plain binder | `bind_capture` refuses `authorization_phase == "r2b"`; it remains fixture/non-R2b only |
| Consumer | `run_capture(..., r2b_capability=capability)` |
| Write gate | `materialize_r2b_write_authorization` runs before `capture_dir.mkdir()` or any eval-root temp/write |

Required call chain:

```text
approved R2b manifest + sidecar
  -> bind_r2b_capture (trusted snapshot recompute)
  -> opaque _R2bCapability
  -> run_capture(..., r2b_capability=capability)
  -> materialize_r2b_write_authorization
  -> first capture_dir creation/write
```

At materialization, authenticate the exact capability type and HMAC; re-read
the sealed manifest; re-verify its sidecar and in-file digest; revalidate the
R2b schema and operation; and re-derive every path, scalar, fixed control, and
source snapshot from the approved body. Capability/grant fields are never the
source of truth.

`run_capture` must reject any eval-root create or replace without that
capability. The CLI currently calls `assert_capture_authorized`, discards the
return, and invokes `run_capture` directly; the implementation PR must replace
that gap with the chain above. Direct library callers are subject to the same
write gate.

---

## Fixed execution controls

Real R2b has no evidence-affecting caller knobs:

| Control | Required value |
|---------|----------------|
| `capture_id` | Exactly `run_id` |
| `overlap_policy` | Exactly `canonical` (40/30/30) |
| `spot_check_n` | Exactly `20` |
| `max_attempts` | Exactly `1` |

The R2b CLI must refuse `--max-retries` values other than `1`, or remove/ignore
the flag and force one attempt. The exact authorized command uses
`--max-retries 1` while that flag remains. `capture_id` is derived internally;
it is not randomly generated or accepted from the caller.

An internal retry in the same directory would violate quarantine and grant
semantics. Any failure requires a new `run_id`, absent `capture_dir`, fresh
snapshot, packet, ACCEPT, and grant.

---

## Completion marker and write order

Today `build_corpus_package` writes `corpus_package_manifest.json` in the middle
of the pipeline. Under R2b, that filename becomes the expanded completion
marker and is written **last and atomically**.

### Required write order

```text
materialize authorization
  -> create capture_dir
  -> export/optional processed copies
  -> canonical Chroma extract + documents
  -> corpus_package.jsonl
  -> overlap_validation.json
  -> historical_spot_check.json
  -> required capture_report.json
  -> final live source-drift check
  -> corpus_package_manifest.json (completion marker; last atomic write)
  -> no further artifact mutation
```

Early `FAILED` reports remain useful operator evidence, but no FAILED, drift,
exception, or interrupted path may publish the marker. The marker may be
published only after a structurally complete `CAPTURE_COMPLETE` or
`UNRESOLVED` outcome.

### Marker schema (minimum)

```text
marker_version: 1
status: "CAPTURE_ARTIFACTS_COMPLETE"
capture_outcome: "CAPTURE_COMPLETE" | "UNRESOLVED"
run_id: <approved run_id>
capture_id: <same value as run_id>
authorization_body_sha256: <approved canonical body digest>
source_snapshot_sha256: <canonical approved source_snapshot digest>
processed_state: "present" | "absent"
package_sha256: <corpus_package.jsonl digest under existing package contract>
unit_corpus_fingerprint: <fingerprint>
unit_count: <integer>
artifact_inventory: <sorted exact relative-path list, including this marker>
artifact_sha256: <relative path -> SHA-256 for every required non-marker artifact>
```

The marker cannot hash its own bytes without a circular preimage. Therefore
`artifact_inventory` includes `corpus_package_manifest.json`, while
`artifact_sha256` covers every required artifact **except the marker itself**.
It must include at least:

```text
knowledge_units.jsonl
chroma_extract.json
chroma_documents.json
corpus_package.jsonl
overlap_validation.json
historical_spot_check.json
capture_report.json
```

When `processed_state == "present"`, both inventory and digest map also include
`processed.json`. When absent, that path must not exist. No other file,
directory, symlink, or leftover temporary path is allowed.

Marker validation requires:

- exact schema, approved IDs/digests, and fixed outcome set;
- exact conditional inventory, with no extras or omissions;
- every non-marker artifact digest matching current bytes;
- report presence and hash, with report outcome equal to `capture_outcome`;
- package digest, fingerprint, unit count, and source/authorization bindings
  agreeing across marker and bound artifacts; and
- marker publication as the last artifact write, with no write after it.

Hermetic implementation tests must instrument atomic-write order. On-disk
VERIFY also checks that no artifact has a modification time after the marker,
but hashes and exact inventory are the authoritative post-run checks.

### Report and exit semantics

`capture_report.status` keeps its existing enum and outcome assignment:
`CAPTURE_COMPLETE`, `FAILED`, or `UNRESOLVED`. It remains required operator
evidence and is hash-bound by the marker, but it is not the completeness
authority.

- `CAPTURE_COMPLETE`: marker required; CLI exit `0`.
- `UNRESOLVED`: marker required; CLI may retain nonzero exit `1` as an operator
  signal. That exit does not make the artifact set structurally incomplete.
- `FAILED`, source drift, or exception: no marker; nonzero exit.

This resolves the prior exit-code contradiction: VERIFY evaluates structural
completion from the marker, while recording the outcome/exit mapping
separately. A marker without `capture_report.json` is invalid and incomplete.

---

## Path access table

| Path | Access and invariant |
|------|----------------------|
| `AUTH_ROOT / run_id` | Read-only after approval; exact manifest + sidecar; no symlink components |
| `paths.export` | Read-only; byte identity bound by trusted snapshot and copy/final checks |
| `paths.processed` | Read-only when present; exact absence bound pre/post when absent |
| `paths.chroma_dir` | Read-only extraction; validate existing directory only; never create or mutate |
| `EVAL_ROOT / run_id / capture` | Write-once; must not exist before materialization; no symlinks; exact inventory only |
| Live config under `~/.config/convmem` | Never written by R2b |

---

## Failure classes and recovery

| Failure class | Required result |
|---------------|-----------------|
| Schema, sidecar, operation, path, staleness, restic, or pre-state failure | Refuse before eval-root creation |
| Crash or exception after directory creation | Partial directory; no marker; quarantine |
| Export, processed, collection, ID, document, or superseded drift | `post_capture_source_drift`; no marker; quarantine |
| Overlap/dedup outcome `FAILED` | Required/early FAILED report as possible; no marker; quarantine |
| Outcome `UNRESOLVED` | Complete artifacts + valid marker; later HITL decides acceptance; no automatic retry |

No recovery path overwrites, cleans, or resumes the same `capture_dir`. Cleanup
is a separate prohibited operation requiring separate authorization.

---

## Later implementation PR

This docs PR does not implement code. The subsequent Cursor-owned PR must name
and test at least these deltas:

| Surface | Required delta |
|---------|----------------|
| `eval_corpus/run_manifest.py` | R2b schema/precedence; safe-ID/path rules; trusted snapshot recompute; `_R2bCapability`; `bind_r2b_capture`; materializer; plain `bind_capture` refusal |
| `eval_corpus/capture.py` | Shared canonical Chroma helper; `capture_id=run_id`; one attempt; capability required before mkdir; source checks; last expanded marker |
| `scripts/eval_corpus_capture.py` | Preserve and pass capability; fixed controls; exact exit mapping; no unbound retry |
| B-Accept reader (later scope) | Require and validate report plus completion marker; never trust report status alone |
| Hermetic tests | Schema isolation, capability forgery/staleness, path/symlink containment, content drift, fixed controls, marker order/inventory/hashes, all failure classes |

Copilot audits exact-tip safety/isolation and Kiro signs architecture fidelity on
the same implementation revision. Ryan alone merges and later grants live R2b.

---

## Acceptance sequence

1. Ryan approves and merges the architecture docs PR, which states
   **Supersedes #64**.
2. Cursor implements the exact architecture with hermetic tests.
3. Copilot and Kiro review the same exact implementation tip; Ryan merges it
   and records tree proof.
4. `restic_gate: PASS` precedes trusted source recomputation and packet draft.
5. Cursor produces a fresh snapshot and draft packet; Ryan ACCEPTs only within
   the one-hour/timezone/source-identity bounds.
6. Materialize manifest, sidecar, hashes, exact argv, and revision; Ryan posts
   **ACCEPT AND GRANT**.
7. Run exactly one capture with `max_attempts=1`; materialize authorization
   before mkdir; Kiro performs VERIFY.

Architecture acceptance, implementation merge, packet ACCEPT, and
**ACCEPT AND GRANT** are distinct states. A verbal `GRANT: yes` without a
filled, approved packet is not execution authority.

---

## Relationship to PR #64

This architecture PR absorbs #64's useful T1 inventory, sidecar, restic,
pre-state STOP, evidence-pack, and independent-verification material. It
settles Option A and replaces #64's open A/B choice, report-status V4c,
incomplete prohibited list, and unconditional exit-zero expectation.

Do not merge #64. Close it only after this replacement PR exists, with a link
to the replacement so review history remains navigable.

---

## Non-goals

- Live capture or any write under the real eval root
- Implementation code, tests, generated configuration, service mutation, or
  model execution in this docs PR
- B-Accept design beyond requiring both report and marker
- C0+, R3–R8, Gate 2, promotion, or cleanup
- R2a changes or weaker non-R2b real validation

## Architecture approval bar

The architecture is mergeable only when the phase schema, content-bound trusted
snapshot, deterministic controls, capability-to-write chain, safe path
containment, expanded final marker, failure semantics, restic sequence, VERIFY
mapping, and #64 supersession are all present as binding text. Merge remains a
planning decision, not a live grant.
