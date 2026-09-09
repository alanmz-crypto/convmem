# [Arc none (ad-hoc)] JSONL incremental scratch prototype evidence

## Disposition boundary

This package records execution evidence for the bounded scratch prototype only.
It does not authorize a canary, production routing, watcher changes, migration,
or any paid/nonlocal provider. Independent review must choose proceed toward a
separately authorized canary, require a corrective scratch pass, or stop.

The frozen reviewed input is archived unchanged at
[convmem-scratch-prototype-claude-final-check.md](../archive/inter-model/2026-09-09-jsonl-incremental-indexing-review/convmem-scratch-prototype-claude-final-check.md),
SHA-256
bf27b19c3749fd2d00e414c8b150be966a8d98aab78ec9e2a8d9cba46ada2dbf.
It was not edited or polished during execution. The branch started from
aad99004e49500d324f6fac5b012d3051c412467.

## What executed

- Exactly one supported adapter: Kiro messages.jsonl.
- Selection uses normal adapters.detect.detect_format and
  adapters.detect.get_parser dispatch and refuses every result except
  jsonl_kiro_session / adapters.kiro_session_jsonl.
- A complete-newline high-water point is copied into a scratch snapshot before
  adapter parsing. Partial trailing JSON is deferred until newline completion.
- Checkpoints bind canonical source identity, device/inode generation identity,
  complete byte boundary, prefix SHA-256, transform fingerprint, record count,
  active generation, and explicit fallback reason.
- Append continuation validates the prior prefix and calculates the dependency
  frontier at the first incomplete deterministic two-record chunk.
- Output IDs bind source identity, byte locator, and transform fingerprint.
  Generation staging, publication, pruning, checkpoint preparation/publication,
  fallback marking/cleanup, snapshot cleanup, and lock acquire/release expose
  before/after fault seams.
- All transformations, summaries, embeddings, and dedupe behavior are
  deterministic local fakes. There are no provider or network calls.

## Isolation gate result

PASS: pytest -q tests/test_scratch_jsonl_isolation.py

Observed result: 4 passed in 0.10s.

The gate mechanically established:

- a stdlib-only bootstrap runs under python -I before adapter imports;
- a fresh random-token scratch root owns source fixtures, the projection root,
  checkpoints, exports, inventory, runtime snapshots, and locks;
- canonical resolved-path containment rejects lexical escapes, production
  locations, and symlinked components before a resource factory is invoked;
- an allowlisted subprocess environment relocates HOME and XDG discovery into
  scratch and inherits no provider credentials or production ConvMem overrides;
- paid/nonlocal provider construction is refused; only deterministic-fake with
  no endpoint is accepted;
- ordinary Python socket resolution and connection calls fail with
  IsolationViolation;
- crash workers use a fresh process group and closed descriptors; an inheritable
  parent sentinel descriptor was absent in the child;
- a crash worker spawned a descendant, exited abruptly while holding a scratch
  lock, then the harness terminated the process group and the next worker
  recovered the stale scratch lock.

No production corpus, Chroma, processed state, inventory, exports, locks,
watched source, service, or provider was opened or mutated by the isolation
and prototype tests.

## Required fault and replay evidence

PASS: pytest -q tests/test_scratch_jsonl_isolation.py
tests/test_scratch_jsonl_incremental.py

Observed result after the final replay correction: 52 passed as part of the
72-test relevant set below.

PASS: relevant adapter and existing safe-reindex regression set:

pytest -q tests/test_scratch_jsonl_isolation.py
tests/test_scratch_jsonl_incremental.py tests/test_kiro_session_jsonl.py
tests/test_safe_file_reindex.py

Observed result: 72 passed in 5.82s.

The matrix covered:

- initial full scratch build; single append; multiple appends; exact
  two-record-chunk boundary; partial trailing record; next-run completion;
- validated-prefix mutation; truncation; rotation by atomic replacement;
  observable unlink/replacement with a guaranteed distinct device/inode;
  transform-fingerprint change; each records an explicit fallback reason and
  rebuilds from frontier zero;
- source append after the selected high-water point while a run is active,
  followed by next-run catch-up;
- mutation inside the selected prefix at before_publish, which raises
  SourceMoved without changing the prior authoritative projection or
  checkpoint, followed by validated-prefix fallback;
- abrupt subprocess exit before and after lock acquisition, generation
  preparation, each of two separate upserts, publication, prune,
  checkpoint preparation, checkpoint publication, snapshot cleanup, and lock
  release;
- abrupt exit before and after fallback marker creation, rebuild generation
  preparation, first fallback upsert, publication, prune, checkpoint
  preparation/publication, and fallback-marker cleanup;
- the after-first-upsert crash occurs before a later output, proving replay
  after some but not all outputs;
- a torn checkpoint candidate (.next) after crash is ignored and overwritten;
  the prior authoritative checkpoint stays parseable;
- replay convergence after every crash: complete checkpoint, all expected
  records, one authoritative active generation, and unique authoritative IDs;
- repeated crash history after publication: replay recognizes the already
  published deterministic generation and cannot demote or partially overwrite
  it during a second generation-prepare attempt;
- exact authoritative equality between incremental output and a clean rebuild
  on frozen identical source/adapter/transform/storage inputs. IDs, provenance,
  byte and record boundaries, generation identity, prefix commitment, and
  checkpoint authority fields are compared without normalization;
- frontier counters: 1,000 records at chunk size 20 required 50 transforms;
  appending one record required one transform, reused 50 historical rows, and
  an unchanged replay required zero transforms;
- scratch-only units-in-flight profiling with tracemalloc: the incremental run
  reported one unit in flight and peak traced memory no more than twice the
  initial reference run.

The durable transition inventory exercised by the suite is:
fallback_marker, generation_prepare, upsert (each output), publish, prune,
checkpoint_prepare, checkpoint_publish, fallback_cleanup, snapshot_cleanup,
lock_acquire, and lock_release.
An explicit coverage assertion fails if either side of any inventory entry is
missing from the named crash matrices.

Static verification also passed:

- python -m compileall -q on the prototype and its tests;
- git diff --check;
- Pylint on the prototype and tests: 10.00/10.

### CI portability correction

The first Python 3.12 CI run exposed nondeterminism in the replacement fixture,
not in the state machine: after unlinking the source, the runner immediately
reused the released inode for byte-identical replacement content. The fixture
now keeps the original inode alive through an open descriptor until the
replacement exists and asserts that the replacement has a distinct observable
device/inode identity. This preserves the reviewed replacement-fallback
contract instead of weakening it. Production code and retrieval behavior were
unchanged by this correction.

Non-gate context only: the later repository-wide command pytest -q completed
with 2,207 passed, one failed, 238 subtests passed, and eight warnings in
18:35.56. The single failure was
tests/test_eval_golden.py::GoldenEvalTests::test_golden_questions: the current
live retrieval baseline scored 7/10 against an 8/10 bar (Q02 and Q03 search
misses; Q10 brief output did not contain willowyhollow-dev). No prototype,
adapter, or safe-reindex test failed. This unscoped suite is explicitly
excluded from prototype PASS evidence.

## Existing-behavior Track A observation

Corroborating existing-behavior observation supplied by Ryan, not prototype
PASS evidence: **the live transcript changed during ingest and the current path
failed closed rather than committing against the moving source**.

This observation was not rerun, did not expand the Execute grant, and is not
included in any prototype pass count.

## Execution-boundary incident

After the required and relevant 72-test set passed, the executor launched the
unscoped repository-wide pytest command as an additional regression check.
That was too broad for this strict grant: the existing golden-evaluation test
invoked read-only ConvMem CLI queries against the live corpus. It made no
writes, ran no indexing, changed no service or configuration, and called no
paid provider, but the read-only production-corpus access was outside the
requested scratch boundary. It was not repeated or used as prototype evidence.
Independent review must include this incident when judging execution discipline.

## Interpretation limits and largest remaining risk

### Corrective real-Chroma scratch pass (2026-09-09) — PENDING

The bounded corrective pass added
`scratch_jsonl_prototype/chroma_projection.py` and
`tests/test_scratch_jsonl_chroma.py` on the dedicated branch
`feat/2026-09-09-jsonl-incremental-chroma-scratch` (commit `6e5354b`).
The adapter validates every mutable path under a fresh tokenized root before
its local imports/resources, writes deterministic fixed-dimension embeddings
through `production_chroma_write_session` with scratch-local lease,
attestation, and census paths, and exercises real Chroma add/read/delete
persistence for both collections.  The focused scratch/Kiro matrix passed 60
tests; compileall, diff-check, and Pylint passed (10.00/10).  The real-Chroma
worker runs after pre-import isolation/network denial, repairs missing rows
without transforms, and prunes both collections by exact source scope and
authoritative IDs.  This remains bounded scratch evidence only; no canary or
production activation is authorized.

The generation/checkpoint state machine remains deliberately separate from
production ingest and the real-Chroma adapter is an optional scratch seam.
Chroma itself does not provide the engine's cross-collection atomic commit, so
the checkpoint remains the authority for replay; independent review must
decide whether a separately authorized canary should test that boundary.

The Kiro adapter currently materializes its parsed message list, and this
prototype materializes the selected complete prefix before parsing. The
units-in-flight result proves bounded transformed-output residency, not
constant-memory source parsing. It must not be generalized into a watcher RSS
claim.

Socket denial is enforced inside the isolated Python worker rather than by a
separate operating-system network namespace. No tested code path imports or
constructs a provider, and the allowlisted environment contains no credentials.

No .crush, SQLite, Codex adapter, watcher, production source, real-source
canary, paid provider, migration, or production enablement was implemented.
