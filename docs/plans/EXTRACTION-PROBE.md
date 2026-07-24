# Office Team extraction probe

| Field | Value |
|---|---|
| Status | Contract for a future Office Team coding pass; no Office Team repository was found or created |
| Question | What is the smallest valuable office workflow that can expose the shared memory boundary? |
| Primary selector | Business value to the office practice |
| Secondary output | Evidence for or against Neutral extraction |
| Stop | Do not implement until Ryan names and approves the real workflow |

## Selection rule

The architecture does not choose a toy workflow. Before coding, Ryan supplies a
one-paragraph workflow card containing:

| Required item | Meaning |
|---|---|
| Business request | A real source/request the practice needs handled |
| Valuable result | A result worth producing even if Neutral is never created |
| Human decision | The actual decision and the person/role authorized to make it |
| Completion evidence | What proves the approved action was carried out |
| Verification observable | What a later check can independently pass or fail |
| Bounded slice | What is deliberately excluded from this first cycle |

If multiple candidates exist, choose the highest-value bounded workflow. Probe
cleanliness breaks only a business-value tie. Do not narrow a valuable workflow
merely to make extraction easier.

## Required workflow envelope

The selected business nouns remain office-owned, but the first workflow must
exercise this complete durable sequence once:

```text
real source or request received
  -> canonical evidence recorded
  -> observation recorded
  -> action proposed
  -> human decision recorded
  -> approved action completed
  -> result verified
  -> process stops and restarts
  -> records and chain recovered
  -> derived index deleted and rebuilt from the ledger
```

Every arrow is represented by durable office-owned state or an explicit
relationship. The canonical append-only ledger is written before any Chroma or
other derived projection. A projection failure may leave an unapplied ledger
record; it must not erase or invalidate that record.

## Office-owned seams required for v0

These are local implementation boundaries, not a Neutral API design:

1. **Runtime identity:** load one hand-written Office Team profile/config with
   explicit project ID, config root, data root and secrets source. No universal
   schema is created.
2. **Record creation:** translate the chosen business input into office-local
   evidence, observation, action proposal, decision, completion and verification
   records.
3. **Durable append/read:** append a canonical record with flush/`fsync`; read all
   records after a fresh process starts.
4. **Identity/hash:** generate deterministic IDs where duplicate delivery must be
   idempotent and content hashes where semantic change must be detected.
5. **Projection:** apply records to a project-owned derived index through a thin
   office adapter. Chroma is allowed but not required by this architecture.
6. **Replay:** recreate an empty derived index solely from the canonical ledger.
7. **Relationships:** recover and traverse the full evidence-to-verification
   chain by stable record identity.
8. **Human policy:** accept the decision actor from office policy; do not copy
   ConvMem's signer list or approval lifecycle.

The first pass needs no scheduler, Gmail integration, background agent, UI,
marketing automation, client intake system or general workflow engine.

## Required test layers

### Workflow contract

Given one approved business fixture:

- running the workflow creates exactly one durable record for each required step;
- duplicate delivery of the source/request does not silently create a second
  canonical evidence identity;
- every child points to an existing parent or explicit root;
- the decision actor and verification result are preserved without ConvMem model
  or signer defaults; and
- all record and derived-state paths are descendants of the configured Office
  Team data root.

### Restart and replay

1. Complete the cycle in process A and close all stores.
2. Start process B with only the Office Team config and data root.
3. Load the six-step record chain and compare stable IDs, hashes, relationships
   and payloads.
4. Delete only the derived index in a disposable test data root.
5. Rebuild it from the durable ledger.
6. Assert equivalent projected record IDs, relationship results and minimal
   retrieval results.

The comparison must not rely on vector row order or backend-generated UUIDs.

### Standalone operational-independence test

Proposed location in the future repository:
`tests/independence/test_first_workflow_without_convmem.py`.

The test runner must:

1. create temporary `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and cache roots;
2. unset every `CONVMEM_*` variable and remove ConvMem entries from `PYTHONPATH`
   and `PATH`;
3. reject symlinks in the Office Team source, config, dependency and data trees;
4. run from a temporary directory outside both repositories, using only Office
   Team's locked/vendored dependency set—not an editable ConvMem install;
5. make the real ConvMem checkout absent from the test namespace or explicitly
   deny access to it, and assert that importing `convmem`, `ledger`, `observe` or
   other checkout modules cannot resolve from that path;
6. initialize a fresh Office Team ledger and database under the temporary data
   root;
7. run the entire workflow, restart, recover, remove the derived test index and
   replay it; and
8. fail on any read, write, import or subprocess access to the ConvMem checkout,
   `~/.config/convmem`, `~/.local/share/convmem`, its engineering database or a
   `convmem` process/command.

An isolated interpreter (`python -I`) plus an installed Office Team artifact is a
useful baseline. A mount namespace such as `bwrap` should make the ConvMem checkout
unavailable where practical; a portable deny-list filesystem/import probe remains
required so CI does not silently skip the assertion.

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
- classification: qualify, needs another workflow, or remain project-owned.

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

The probe passes when the approved office result is delivered, the full record
cycle survives restart and replay, the standalone independence test passes, and a
candidate comparison can be made without extracting or changing ConvMem. Probe
PASS permits an extraction-gate review; it does not itself approve extraction.

**TL;DR:** Run one genuinely valuable, tightly bounded office workflow through a
ledger-first evidence-to-verification cycle, prove restart/replay and total ConvMem
absence, then use the resulting comparison as evidence; do not select or distort
the workflow for architectural convenience.
