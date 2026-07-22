# Verify Plan — R2b capture + corpus package

```
Planning Status

Phase:        Verify (architecture-filled; not executed)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical evidence); Kiro (sign-off); Ryan (GATE + grant)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Architecture:** [`ARCHITECTURE-r2b-capture-auth.md`](ARCHITECTURE-r2b-capture-auth.md)

**Execution:** [`EXECUTION-2026-07-20-r2b-capture.md`](EXECUTION-2026-07-20-r2b-capture.md)

**Parent runbook:** [`EXECUTION-embedding-model-eval.md`](EXECUTION-embedding-model-eval.md)

**Future CLI:** `scripts/eval_corpus_capture.py` -> `eval_corpus.capture.run_capture`

**Gate 1 harness pin:** `3b2790f50414f0445c35748e52f849c6276839f7`

**Working directory:** `/home/lauer/Projects/convmem`

**Goal:** Prove that one Ryan-granted, real R2b capture used the exact approved
sources and controls, crossed the binder-only write gate once, and produced a
complete immutable artifact set under a previously absent capture directory.

**Report format:** Each check receives **PASS / FAIL / SKIP** plus one line of
evidence. A missing required check is not an implicit PASS. **GATE** denotes a
Ryan process decision, not a mechanical agent verdict.

**Status:** Filled against the R2b architecture. **NOT RUN.** The architecture
docs PR, its merge, and this VERIFY plan do not authorize implementation or
live capture.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| One real `authorization_phase: "r2b"`, `operations: ["capture"]` run | Fixture authorization as a substitute for a live grant |
| Approved export, processed-state path, Chroma collection, and absent capture directory | B-Accept, adjudication, C0+, R3–R8, Gate 2 |
| Fixed `capture_id`, overlap, spot, and one-attempt controls | Config generation, builds, compare, model execution |
| Trusted pre/bind/write/post source-snapshot checks | Promotion, cleanup, overwrite, resume, or same-directory retry |
| Expanded last atomic completion marker | Treating `capture_report.status` alone as completeness authority |

This plan verifies the later implementation and one later grant. It does not
authorize either.

---

## Canonical roots and completed artifact inventory

```text
AUTH_ROOT = ~/.local/share/convmem/authorizations/r2b
EVAL_ROOT = ~/.local/share/convmem/eval
manifest  = AUTH_ROOT / <run_id> / capture.json
sidecar   = AUTH_ROOT / <run_id> / capture.json.approved.sha256
capture   = EVAL_ROOT / <run_id> / capture
```

A completed capture has exactly these relative paths:

| Path | Required condition |
|------|--------------------|
| `knowledge_units.jsonl` | Always; approved export copy |
| `processed.json` | Only when approved `processed_state == "present"` |
| `chroma_extract.json` | Always; collection identity, full extracted ID set, superseded state, canonical digests |
| `chroma_documents.json` | Always; extracted documents |
| `corpus_package.jsonl` | Always; package bytes |
| `overlap_validation.json` | Always; canonical overlap result |
| `historical_spot_check.json` | Always; deterministic `n=20` plan |
| `capture_report.json` | Always; required operator/outcome evidence |
| `corpus_package_manifest.json` | Always; expanded completion marker, written last atomically |

When processed state is absent, `processed.json` must be absent. No other file,
directory, symlink, or temporary artifact is permitted. The completion marker
lists itself in `artifact_inventory` and hashes every required **non-marker**
artifact, including `capture_report.json`.

---

## Future exact command shape

The later approved packet must fill every placeholder and bind the exact argv
vector. While the retry flag exists, the authorized shape is:

```bash
cd /home/lauer/Projects/convmem
python3 scripts/eval_corpus_capture.py \
  --run-manifest <AUTH_ROOT>/<run_id>/capture.json \
  --export <approved absolute export path> \
  --processed <approved absolute processed path> \
  --capture-dir <EVAL_ROOT>/<run_id>/capture \
  --chroma-dir <approved absolute Chroma path> \
  --max-retries 1
```

No `--authorize-fixture`, caller-supplied `capture_id`, alternate overlap
policy, spot count, retry, or correction command is allowed. The implementation
must exist on merged `main` and pass exact-tip review before this command can be
granted.

---

## Mandatory rules

1. **Restic absolute:** `convmem doctor` must report `restic_gate: PASS` before
   trusted snapshot computation and before eval-root capture write. There is no
   docs, fixture, or operator waiver.
2. **Separate authority states:** architecture approval, implementation merge,
   packet ACCEPT, and `ACCEPT AND GRANT` are distinct. `GRANT: yes` without a
   filled, approved packet is not authorization.
3. **Write once:** `capture_dir` must not exist before materialization. Any
   partial directory is quarantined; no overwrite, cleanup, resume, or retry
   without a new grant and new `run_id`.
4. **Capability only:** R2b must flow through `bind_r2b_capture` -> opaque
   `_R2bCapability` -> `run_capture` ->
   `materialize_r2b_write_authorization` before mkdir. Public `AuthContext`,
   plain `bind_capture`, and path match alone cannot unlock eval-root writes.
5. **Trusted identity:** source snapshot is recomputed before capability mint,
   at materialization, and after extraction/final source check. Caller-supplied
   equality is insufficient.
6. **Fixed controls:** `capture_id=run_id`, overlap policy `canonical`,
   `spot_check_n=20`, `max_attempts=1`.
7. **Marker authority:** a valid last marker is the only structural completion
   signal. The report remains required and hash-bound, but its status is
   secondary.

---

## V0 — Safety and revision gate

```bash
convmem doctor
git -C /home/lauer/Projects/convmem rev-parse HEAD
```

| ID | Check | PASS evidence |
|----|-------|---------------|
| V0a | `restic_gate: PASS` before snapshot computation | Doctor output + timestamp |
| V0b | R2b implementation is merged on `main`; grant names its exact reviewed revision | Main SHA + ancestry/tree proof |
| V0c | Copilot and Kiro verdicts name the same exact implementation tip | Written same-SHA verdict links |
| V0d | Architecture docs PR is merged and #64 is superseded, not merged | PR links |
| V0e | Ryan packet ACCEPT and later `ACCEPT AND GRANT` are both present | Exact posts/digests; no verbal-only grant |

Any V0 failure stops before snapshot refresh or capture execution, as
applicable.

---

## V1 — Grant and packet integrity

| ID | Check | PASS evidence |
|----|-------|---------------|
| V1a | Packet and manifest contain no `PENDING_AFTER_WRITE` or unfilled placeholder | Search/result |
| V1b | `manifest_file_sha256` equals manifest file bytes | SHA-256 |
| V1c | Canonical body digest equals packet field, in-file `ryan_approved_manifest_sha256`, and adjacent one-line sidecar | Four-way values |
| V1d | Required R2b fields and source-snapshot schema validate; no pre-image Gate 2 fields are required | Validator output |
| V1e | `run_id` satisfies safe pattern and exact auth/capture path templates; lexical and resolved bindings pass | Validator/binder output |
| V1f | Exact values: real, approved, phase `r2b`, operations `["capture"]`, service policy `no_service_changes`, Gate 1 pin | Field dump |
| **V1g** | `prohibited_actions` contains `config_generation`, `adjudicate`, `baseline_build`, `challenger_build`, `compare`, `model_exec`, `model_execution`, `promote`, `cleanup_external` | Full list |
| V1h | `paths` contains exactly `export`, `processed`, `capture_dir`, `chroma_dir`, all as canonical absolute lexical strings | Field dump |
| V1i | Grant binds `capture_id=run_id`, `overlap_policy=canonical`, `spot_check_n=20`, `max_attempts=1` and exact argv | Grant excerpt |
| V1j | Packet snapshot timestamp is timezone-aware, not future, and <=1 hour at ACCEPT; any claimed same-session evidence ID is body-bound | Timestamp calculation + packet field |

---

## V2 — Trusted snapshot and pre-state STOP

| ID | Check | PASS evidence |
|----|-------|---------------|
| V2a | Trusted helper independently recomputes approved export and processed state/hash | Recompute report |
| V2b | Collection name and non-null collection ID equal approval | Recompute report |
| V2c | Full extracted count and bytewise-sorted newline ID hash equal approval, including superseded IDs | Recompute report |
| V2d | Canonical `chroma_capture_slice_sha256` binds collection + ID + document bytes + superseded state and equals approval | Recompute report |
| V2e | Recompute uses the same canonical helper as extraction; pinned canonicalization tests pass | Test names/output |
| V2f | Timestamp remains timezone-aware, not future, and <=1 hour independently at binder and materialization | Separate binder/materialization timestamp calculations |
| V2g | `capture_dir` does not exist; source paths and existing parents contain no symlink component | `lstat`/containment evidence |
| V2h | Plain `bind_capture` refuses R2b; valid binder mints the opaque capability only after V2a–V2g | Binder evidence |

Any source difference requires a fresh snapshot, packet digest, ACCEPT, and
grant. It is not correctable inside the approved run.

---

## V3 — Execution and authorization evidence

| ID | Check | PASS evidence |
|----|-------|---------------|
| V3a | CLI preserves binder output and passes the exact capability into `run_capture` | Trace/test or reviewed call chain |
| V3b | Materialization authenticates exact type/HMAC, re-verifies sidecar, re-derives bindings/snapshot, and occurs before the first mkdir/write | Trace/test |
| V3c | Actual argv vector equals the packet/grant exactly; cwd and implementation SHA recorded | JSON argv + cwd + SHA |
| V3d | Exactly one attempt; report `capture_id == run_id` and `attempt == 1`; canonical overlap and spot `n=20` | Report/artifacts |
| V3e | Exit mapping is consistent: complete -> 0; unresolved may -> 1; failed/drift/exception -> nonzero | Exit + report/marker state |
| V3f | Evidence pack records start/finish ISO timestamps, exit, complete stdout/stderr, and pre-marker artifact hashes | Evidence pack |

An `UNRESOLVED` exit `1` is not automatically a V3 failure when its valid
completion marker exists. The reviewer records the outcome and applies V4.

---

## V4 — Artifact completeness and marker authority

| ID | Check | PASS evidence |
|----|-------|---------------|
| V4a | Required non-marker artifacts exist for the approved processed state | Inventory |
| V4b | Required report exists, hashes correctly, and status is `CAPTURE_COMPLETE` or `UNRESOLVED`; `FAILED` cannot be a completed run | Report + digest |
| **V4c** | `corpus_package_manifest.json` exists, validates as `CAPTURE_ARTIFACTS_COMPLETE`, binds run/capture/auth/snapshot/package values, has exact inventory + every non-marker hash, and was published last with no later artifact write. This marker is the sole structural completeness authority; report status is secondary | Marker validator + inventory/hashes + write-order evidence |
| V4d | Marker `capture_outcome` equals report status; report hash is in marker | Cross-check |
| V4e | Package SHA, fingerprint, and unit count agree across marker, report, and package bytes | Cross-check |
| V4f | Processed-present includes `processed.json` and hash; processed-absent excludes it and source/destination remain absent | State evidence |
| V4g | `chroma_extract.json` and documents reproduce the approved canonical Chroma digest | Recomputed digest |
| V4h | Overlap output agrees with report; spot sample is deterministic from `run_id` and exactly `min(20, eligible_count)` | Recompute/result |
| V4i | FAILED, drift, exception, and crash-path tests/runs have no completion marker | Negative-path evidence |

A marker without `capture_report.json`, a marker with a stale/missing digest, or
a report without a valid marker is incomplete.

---

## V5 — Immutability and scope

| ID | Check | PASS evidence |
|----|-------|---------------|
| V5a | Final trusted live-source recomputation equals the approved snapshot before marker publication | Final snapshot evidence |
| V5b | Manifest and sidecar bytes equal V1 after execution | SHA-256 values |
| V5c | Exact capture inventory has no extras, symlinks, temp files, or artifact mtime after marker | Tree/inventory evidence |
| V5d | `historical_spot_check.json` remains byte-identical through independent sign-off | SHA-256 |
| V5e | No B-Accept/adjudication output; `corpus_accepted` remains false | Absence/report |
| V5f | No live config, service, Chroma, source, promotion, or cleanup mutation | Scoped evidence |

---

## V6 — Failure handling and independent sign-off

| ID | Check | PASS evidence |
|----|-------|---------------|
| V6a | Any partial/drift/failed directory is quarantined and not reused, resumed, overwritten, or cleaned | Path + operator statement |
| V6b | Any retry proposal names a new `run_id`, capture directory, snapshot, packet, ACCEPT, and grant | New authority chain or N/A |
| V6c | Kiro issues written PASS/FAIL naming packet/body/file hashes, implementation revision, marker hash, package SHA, fingerprint, report hash, and spot hash | Kiro verdict |
| V6d | Kiro confirms no corrective mutation or cleanup was performed during review | Explicit statement |
| V6e | Ryan alone records the arc GATE after mechanical and Kiro results | Ryan decision |

---

## Required implementation fitness tests

The later implementation PR must make these architecture properties executable:

- type-safe precedence and R2b schema isolation from R2a/global real;
- full prohibited set and exact fixed controls;
- safe `run_id`, canonical lexical equality, resolved containment, and symlink
  refusal at bind and materialization;
- caller-forged capability, public `AuthContext`, plain binder, stale sidecar,
  manifest retarget, and missing-capability refusal;
- trusted source recompute, future/naive/stale timestamp refusal, stable-ID
  document/superseded drift, collection-ID drift, and processed absence;
- one shared canonicalizer with Unicode/byte-order and missing/empty document
  fixtures;
- capability materialization before mkdir and no eval-root writes on all
  preflight failures;
- one attempt, deterministic capture/overlap/spot controls;
- last atomic marker, exact inventory/hashes, report-required semantics,
  `UNRESOLVED` marker behavior, and no marker on every failure class.

Each check should isolate one property. A holistic R2b PASS composes those
atomic checks; it must not silently reinterpret a WARN/report as a gate.

---

## Evidence log template

```text
VERIFY-r2b-capture — implementation tip <sha> — run_id <id> — <ISO-8601>
V0: …
V1: …
V2: …
V3: …
V4: …
V5: …
V6: …
Mechanical: PASS|FAIL|NOT_RUN
Kiro: PASS|FAIL|NOT_RUN — exact tip <sha>
Ryan GATE: ACCEPT|REJECT|NOT_RUN
```

## Arc close bar

The planning arc can close after architecture approval. The capture arc cannot
close until the later implementation is merged, the exact packet is granted,
V0–V5 evidence is complete, V6 independent review is written, and Ryan records
the GATE. No planning document or merge grants live execution.
