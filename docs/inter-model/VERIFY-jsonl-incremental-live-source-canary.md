# [Arc none (ad-hoc)] Isolated live-source JSONL canary evidence

## Scope and disposition

**Disposition: PASS, pending independent Kiro review.** This document records
sanitized evidence for Ryan's frozen Execute grant at
`474a27c654c0511fe1d076669df22288876206a6`. The one-shot canary execution used
implementation `f5503832917c8a4d51292d3d3fa3c27c33d80f28`. The independently
reviewed reproducibility correction is `fc811fc85312ae901d1896defda7f3fe72ae4e81`
on `feat/2026-09-09-jsonl-incremental-live-source-canary`.

The canary read one explicitly bound Kiro transcript and its sibling metadata
file. Every write, mutation, crash, Chroma collection, checkpoint, projection,
lock, attestation, census, and configuration path was created under fresh
temporary roots and removed after evidence extraction. No PR, activation,
production ingest, watcher mutation, ConvMem index/add/record, provider call,
or outbound network call was made.

## Gate 0 and isolation

Gate 0 ran before adapter or Chroma imports and passed:

- `systemctl --user is-active convmem-watch.service` could not reach the local
  user bus, so the fail-closed fallback queried the same user manager through
  `systemctl --user --machine=lauer@.host is-active convmem-watch.service`;
- the fallback returned `inactive`, and the independent `/proc` command/name
  census found zero ConvMem watcher processes;
- the worker received a fresh tokenized root and a sanitized environment with
  no credential-like or production-override names;
- network denial was installed before heavy imports and raises
  `IsolationViolation`;
- the post-run descriptor census found no open production ConvMem path or lock;
- all subprocess workers used isolated mode, a new session, closed inherited
  descriptors, and deterministic local four-dimensional embeddings.

The fallback does not convert unknown state into success: only the literal
`inactive` or `failed` state is accepted. `active`, missing/unknown output, both
probe failures, or any matching watcher process aborts the run.

## Frozen source binding

The only authorized live source was alias `kiro-pr291-exact-tip-review`:

- messages path:
  `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_9139c273-f6b3-4080-a3f0-d89406f7f0e4/messages.jsonl`;
- messages device/inode: `66306` / `23605844`;
- messages size/physical lines: `304730` bytes / `228`;
- messages and selected-prefix SHA-256:
  `27ce00afc7b86191bdd8f848546f1d6e10426310277d9d03656eb4f69e3611da`;
- selected complete boundary: `304730`;
- sibling `session.json` device/inode: `66306` / `23605859`;
- sibling size/SHA-256: `1272` bytes /
  `ad664aab6445f34a2bc509d8f9daa0427c7492285eb09790a2d078e879cf3172`.

Both files were opened read-only with close-on-exec and no-follow flags where
available. Regular-file type, canonical path, identity, size, and digest were
validated before atomic scratch capture and revalidated afterward. A final
independent `sha256sum` after execution reproduced both grant digests. The live
files were read, never mutated.

## Canary execution

Command (exit `0`, status `PASS`):

```text
/home/lauer/miniforge3/envs/convmem/bin/python -I scratch_jsonl_prototype/live_source_canary.py
```

Sanitized results:

- full-source baseline: `80` parsed records, `40` summary rows, `40` unit rows,
  selected boundary `304730`;
- unchanged replay: `0` transform calls and exact Chroma authority equality;
- staged source-derived append: `39` initial records to `80`, frontier record
  `38`, `21` transform calls, and `19` reused rows;
- staged append versus same-path clean rebuild: exact summaries/units,
  projection, and checkpoint-authority equality with no normalization other
  than diagnostic-only `fallback_reason`;
- incomplete record: authority remained at `1` record with `0` transforms;
  completing that source-derived record produced `2` records with exactly `1`
  transform;
- fallbacks: `validated_prefix_mutated`, `source_truncated`,
  `source_replaced_or_rotated`, and `transform_fingerprint_changed` all took
  their declared paths;
- storage repair: independently removed summary and unit rows were repaired
  with `0` transforms and exact authority equality;
- source-scoped pruning: the unrelated-source sentinel survived normal and
  crash/replay pruning;
- bounded residency: `max_units_in_flight = 1`.

The exhaustive crash fixture was the smallest complete source-derived prefix
containing `32` parsed messages: boundary `140924`, SHA-256
`dc3a7045cb326aeef4b08ae6cd08b5d5b55a7d91fd6de67874f20b5adf0577f2`.
Real subprocess exit `86` and replay covered:

- `6/6` capture sides: snapshot prepare, snapshot publish, and source
  revalidation; replayed scratch copies equaled the captured bytes exactly;
- `52/52` engine sides: fallback marker, generation prepare, every discovered
  upsert authority point, publish, prune, checkpoint prepare/publish, fallback
  cleanup, snapshot cleanup, and lock acquire/release;
- `4/4` real-Chroma upsert sides: summary and unit upsert;
- `4/4` real-Chroma prune sides: summary and unit prune.

The runtime compares the declared engine, Chroma, and capture inventories to
the injected points and requires both `before` and `after` coverage. A focused
test removes one side and proves the assertion fails closed. Every engine and
Chroma crash replay converged exactly to a same-path clean rebuild.

## Focused verification at the implementation revision

PASS — required five-file behavioral set:

```text
python -m pytest -q tests/test_scratch_jsonl_isolation.py tests/test_scratch_jsonl_incremental.py tests/test_kiro_session_jsonl.py tests/test_scratch_jsonl_chroma.py tests/test_scratch_jsonl_live_source_canary.py
76 passed, 1 warning in 18.46s
```

The warning is an upstream OpenTelemetry `SelectableGroups` deprecation emitted
by the installed Chroma dependency.

PASS — exact grant-wide Pylint scope (`PYLINTHOME` redirected to temporary
storage because this execution sandbox makes the normal cache read-only):

```text
python -m pylint scratch_jsonl_prototype tests/test_scratch_jsonl_isolation.py tests/test_scratch_jsonl_incremental.py tests/test_kiro_session_jsonl.py tests/test_scratch_jsonl_chroma.py tests/test_scratch_jsonl_live_source_canary.py
Your code has been rated at 10.00/10
```

PASS — compile and diff checks:

```text
python -m compileall -q scratch_jsonl_prototype tests/test_scratch_jsonl_isolation.py tests/test_scratch_jsonl_incremental.py tests/test_kiro_session_jsonl.py tests/test_scratch_jsonl_chroma.py tests/test_scratch_jsonl_live_source_canary.py
git diff --check
```

The Pylint correction reformats only the already-scoped
`tests/test_kiro_session_jsonl.py` and removes its unused import; it changes no
test behavior or production runtime code.

## Post-review reproducibility correction

Kiro's independent review at evidence tip `97c8518` issued a conditional PASS:
the safety envelope and recorded canary execution were sound, but
`test_capture_worker_fault_name_reaches_explicit_fault_option` reused the
point-in-time live grant. Once that active transcript grew, the guard correctly
failed with `size drift`, making the repeatable suite nondeterministic.

Correction `fc811fc85312ae901d1896defda7f3fe72ae4e81` supplies the capture
subprocess with explicit synthetic message/metadata descriptors created below
the tokenized temporary root. The worker rejects partial descriptor sets and
contains both synthetic paths through `ScratchBoundary` before opening them.
The default one-shot canary path remains bound to `FROZEN_MESSAGES` and
`FROZEN_SESSION_META`; no new live-source authority was added.

The exact five-file suite now passes independently of the changed live file:
`76 passed, 1 warning in 18.66s`; Pylint remains `10.00/10`, and compileall plus
`git diff --check` remain clean. Per Kiro's recommendation, the live canary was
not rerun: the recorded execution at `f550383` remains the point-in-time
evidence, while the unit suite at `fc811fc` is deterministic.

## Scope audit and residual risk

The Execute and corrective diff is confined to the scratch package, focused tests, this
VERIFY document, and `docs/inter-model/LATEST.md`. No production adapter,
writer, watcher, retrieval, provider, or Chroma-store module changed.

This PASS is evidence for the isolated one-source canary only. Chroma still
does not provide an atomic cross-collection commit; checkpoint-governed replay
is the recovery mechanism tested here. `max_units_in_flight` proves bounded
transformed-output residency, not constant-memory parsing or watcher RSS.
Nothing here authorizes a PR, migration, production indexing, watcher
integration, paid/nonlocal provider, or activation. Independent Kiro review
decides whether to proceed, require a corrective scratch pass, or stop.
