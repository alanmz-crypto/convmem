# Office Team extraction probe

| Field | Value |
|---|---|
| Status | Contract for a future Office Team coding pass; no Office Team repository was found or created |
| Question | What is the smallest valuable office workflow that can expose the shared memory boundary? |
| Primary selector | Smallest independently valuable workflow that exercises the durable seams without unrelated product infrastructure |
| Secondary output | Evidence for direct qualification, bounded convergence, deferral or project ownership |
| Gate 0 default | Approved office policy or procedure change; no current repository evidence blocks it |
| Stop | Do not implement until Ryan authorizes the repository/pass and identifies the real policy artifact with the office authorities |

## Selection rule

Choose the **smallest independently valuable workflow that exercises the target
durable seams without requiring unrelated product infrastructure**. Business
value is mandatory, but so are a finishable boundary and useful coverage of the
ledger, authority, completion and verification seams.

Repository evidence reveals no blocker to the following exact Gate 0 workflow.
Use it unless a concrete office-artifact or authority blocker is found before
execution:

### Gate 0 workflow card — approved office policy or procedure change

| Item | Locked v0 choice |
|---|---|
| Business request | Revise one real office service or operating policy. |
| Valuable result | The approved policy artifact is updated. |
| Evidence | One canonical evidence record contains or references the change request and previous policy text. The received request is not a seventh record. |
| Observation | The current text does not match the intended policy. |
| Action proposal | An exact replacement revision. |
| Human decision | The Owner–Practitioner approves or rejects the exact revision. |
| Completion | The Managing Co-operator applies the approved revision to the office-owned policy artifact. |
| Verification observable | The active artifact matches the approved content and semantic hash. |
| Exclusions | Gmail, scheduling, client records, health intake, background agents, website automation and general workflow machinery. |

Gate 0 still requires Ryan to authorize repository creation and execution and to
identify the real policy artifact with the office authorities. It does not require
another architecture search for a different workflow.

### Distinct human authorities

| Authority | Responsibility in this pass |
|---|---|
| Ryan | Repository creation, architecture and execution gates, implementation authorization and merge. Ryan is not automatically the office policy decision actor. |
| Owner–Practitioner | Final authority over the selected office policy or public service promise; approves or rejects the exact revision. |
| Managing Co-operator | Applies the approved revision and performs operational verification where authorized; cannot substitute for Owner–Practitioner approval. |

## Required workflow envelope

The selected business nouns remain office-owned, but the first workflow must
exercise this complete durable sequence once:

```text
canonical evidence recorded (contains/references the received request + old text)
  -> observation recorded
  -> action proposed
  -> human decision recorded
  -> approved action completed
  -> result verified
  -> process stops and restarts
  -> records and chain recovered
  -> derived index deleted and rebuilt from the ledger
```

The v0 ledger contains exactly six canonical records:

1. evidence;
2. observation;
3. action proposal;
4. human decision;
5. completion; and
6. verification.

The source/request payload or durable source reference lives inside the evidence
record. It is input to record 1, not record 0 or a seventh canonical record.

Every arrow is represented by durable office-owned state or an explicit
relationship. The canonical append-only ledger is written before any Chroma or
other derived projection. A projection failure may leave an unapplied ledger
record; it must not erase or invalidate that record.

## Office-owned seams required for v0

These are local implementation boundaries, not a Neutral API design:

1. **Human project identity:** load one hand-written `PROJECT-PROFILE.md` with
   purpose, human roles, authorities, first workflow, exclusions and assumptions.
2. **Machine configuration:** load a separate `config.toml` with project ID,
   config/data/secrets roots, ledger/projection paths and runtime settings.
   Neither file is a universal schema.
3. **Record creation:** translate the chosen business input into office-local
   evidence, observation, action proposal, decision, completion and verification
   records.
4. **Durable append/read:** append a canonical record with flush/`fsync`; read all
   records after a fresh process starts.
5. **Identity/hash:** generate deterministic IDs where duplicate delivery must be
   idempotent and content hashes where semantic change must be detected.
6. **Projection:** apply records to a project-owned derived index through a thin
   office adapter. Chroma is allowed but not required by this architecture.
7. **Replay:** recreate an empty derived index solely from the canonical ledger.
8. **Relationships:** recover and traverse the full evidence-to-verification
   chain by stable record identity.
9. **Human policy:** accept the decision actor from office policy; do not copy
   ConvMem's signer list or approval lifecycle.

The first pass needs no scheduler, Gmail integration, background agent, UI,
marketing automation, client intake system or general workflow engine.

## Minimum ledger integrity rules

This is a deliberately small ledger contract, not a transaction framework:

- v0 has one writer; concurrent writers are rejected or serialized by an
  office-local lock;
- each append writes one complete canonical JSON record on one line, followed by
  flush and `fsync`, before projection begins;
- startup validates every line and detects an invalid or truncated final line;
- corruption is reported and fails closed—no malformed line is silently skipped;
- a projection failure never removes or invalidates the durable canonical record;
- projection progress is stored independently from canonical durability, so the
  last applied record can be identified and unapplied records retried;
- projection apply/replay is idempotent by stable record identity; and
- tests cover duplicate source delivery, a simulated crash tail, startup
  detection, recovery after the tail is explicitly repaired, and projection
  retry after a durable append.

## Required test layers

### Workflow contract

Given one approved business fixture:

- running the workflow creates exactly six durable canonical records in the
  locked order: evidence, observation, action proposal, human decision,
  completion and verification;
- the evidence record contains or references the received request and previous
  policy text;
- duplicate delivery of that input does not silently create a second
  canonical evidence identity;
- every child points to an existing parent or explicit root;
- the decision actor and verification result are preserved without ConvMem model
  or signer defaults; and
- all record and derived-state paths are descendants of the configured Office
  Team data root.

### Restart and replay

1. Complete the cycle in process A and close all stores.
2. Start process B with only the Office Team config and data root.
3. Load the six-record chain and compare stable IDs, hashes, relationships
   and payloads.
4. Delete only the derived index in a disposable test data root.
5. Rebuild it from the durable ledger.
6. Assert equivalent projected record IDs, relationship results and minimal
   retrieval results.

The comparison must not rely on vector row order or backend-generated UUIDs.

### Independence v0 — mandatory for the first implementation

Proposed location in the future repository:
`tests/independence/test_first_workflow_without_convmem.py`.

The test runner must:

1. create temporary `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and cache roots;
2. unset every `CONVMEM_*` variable and remove ConvMem entries from `PYTHONPATH`
   and `PATH`;
3. assert no Office Team source, configuration, dependency or data path is a
   symlink into the ConvMem checkout;
4. run from a temporary directory outside both repositories, using only Office
   Team's locked/vendored dependency set—not an editable ConvMem install;
5. make the ConvMem checkout unavailable to the test process and assert that
   importing `convmem`, `ledger`, `observe` or other checkout modules cannot
   resolve from it;
6. initialize a fresh Office Team ledger and database below the temporary Office
   Team root and assert every configured/runtime path stays below that root;
7. run the entire workflow, restart, recover, remove the derived test index and
   replay it; and
8. fail on any resolved import, configured path, data access or command dependency
   involving the ConvMem checkout,
   `~/.config/convmem`, `~/.local/share/convmem`, its engineering database or a
   `convmem` process/command.

An isolated interpreter (`python -I`) plus an installed Office Team artifact is a
useful baseline. The checkout may be omitted from the clean test installation or
made unavailable with an inexpensive portable mechanism. Independence v0 must not
grow an OS-auditing subsystem before the workflow functions.

### Independence v1 — required hardening after the first workflow

After the functional probe and any approved convergence proof, harden isolation
with OS-level mount/access denial, comprehensive subprocess interception and
filesystem auditing. Use `bwrap` or an equivalent mechanism where available and
portable. These checks remain required before the independence arc closes, but
they do not block the first functioning workflow unless already inexpensive in
the Office Team environment.

### Expected fixture shape

```text
tests/fixtures/independence/
  input/                 # one real but sanitized request/source
  expected/
    record_chain.json    # semantic IDs, kinds and relationships only
    verification.json    # expected observable and result
  clean_home/            # empty config/data skeleton, no copied ConvMem files
```

Do not commit real client data or secrets. The fixture should preserve the shape
of the valuable workflow while using fabricated content.

## Evidence harvested after the run

For each candidate in
[NEUTRAL-CORE-CANDIDATES.md](NEUTRAL-CORE-CANDIDATES.md), record:

- ConvMem responsibility and observable contract;
- Office Team responsibility and observable contract;
- identical invariants and divergent policy;
- tests that can move unchanged;
- imports, config, paths and state each implementation requires; and
- classification: qualifies directly, requires bounded convergence proof, needs
  another workflow, or remains project-owned.

This comparison is the output of the probe. Extracting code is not.

## Stop conditions

Stop the coding pass and return to Ryan when:

- no real, valuable and bounded office workflow has been approved;
- the proposed slice is useful only as an architectural demonstration;
- completing the value requires a product feature explicitly out of scope—return
  for a business-scope decision instead of faking it;
- any runtime import, path, database, process or config points to ConvMem;
- the ledger cannot reconstruct the derived state after restart;
- a proposed “shared” seam needs domain flags to disguise different
  responsibilities; or
- the only qualified result is a helper too small to form a useful standalone
  Neutral runtime.

## Probe pass criteria

The probe passes when the approved policy artifact is updated, exactly six records
survive restart and replay, Independence v0 passes, and a candidate comparison can
be made without extracting or changing ConvMem. Probe PASS permits the comparison
gate to route candidates, including to a separately approved convergence proof;
it does not itself approve ConvMem changes or Neutral extraction.

**TL;DR:** Revise one real office policy through exactly six ledger-first records,
with Owner–Practitioner approval and Managing Co-operator completion; prove
restart/replay and Independence v0, then route comparison results to direct
qualification, bounded convergence, another workflow or project ownership.
