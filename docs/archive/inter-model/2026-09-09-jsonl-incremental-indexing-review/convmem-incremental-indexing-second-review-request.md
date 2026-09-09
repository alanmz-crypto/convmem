# ConvMem Incremental Indexing — Second Review Request

> Status: **review requested** — This is a synthesis of the first review and my current engineering position. Please challenge it again before any ConvMem implementation begins.

## Question for the reviewer

Can we safely improve ConvMem’s indexing while keeping the live corpus, paid providers, and production watcher completely out of the development loop—and what is the smallest implementation that provides real value without creating a data-loss or duplicate-memory risk?

## My current position

I believe the answer is **yes, with conditions**:

1. Development can proceed at zero paid API cost and without indexing production data.
2. The live watcher should remain paused during implementation.
3. A scratch-only test mode should enforce path, lock, provider, and network isolation mechanically.
4. Synthetic JSONL fixtures plus deterministic fake transformations can prove most checkpoint, replay, invalidation, fallback, and duplicate/loss invariants.
5. The first implementation should be adapter-scoped to append-only JSONL, not SQLite.
6. The current full-rebuild path should remain available as a conservative fallback.
7. `.crush/crush.db` should remain paused or full-rebuild-only until SQLite-specific semantics are designed and tested.
8. No production enablement should occur until incremental and scratch full-rebuild outputs converge across normal and crash/retry histories.

I do **not** believe we should promise a 3–5 working-day production-safe fix yet. A narrow prototype may fit that window, but the safe slice likely requires more time because checkpoint identity, commit ordering, stable output IDs, invalidation-frontier calculation, and mechanical isolation are substantive work.

## What I think the first reviewer established

The first reviewer returned `PASS WITH CONDITIONS` and identified these as necessary:

- source generation identity in addition to a byte/message offset and prefix hash;
- a committed complete-record boundary rather than an observed byte position;
- a transformation/configuration fingerprint;
- deterministic and replay-safe output identities;
- checkpoint advancement only after authoritative outputs commit;
- actual dependency-frontier calculation rather than assuming one final chunk;
- path guards independent of nominal test configuration;
- paid-provider and network blocking;
- separate treatment of background services and SQLite.

I accept these as the working safety baseline unless this review finds a concrete contradiction.

## Propositions I want checked again

| ID | My proposition | What would change my mind |
|---|---|---|
| R1 | A hard isolated-test mode can provide strong correctness evidence without production indexing. | Evidence that current ConvMem code has an unavoidable production-path discovery or shared lock that cannot be bypassed safely in tests. |
| R2 | Deterministic fake summaries, embeddings, and dedupe are sufficient for the core state-machine tests. | Evidence that a correctness property depends on real model semantics rather than inputs, identities, writes, or state transitions. |
| R3 | The first useful implementation should target append-only JSONL. | Evidence that no representative JSONL source exists, or that the shared ingest/storage contracts cannot support a source-neutral implementation. |
| R4 | SQLite `.crush` support should not be included in the first slice. | Evidence that SQLite is the only meaningful cost driver and JSONL work would provide no useful architectural or economic evidence. |
| R5 | Automatic full-rebuild fallback is safe if it runs only against scratch resources in tests and is idempotent in production. | Any failure mode where fallback can expose mixed generations, advance a false checkpoint, duplicate authoritative units, or prune valid data. |
| R6 | The invalidation frontier should be derived from actual chunk dependencies, not hard-coded as one chunk. | Evidence that current chunking and downstream transforms guarantee a narrower fixed frontier under all supported append cases. |
| R7 | We can get meaningful savings without a paid canary by measuring work proxies and synthetic scaling. | Evidence that production cost behavior cannot be inferred from call counts and frontier scaling until a real paid run occurs. |
| R8 | Keeping the watcher paused is the correct immediate cost-control action. | Evidence that another active service is still indexing or that pausing creates unrecoverable source changes. |
| R9 | No corpus migration should be required for the initial rollout. | Evidence that current authoritative IDs or provenance make safe reuse impossible without a migration. |
| R10 | The safe first slice is likely 5–10 working days, not 3–5. | A repository-specific audit showing the required checkpoint, identity, isolation, and fault-injection machinery already exists. |

## Proposed no-cost execution boundary

Before implementation tests:

- watcher, refine, reconciliation, and any ingest-capable timers are stopped or independently isolated;
- every mutable test path is beneath a fresh temporary root;
- production Chroma, processed state, inventory, exports, locks, watched roots, and `.crush` are rejected before open;
- paid-provider selection is a test error;
- nonlocal model endpoints are rejected;
- ordinary tests use deterministic fakes and no network;
- local-model compatibility tests, if needed, are separate and use scratch stores;
- no `convmem index`, `record --approve-last`, or production write command is run.

## Proposed implementation boundary

The first code slice should introduce source-neutral contracts for:

- source identity and generation;
- complete committed record boundary;
- transform fingerprint;
- checkpoint and commit state;
- stable derived-output identity;
- dependency invalidation frontier;
- explicit fallback reason.

Then implement JSONL append continuation behind an opt-in capability gate. The implementation must be able to replay after any crash and converge with a clean scratch full rebuild. It must not prune on verified append. Uncertain continuity must fall back conservatively.

## Acceptance gates I currently consider necessary

### Zero-cost isolation gate

- no production path or lock can be opened by the test harness;
- no paid or nonlocal provider can succeed;
- no live service can mutate the production store during tests.

### Correctness gate

For every fixture state and injected crash point, incremental replay must produce the same authoritative source coverage, IDs, provenance, boundaries, duplicate count, and checkpoint meaning as a clean scratch rebuild.

### Incrementality gate

A small append to a large synthetic JSONL source must reuse historical work and perform work proportional to the calculated dependency frontier, not total source size.

### Production gate

Passing JSONL tests does not authorise `.crush` SQLite processing or a real-source canary. Those require separate review and explicit scope.

## Specific questions for this second check

1. Is my distinction between “correctness evidence” and “production economics/semantic quality” technically sound?
2. Is the proposed hard isolation boundary sufficient, or is a stronger subprocess/container/network boundary required?
3. Is JSONL still the right first target given that the currently narrowed watched source is `.crush` SQLite?
4. Which of the listed contracts must exist before any implementation, and which can safely follow in later slices?
5. Is retaining full-rebuild fallback compatible with safe incremental writes, or does it require generation staging from the start?
6. What is the minimum crash/fault matrix that should block a canary?
7. Is the 5–10 working-day estimate reasonable after including isolation and review, or is it still optimistic?
8. What important risk or cost-control mechanism have I missed?

## Required verdict format

Return:

### Overall verdict

`PASS`, `PASS WITH CONDITIONS`, or `FAIL`

State whether the position and execution boundary are safe to carry into an implementation plan.

### Proposition verdicts

| ID | Verdict (`agree` / `refute` / `restate`) | Reasoning | Corrected formulation if needed |
|---|---|---|---|
| R1 |  |  |  |
| R2 |  |  |  |
| R3 |  |  |  |
| R4 |  |  |  |
| R5 |  |  |  |
| R6 |  |  |  |
| R7 |  |  |  |
| R8 |  |  |  |
| R9 |  |  |  |
| R10 |  |  |  |

### Required corrections

List only corrections that must be made before implementation planning or before a real-source canary.

### Recommended next action

Name the smallest safe next action, its lane/owner, and the evidence it must produce.

### Confidence

State `high`, `medium`, or `low`, with one sentence explaining what remains unverified.

## Review boundary

This is a design and safety review. Do not modify ConvMem, index any source, call paid providers, change services, mutate the production corpus, or treat this request as implementation authorisation.
