# ConvMem Incremental Indexing — Claude Adversarial Readiness Audit

> Status: **audit authorised** — Perform a strictly read-only implementation-readiness audit. This document is the governing specification for the audit and does not authorise implementation, indexing, service changes, provider calls, production access, migration, or corpus modification.

## TL;DR

ConvMem currently reprocesses an entire changed source, causing avoidable summarisation, embedding, deduplication, CPU, memory, and provider cost. The proposed remedy is conservative chunk-level incremental indexing, beginning with append-only JSONL and keeping SQLite/`.crush` separate.

Your task is to determine whether the repository contains enough evidence to plan the isolated JSONL slice safely, or whether a bounded scratch prototype is required first. Do not infer runtime safety from static intent. Do not touch production resources.

## Repository and operating context

- Repository: `alanmz-crypto/convmem`
- Current narrowed relocation watcher source: `/home/lauer/Projects/SubProjects/Relocating_Habitat/Shipping_Transportation/.crush/crush.db`
- Ordinary Markdown in that relocation folder is not an active watcher input under the current parser routing.
- The production corpus is shared and must not be opened, indexed, or used as a test target.
- The live watcher and other production-capable indexing paths are expected to remain paused or isolated during later development; do not change their state during this audit.

Relevant background:

- [Issue #286 — Make changed-file indexing incremental at chunk/append level](https://github.com/alanmz-crypto/convmem/issues/286)
- [Issue #268 — Watch OOM: full-file re-index on every append](https://github.com/alanmz-crypto/convmem/issues/268)

## Audit role

Act as Claude’s independent adversarial reviewer for storage correctness, crash safety, cost isolation, and implementation readiness.

Do not redesign this audit procedure unless you encounter a concrete contradiction. Report repository facts, unresolved runtime questions, blockers, and a bounded recommendation.

## Absolute audit boundaries

### Permitted

- Read source files, tests, configuration text, service-unit definitions, timer definitions, shell scripts, Git history, and issue/design documents.
- Trace call paths with static search and code reading.
- Derive production locations from repository, configuration, and service declarations.
- Classify existing tests by their apparent isolation and side effects.
- Inspect independently surfaced, read-only runtime metadata only when doing so does not probe production data resources or change service state.

### Prohibited

- Run `convmem index`, `convmem add`, `convmem record`, refine, reconciliation, or watch.
- Instantiate Chroma, model, provider, adapter, lock, or ingest clients.
- Open production Chroma, `.crush`, processed state, inventory, exports, or production locks—even read-only.
- Probe, enumerate, resolve through, `stat`, or otherwise inspect production corpus/store paths merely to establish that they exist.
- Execute production-capable helpers, CLI commands, service scripts, or existing tests merely to discover behavior.
- Start, stop, restart, enable, disable, or reconfigure services.
- Make paid or nonlocal provider calls.
- Create an implementation branch, modify code/configuration, migrate data, or alter the corpus.

If a fact cannot be established within these boundaries, classify it as `unknown` and recommend the smallest bounded scratch mechanism needed to resolve it.

## Evidence discipline

Every material finding must include:

| Finding | Evidence | Status | Side-effect classification | Consequence |
|---|---|---|---|---|
| Example | `path/to/file.py:Lx-Ly` | `observed` / `inferred` / `unknown` | pure/read-only, filesystem read, lock, write, spawn, network, or uncertain | plan / scratch prototype / blocker |

Definitions:

- **Observed:** directly established from source, configuration, independently surfaced read-only metadata, or a trustworthy historical test result whose exact revision, result, isolation boundary, and correspondence to the proposition are all established.
- **Inferred:** a reasoned interpretation that still depends on an untested assumption.
- **Unknown:** not established safely; it must not serve as an implementation premise.

The existence or source code of a test does not by itself establish the behavior it asserts. Do not call behavior safe, atomic, idempotent, migration-free, or cost-free without evidence for that exact proposition.

## Required audit questions

1. Which existing append-only JSONL adapter and representative fixture/source should be the Phase-1 target?
2. How are source, source-generation, record/message, chunk, summary, embedding/unit, provenance, deduplication, and Chroma identities formed?
3. Where does whole-file hashing enter skip, identity, provenance, pruning, or completion behavior?
4. What is the actual chunking and downstream dependency graph, and what append invalidation frontier follows from it?
5. In what order are derived outputs, Chroma writes, pruning, processed/checkpoint state, and completion markers written?
6. Can current full rebuild or fallback expose mixed generations, lose units, duplicate units, or falsely mark a source complete?
7. Which write/upsert operations are replay-safe, replay-unsafe, or unknown?
8. How are CLI flags, environment variables, config files, defaults, adapter defaults, model/provider fallbacks, and hard-coded paths resolved?
9. What services, timers, reconciliation loops, scripts, and manual commands can ingest, summarise/embed, write Chroma, mutate checkpoints, acquire locks, or restart another process?
10. Where are candidate crash/fault-injection seams, without invoking them?
11. Which proposed contracts already exist, are insufficient, are missing, or can follow the isolated slice?
12. What revised effort range is defensible for isolated JSONL implementation plus scratch proof only?

## Required evidence package

### A. Source-to-write call path

Map:

`source event → watcher/CLI → adapter → parser → chunker → summary/embed/dedupe → Chroma write/upsert → prune → processed/checkpoint → completion/reconciliation`

Mark every edge for side effects, configuration inputs, locks, subprocesses, and external calls.

### B. Identity and compatibility matrix

| Artifact | Current identity | Identity inputs | Whole-file dependency | Provenance link | Reuse status | Migration implication |
|---|---|---|---|---|---|---|
| Source/generation |  |  |  |  |  |  |
| Record/message |  |  |  |  |  |  |
| Chunk |  |  |  |  |  |  |
| Summary |  |  |  |  |  |  |
| Embedding/unit |  |  |  |  |  |  |
| Deduplication |  |  |  |  |  |  |

### C. Publication, prune, and completion chain

Identify:

- output publication point;
- deletion/prune selector and scope;
- write/prune ordering;
- checkpoint or processed-log update;
- completion marker;
- component that trusts completion;
- failure windows that could expose mixed generations or premature completion.

If atomic activation is not established, classify it as `unknown` and recommend scratch fault testing.

### D. Configuration and provider precedence

Trace precedence among:

- CLI arguments;
- environment variables;
- config files;
- defaults;
- adapter defaults;
- model/provider fallbacks;
- hard-coded paths.

Record whether any production path, lock, store, model client, or provider can be opened before isolation checks would run.

### E. Runtime-capable process inventory

| Process/path | Can ingest? | Can summarise/embed? | Can write Chroma? | Can mutate checkpoint? | Can acquire shared lock? | Evidence/status |
|---|---:|---:|---:|---:|---:|---|
| Watcher |  |  |  |  |  |  |
| Refine |  |  |  |  |  |  |
| Reconciliation |  |  |  |  |  |  |
| Timer/script |  |  |  |  |  |  |
| Manual CLI |  |  |  |  |  |  |

Do not change service state. If current running state cannot be established safely, mark it `unknown`.

### F. Test and fault-seam inventory

Classify relevant tests as:

- pure unit;
- scratch-store integration;
- local-model;
- network-capable;
- provider-capable;
- production-path-capable;
- unknown.

For any historical result treated as `observed`, provide tested revision, result, isolation boundary, and proposition correspondence. Otherwise use `inferred` or `unknown`.

Identify candidate crash seams but do not execute them during this audit.

### G. Contract and architecture-change budget

Classify each proposed contract as **existing and reusable**, **existing but insufficient**, **missing and required before implementation**, or **can follow the first isolated slice**.

For each, record whether it requires:

`schema change? / storage migration? / new metadata only? / code-only?`

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

## Decision rule

Choose exactly one final disposition.

### A — Proceed to isolated implementation planning

Repository facts are sufficient to specify the JSONL slice, and every implementation-critical safety assumption is resolved or supported by trustworthy observed evidence. Non-blocking unknowns may remain only when they are explicitly outside the authorised first slice and cannot invalidate its safety assumptions.

This disposition still authorises no production routing, `.crush` processing, real-source canary, provider use, migration, or corpus rewrite.

### B — Proceed with bounded scratch prototype first

The architecture is plausible, but material runtime behavior—such as crash replay, publication atomicity, invalidation behavior, or provider/path isolation—remains unknown. The prototype must use a fresh temporary root, dedicated subprocess, deterministic fakes, no network, isolated locks, and no production resources.

### C — Do not proceed

A fundamental identity, publication, isolation, provider, or migration issue prevents safe isolated work.

## Defensible constraints

- Do not index or open the production corpus to answer audit questions.
- Do not call paid or nonlocal providers.
- Do not treat raised memory caps as the indexing-cost fix.
- Do not treat JSONL success as a solution for the active SQLite/`.crush` source.
- Do not authorise destructive or irreversible corpus migration in the first slice.
- Do not assume existing IDs/provenance are reusable until audited.
- Do not assume full-rebuild fallback is safe without source-generation-safe publication or an equivalent activation protocol.
- Do not claim production economics, semantic model quality, or SQLite correctness from synthetic JSONL tests alone.

## Required final response

Return exactly these sections:

### Overall verdict

`PASS`, `PASS WITH CONDITIONS`, or `FAIL`

State whether the audit produced enough evidence for disposition A, requires disposition B, or requires disposition C.

### Evidence summary

Provide the source-to-write map, identity/provenance findings, publication/prune/completion ordering, provider/configuration precedence, process inventory, test-trust classification, and contract-readiness classification. Mark material findings `observed`, `inferred`, or `unknown`.

### Implementation-critical unknowns

List each unresolved unknown and state whether it blocks A, requires B, or is genuinely outside the first slice.

### Required corrections or blockers

List only corrections or blockers that must be addressed before the next disposition.

### Recommended next action

Choose one:

- isolated implementation planning;
- bounded scratch prototype first;
- stop pending a fundamental correction.

Name the owner/lane and exact evidence the next action must produce.

### Effort estimate and confidence

Give the narrowest defensible effort range for the authorised next step. Mark confidence `high`, `medium`, or `low`, and identify the dominant uncertainty.

### Non-mutation confirmation

State explicitly whether the audit opened any production resource, changed any service, indexed any source, called any provider, mutated any corpus/state, or committed any code. The expected answer is “no” for every item.

## Review boundary

This is an adversarial readiness audit only. Do not modify ConvMem, start or stop services, index any source, construct production clients, call providers, inspect production data paths, mutate the production corpus, migrate storage, create implementation commits, or treat the audit as implementation authorization.
