# ConvMem Readiness Audit — Final Position for Independent Check

> Status: **review requested** — This document states my final position before the read-only implementation-readiness audit. Please challenge the procedure and decision boundary once more.

## My position

The next safe action is a strictly non-mutating audit of the ConvMem repository and its declared runtime configuration. The audit is not implementation, not a scratch prototype, and not a production verification run.

The audit should answer what can be established statically and identify what must remain a bounded scratch-prototype question. It must never convert an untested runtime assumption into implementation authority.

## Hard boundaries

The audit may:

- read source files, tests, configuration text, service-unit definitions, timer definitions, and shell scripts;
- trace call paths with static search and code reading;
- inspect Git history and existing issue/design text read-only;
- inspect declared production paths from repository, configuration, and service definitions;
- classify existing tests by their apparent isolation and side effects.

The audit may not:

- run `convmem index`, `convmem add`, `convmem record`, refine, reconciliation, or watch;
- instantiate Chroma, model, provider, adapter, lock, or ingest clients;
- open production Chroma, `.crush`, processed state, inventory, exports, or production locks, even read-only;
- run existing tests unless they are first proven pure or hermetic and the run is explicitly classified as scratch-only;
- start, stop, restart, enable, disable, or reconfigure services;
- make paid or nonlocal provider calls;
- create a production branch, commit code, migrate data, or alter configuration.

The audit must not probe, enumerate, resolve through, `stat`, or otherwise inspect
production corpus/store paths merely to establish that they exist. Production
locations must be derived from repository, configuration, and service declarations,
or from independently safe read-only evidence already surfaced elsewhere.

If a question cannot be answered within these boundaries, the correct result is `unknown` plus a bounded scratch-prototype recommendation.

## Facts the audit must establish

1. A representative supported append-only JSONL adapter/source exists, preferably through an existing fixture rather than a production file.
2. Current source, record, chunk, summary, embedding/unit, provenance, deduplication, and Chroma identities are traceable in code.
3. Whole-file hashing’s exact role in skip, identity, provenance, pruning, and completion is known.
4. The actual chunker and downstream transformation dependencies reveal the possible append invalidation frontier.
5. Current output, prune, processed/checkpoint, and completion ordering is known from static code paths.
6. Existing write/upsert behavior can be classified as replay-safe, replay-unsafe, or unknown without executing it.
7. Provider/model/configuration precedence and fallback behavior are known.
8. Every declared process, timer, script, or CLI path capable of production ingest or writes is listed.
9. Global/shared locks and state paths are identified from configuration and code.
10. Candidate crash/fault-injection seams are identified without invoking them.

## Evidence discipline

Every material finding must use this format:

| Finding | Evidence | Status | Side-effect classification | Consequence |
|---|---|---|---|---|
| Example: checkpoint advances after writes | `ingest.py:Lx-Ly` | `observed` / `inferred` / `unknown` | pure/read-only, filesystem read, lock, write, spawn, network, or uncertain | safe to plan / scratch prototype / blocker |

Definitions:

- **Observed:** directly established from source, configuration, or trustworthy read-only system metadata.
- **Inferred:** a reasoned interpretation that still depends on an untested assumption.
- **Unknown:** not established safely; must not be used as an implementation premise.

The audit must not report “safe,” “atomic,” “idempotent,” “no migration,” or “no cost” unless the evidence actually establishes that exact proposition.

The existence or source code of a test does not by itself establish the behaviour it
asserts. A historical test result may support `observed` only when its exact tested
revision, execution result, relevant isolation boundary, and correspondence to the
proposition are established. Otherwise classify the behaviour as `inferred` or
`unknown`.

## Required evidence package

### A. Source-to-write call path

Map:

`source event → watcher/CLI → adapter → parser → chunker → summary/embed/dedupe → Chroma write/upsert → prune → processed/checkpoint → completion/reconciliation`

For each edge, identify side effects, configuration inputs, locks, subprocesses, and external calls.

### B. Identity and compatibility matrix

| Artifact | Current key/identity | Identity inputs | Whole-file dependency | Provenance link | Reuse status | Migration implication |
|---|---|---|---|---|---|---|
| Source/generation |  |  |  |  |  |  |
| Record/message |  |  |  |  |  |  |
| Chunk |  |  |  |  |  |  |
| Summary |  |  |  |  |  |  |
| Embedding/unit |  |  |  |  |  |  |
| Deduplication |  |  |  |  |  |  |

### C. Publication and completion chain

Identify:

- output publication point;
- prune/delete scope and ordering;
- checkpoint/processed-log update;
- completion marker;
- component that trusts completion;
- failure windows that could expose mixed generations, lose units, duplicate units, or falsely mark completion.

If atomic activation is not established, classify it as `unknown` and recommend scratch fault testing.

### D. Configuration and provider precedence

Trace precedence among:

- CLI flags;
- environment variables;
- config files;
- defaults;
- adapter defaults;
- model/provider fallback;
- hard-coded paths.

Record whether any path or provider can be opened before isolation checks execute.

### E. Runtime-capable process inventory

List watcher, refine, reconciliation, timers, scripts, and manual commands. For each, record whether it can ingest, call a model, write Chroma, mutate checkpoints, acquire shared locks, or restart another process.

Running-state evidence may be inspected only if it is available read-only and without changing service state. Otherwise mark it `unknown`.

### F. Test and fault-seam inventory

Classify existing tests as pure unit, scratch integration, local-model, network-capable, provider-capable, production-path-capable, or unknown. Identify candidate crash points but do not execute them in this audit.

## Decision rule

The audit must finish with exactly one disposition:

### A — Proceed to isolated implementation planning

Repository facts are sufficient to specify the JSONL slice, and no unresolved identity, publication, isolation, or migration blocker remains. This still authorizes no code, production routing, `.crush`, canary, provider use, or migration.

Non-blocking unknowns may remain only if they are explicitly outside the authorized
first implementation slice and cannot invalidate its safety assumptions.

### B — Proceed with bounded scratch prototype first

The architecture is plausible, but crash replay, publication atomicity, invalidation behavior, or another material property cannot be established statically. The prototype must use a fresh temporary root, dedicated subprocess, deterministic fakes, no network, and no production resources.

### C — Do not proceed

A fundamental identity, publication, isolation, provider, or migration issue prevents safe isolated work.

## My specific hypotheses for recheck

| ID | Hypothesis | Required challenge |
|---|---|---|
| P1 | The audit can be completed without opening any production resource. | Identify any indirect initialization or helper inspection that violates this. |
| P2 | Static tracing can select the correct JSONL target and bound the implementation shape. | Show any key behavior that requires real execution before even planning. |
| P3 | Crash safety and publication atomicity should be classified as unknown unless existing hermetic evidence proves them. | Identify a valid reason static evidence alone is sufficient. |
| P4 | No destructive migration is an authorization constraint, not a repository fact. | Check whether the wording still accidentally assumes compatibility. |
| P5 | A separate scratch prototype is the right response to unresolved runtime behavior. | Identify any safer or smaller evidence path. |
| P6 | The audit can produce a useful estimate, but not a firm promise, unless the prototype is unnecessary. | Challenge whether any estimate is premature. |
| P7 | JSONL remains the best first architecture target only if an existing supported adapter/fixture is confirmed. | Challenge whether SQLite must come first because it is the active cost driver. |
| P8 | Leaving the watcher paused is safe only after resume/reconciliation semantics are documented or explicitly treated as a later gate. | Identify any loss risk from the pause itself. |

## Questions for the independent reviewer

1. Is this audit genuinely read-only, or does any proposed inspection still risk opening production state?
2. Are the evidence statuses and side-effect classifications precise enough to prevent overclaiming?
3. Are the identity, publication, prune, completion, and configuration checks sufficient before implementation planning?
4. Which questions should be downgraded to scratch-prototype gates immediately?
5. Is the A/B/C decision rule safe and unambiguous?
6. Is the JSONL-first hypothesis still justified after considering the active `.crush` SQLite source?
7. What important audit evidence or cost-control boundary is missing?

## Required verdict format

### Overall verdict

`PASS`, `PASS WITH CONDITIONS`, or `FAIL`

State whether this final audit position is safe to carry into the readiness audit.

### Hypothesis verdicts

| ID | Verdict (`agree` / `refute` / `restate`) | Reasoning | Corrected formulation if needed |
|---|---|---|---|
| P1 |  |  |  |
| P2 |  |  |  |
| P3 |  |  |  |
| P4 |  |  |  |
| P5 |  |  |  |
| P6 |  |  |  |
| P7 |  |  |  |
| P8 |  |  |  |

### Required corrections

List only corrections required before the read-only audit begins.

### Final disposition recommendation

Recommend A, B, or C and explain the decisive evidence.

### Confidence

State `high`, `medium`, or `low`, with one sentence explaining what remains unverified.

## Review boundary

This is a request to review an audit procedure. It authorizes no code change, service action, indexing, provider call, production resource access, migration, or implementation.
