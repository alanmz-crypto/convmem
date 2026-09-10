# [Arc none (ad-hoc)] Isolated live-source JSONL canary evidence

## Scope and disposition

This document records sanitized evidence for the frozen Execute grant at
`474a27c654c0511fe1d076669df22288876206a6`. The canary implementation is on
`feat/2026-09-09-jsonl-incremental-live-source-canary` at Execute tip
`091a91f8102ce611edd8c229ea9ee958b2542c37`. No PR, activation, production ingest, watcher
mutation, ConvMem index/add/record, provider call, or network call was made.

The canary is intentionally fail-closed when watcher state is indeterminate.
The live-source matrix therefore has no PASS disposition in this environment;
independent review must decide whether to rerun after the user service bus is
available.

## Gate 0

Read-only checks before adapter/Chroma imports:

- branch: `feat/2026-09-09-jsonl-incremental-live-source-canary`;
- starting HEAD: `474a27c654c0511fe1d076669df22288876206a6`;
- required watcher query: `systemctl --user is-active convmem-watch.service`;
- result: ABORT, exit 1, user-scope bus unavailable (`No data available`);
- service/process status is therefore indeterminate and the grant requires
  abort; no canary write or heavy import followed this final Gate 0 attempt;
- no exact-name watcher process was observed by the read-only process check;
- frozen source paths were independently confirmed regular, non-symlink files
  with device `66306`, message inode `23605844`, metadata inode `23605859`,
  message size `304730`, and metadata size `1272`.

## Frozen source binding

The only authorized source is alias `kiro-pr291-exact-tip-review`:

- messages canonical path:
  `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_9139c273-f6b3-4080-a3f0-d89406f7f0e4/messages.jsonl`;
- messages SHA-256:
  `27ce00afc7b86191bdd8f848546f1d6e10426310277d9d03656eb4f69e3611da`;
- session metadata SHA-256:
  `ad664aab6445f34a2bc509d8f9daa0427c7492285eb09790a2d078e879cf3172`;
- physical message lines: `228`; selected complete boundary: `304730`;
- selected complete-prefix SHA-256:
  `27ce00afc7b86191bdd8f848546f1d6e10426310277d9d03656eb4f69e3611da`.

The implementation opens both frozen files read-only with close-on-exec and
no-follow flags where available, validates regular-file type, canonical path,
device/inode, size, full digest, and revalidates after atomic scratch capture.
All mutable paths are resolved below a tokenized fresh scratch root.

## Focused verification

PASS — focused behavioral set:

```text
pytest -q tests/test_scratch_jsonl_isolation.py tests/test_scratch_jsonl_incremental.py tests/test_kiro_session_jsonl.py tests/test_scratch_jsonl_chroma.py tests/test_scratch_jsonl_live_source_canary.py
73 passed in 18.41s
```

PASS — compile and repository diff checks:

```text
python -m compileall -q scratch_jsonl_prototype tests/test_scratch_jsonl_isolation.py tests/test_scratch_jsonl_incremental.py tests/test_kiro_session_jsonl.py tests/test_scratch_jsonl_chroma.py tests/test_scratch_jsonl_live_source_canary.py
git diff --check
```

PASS — changed-file Pylint (`scratch_jsonl_prototype/live_source_canary.py`
and `tests/test_scratch_jsonl_live_source_canary.py`), with the known harmless
read-only home-cache warning. The grant-wide Pylint command also reports
pre-existing findings in `tests/test_kiro_session_jsonl.py`; that file was not
edited.

## Implemented canary contract (not live-source PASS evidence)

The worker has bounded, content-free seams for snapshot prepare/publish and
source revalidation; exact source capture; deterministic local four-dimensional
embeddings; real Chroma summary/unit projection; same-path clean rebuild
comparison; independent summary and unit repair; source-scoped prune with an
unrelated sentinel; and subprocess crash/replay comparison of projection,
checkpoint authority, and Chroma summaries/units. Wrapper seams are explicitly
classified as subsumed by the underlying Chroma transitions. The exhaustive
scratch fixture uses the smallest source-derived complete prefix yielding 32
parsed user/assistant records and records only its byte boundary/count/digest.

The actual successful matrix output from an earlier pre-review run is not used
as evidence because it used the superseded system-scope watcher query. The
final required user-scope Gate 0 attempt stopped before live-source execution.

## Residual risk

Largest residual risk is environmental: without a working user-scope systemd
bus, watcher inactivity cannot be established, so the real-source canary cannot
be authorized by this run. Chroma still has no atomic cross-collection commit;
the implementation tests checkpoint-governed replay only. Bounded
`max_units_in_flight` is not a constant-memory parser or watcher-RSS claim.
