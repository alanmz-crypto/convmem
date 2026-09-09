# ConvMem Incremental Indexing — Readiness-Audit Review Request

> Status: **review requested** — The zero-cost development workflow has passed two conditional reviews. Before implementation, I propose a read-only repository and service audit. Please check whether this audit is sufficiently bounded and whether its evidence can safely support an implementation plan.

## My current position

The next action should be a **non-mutating implementation-readiness audit** of `alanmz-crypto/convmem` in an isolated or read-only checkout.

The audit must not:

- index any source;
- open or mutate the production Chroma store;
- modify `processed.json`, inventory, exports, locks, or configuration;
- start, stop, restart, or reconfigure services;
- call a paid provider or external endpoint;
- alter the production corpus;
- commit to an implementation branch.

The audit should establish repository-specific facts before the implementation plan is frozen.

## Audit questions

The auditor should answer, with file paths and line-level evidence where practical:

1. Which existing JSONL adapter and representative source should be the Phase-1 target?
2. How are source, source-generation, message/record, chunk, unit, summary, embedding, provenance, deduplication, and Chroma identities currently formed?
3. Where does whole-file hashing enter skip, identity, provenance, pruning, or completion behavior?
4. What is the actual chunking and transformation dependency graph, and what append invalidation frontier does it imply?
5. In what order are derived outputs, Chroma writes, processed state, pruning, and completion markers written?
6. Can current full rebuild or incremental fallback expose mixed generations or premature completion?
7. Which existing write/upsert semantics are replay-safe, and which are not?
8. How are configuration, model selection, provider endpoints, and fallback models resolved?
9. What services, timers, reconciliation loops, scripts, and locks can index or mutate production state?
10. Where can crash/fault injection be placed without production resource acquisition?
11. Which proposed contracts already exist, and which require new infrastructure?
12. What is the revised effort estimate for isolated JSONL implementation plus scratch proof only?

## Proposed audit method

### Repository inspection

Read-only inspection of:

- ingest and watch dispatch;
- adapters and format detection;
- chunking and transformation code;
- Chroma write/upsert/prune paths;
- processed/checkpoint state;
- provenance and deterministic-ID helpers;
- configuration and provider resolution;
- tests and existing fault-injection seams;
- service units, timers, and scripts.

### Static call-path map

Produce a compact map showing:

`source change → watcher → parser → chunker → transform calls → Chroma writes → processed/checkpoint update → reconciliation/prune`

Mark every point that can perform an external call, acquire a production lock, or mutate durable state.

### Identity and publication audit

For each authoritative output, record:

| Output | Current identity | Inputs to identity | Write operation | Prune/replace behavior | Replay safety |
|---|---|---|---|---|---|
| Record/message |  |  |  |  |  |
| Chunk |  |  |  |  |  |
| Summary |  |  |  |  |  |
| Embedding/unit |  |  |  |  |  |
| Provenance |  |  |  |  |  |

Do not infer compatibility from names alone; trace the code that constructs and consumes each key.

### Service and isolation audit

Inventory every production-capable process and classify it as:

| Process/path | Can ingest? | Can summarise/embed? | Can write Chroma? | Can mutate checkpoint? | How isolated/stopped? |
|---|---:|---:|---:|---:|---|
| Watcher |  |  |  |  |  |
| Refine |  |  |  |  |  |
| Reconciliation |  |  |  |  |  |
| Timer/script |  |  |  |  |  |
| Manual CLI |  |  |  |  |  |

This is an inventory exercise only. Do not change service state while performing it.

### Contract-readiness classification

Classify each proposed contract as:

- **Existing and reusable**;
- **Existing but insufficient**;
- **Missing and required before implementation**;
- **Can follow the first isolated slice**.

Required concepts:

- source identity and generation;
- complete committed record boundary;
- transform fingerprint;
- checkpoint/commit state;
- stable derived-output identity;
- dependency invalidation frontier;
- fallback reason;
- source-generation publication/activation state;
- test isolation guard.

## My assumptions that need checking

| ID | Assumption | What would invalidate it |
|---|---|---|
| A1 | A read-only code/config audit can answer the readiness questions without indexing or starting services. | Any required fact that can only be learned by mutating production state or calling a paid provider. |
| A2 | Existing tests and static tracing can identify most crash and publication risks before implementation. | Critical behavior hidden in runtime configuration or external systems that static inspection cannot reveal. |
| A3 | The current full-rebuild path can remain untouched during audit and serve as a behavioral reference later. | Evidence that merely inspecting or invoking its helpers causes production writes or irreversible state changes. |
| A4 | JSONL remains a valid first target if the audit finds a representative adapter and source. | No suitable adapter/source, or shared storage semantics force SQLite-specific work first. |
| A5 | Source-generation-safe publication can be designed after identity/write inspection rather than assumed upfront. | Evidence that current Chroma/write semantics make source-scoped atomic activation impossible without a migration. |
| A6 | The audit can narrow the estimate enough for an implementation plan. | The decisive work is experimental and cannot be bounded without scratch prototyping. |
| A7 | No destructive migration is required for Phase 1, even if compatibility is incomplete. | Evidence that the only safe implementation requires irreversible changes to existing authoritative data. |

## Required audit deliverable

The audit should produce one bounded report containing:

1. target adapter/source recommendation;
2. source-to-Chroma call-path map;
3. identity/provenance compatibility matrix;
4. current write/publication/checkpoint ordering;
5. actual invalidation-frontier analysis;
6. production process/service/lock inventory;
7. provider and configuration resolution map;
8. fault-injection seam inventory;
9. contract readiness classification;
10. blockers and non-blockers;
11. revised effort estimate and confidence;
12. explicit statement that no production mutation or paid call occurred.

## Decision gates after the audit

The audit should recommend one of:

- **Proceed to isolated implementation planning** — enough evidence exists and no unresolved safety blocker remains;
- **Proceed with a bounded scratch prototype first** — architecture is plausible but key behavior needs isolated experimentation;
- **Do not proceed** — a safety, identity, publication, or isolation blocker remains.

Passing the audit must not authorise:

- production incremental routing;
- `.crush` SQLite processing;
- a real-source canary;
- paid-provider use;
- migration or corpus rewrite.

## Required second-opinion verdict

Return:

### Overall verdict

`PASS`, `PASS WITH CONDITIONS`, or `FAIL`

State whether this audit is sufficiently bounded and whether its outputs can safely support an implementation plan.

### Assumption verdicts

| ID | Verdict (`agree` / `refute` / `restate`) | Reasoning | Corrected formulation if needed |
|---|---|---|---|
| A1 |  |  |  |
| A2 |  |  |  |
| A3 |  |  |  |
| A4 |  |  |  |
| A5 |  |  |  |
| A6 |  |  |  |
| A7 |  |  |  |

### Required corrections

List only changes required before the audit starts or before its result can authorize implementation planning.

### Audit additions

List any missing read-only checks, evidence fields, or safety boundaries.

### Recommended next action

Name the smallest safe next step, owner/lane, and expected evidence.

### Confidence

State `high`, `medium`, or `low`, with one sentence explaining what remains unverified.

## Review boundary

This request authorizes no code change, service change, indexing, provider call, production write, corpus migration, or implementation. It is solely a request to review the proposed read-only audit boundary.
