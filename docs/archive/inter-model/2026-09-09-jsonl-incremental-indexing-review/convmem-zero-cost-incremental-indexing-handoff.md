# ConvMem Zero-Cost Incremental Indexing — Second-Opinion Handoff

> Status: **open review request** — We want to improve ConvMem’s indexing without spending money on live re-indexing or risking the production corpus. This handoff requests an independent safety review of the proposed development workflow.

## TL;DR

ConvMem currently performs whole-source work when a watched source changes. A small append can trigger full parsing, rechunking, summarisation, embeddings, distillation, deduplication, and Chroma writes. The immediate goal is to develop the incremental-indexing fix while the live watcher and production indexing remain paused.

Please determine whether the workflow below can provide meaningful correctness evidence with **zero live-corpus indexing and zero paid-model calls**, and identify any hidden path, service, or test that could still spend money or mutate production state.

## Reviewer role

Act as an independent senior reviewer for cost control, test isolation, and data safety. Do not edit the ConvMem repository or this handoff. Return a verdict and concrete corrections. Treat “no production indexing” and “no paid API calls” as hard requirements, not preferences.

## Ground truth

The repository is `alanmz-crypto/convmem`.

Relevant engineering evidence:

- [Issue #286 — Make changed-file indexing incremental at chunk/append level](https://github.com/alanmz-crypto/convmem/issues/286) reports that a small file change causes whole-file reprocessing and proposes cursor/prefix validation, affected-chunk processing, and reuse of unchanged results.
- [Issue #268 — Watch OOM: full-file re-index on every append](https://github.com/alanmz-crypto/convmem/issues/268) records repeated memory failures and identifies the raised 12G child cap as interim containment rather than the durable fix.
- The currently narrowed watched relocation source is the SQLite database:
  `/home/lauer/Projects/SubProjects/Relocating_Habitat/Shipping_Transportation/.crush/crush.db`.
- Ordinary Markdown files in that relocation folder are not active watcher inputs because plain `.md` has no current parser on the watch path.
- The production ConvMem corpus is shared and contains roughly 40,000 active knowledge units. It must not be used for routine development tests.

## Proposed no-cost development workflow

### 1. Stop live automatic work

Before implementation or tests:

- keep `convmem-watch` stopped;
- stop or isolate any background `refine` process that can call summarisation or mutate Chroma;
- do not run `convmem index` against production paths;
- do not run `convmem record --approve-last` or other durable production writes;
- verify test commands cannot resolve to the production Chroma directory, processed log, export, or API configuration.

### 2. Use an isolated test configuration

Create a temporary or test-only ConvMem configuration whose paths point to:

- a temporary Chroma directory;
- a temporary processed/checkpoint file;
- temporary source fixtures;
- no production inventory or source roots;
- no paid summarisation endpoint or production API key.

The test configuration must fail closed if a production path is accidentally supplied.

### 3. Use synthetic sources first

Build small deterministic fixtures covering:

- initial JSONL ingest;
- one-record append;
- multi-record append;
- append ending in a partial record;
- exact chunk-boundary append;
- prefix mutation;
- truncation;
- source replacement/rotation;
- parser/chunker/model/config fingerprint changes;
- crash at each commit stage;
- append arriving during a run.

Fixtures should be large enough to demonstrate reuse of old chunks but small enough to run repeatedly without external services.

### 4. Mock or localise expensive transformations

Unit and integration tests should use deterministic fake summarisation, fake embeddings, and fake deduplication where the behavior under test does not require the real model. If a real embedding is needed, use a local model and a scratch store. No test should call DeepSeek or another paid provider.

Record counters for:

- parser calls;
- summary calls;
- embedding calls;
- deduplication calls;
- reused chunks;
- new chunks;
- reprocessed chunks;
- full rebuilds;
- fallback reasons.

### 5. Compare against a scratch full rebuild

For each fixture state, compare:

- source-record coverage;
- authoritative unit IDs;
- provenance;
- summary/chunk boundaries;
- duplicate count;
- checkpoint state;
- fallback reason;

between incremental processing and a clean full rebuild in the **temporary** store. The comparison must not touch production data.

## Proposed implementation boundary

Phase 1 should support only explicitly append-only JSONL adapters. It should define source-neutral concepts for source identity/generation, committed record boundary, transform fingerprint, invalidation frontier, checkpoint state, and fallback reason.

The implementation must:

1. persist a checkpoint only after required derived outputs are safely committed;
2. validate the source generation and committed prefix before continuation;
3. process only complete records through a selected high-water mark;
4. calculate the actual affected dependency frontier rather than assuming one boundary chunk;
5. make replay after a crash deterministic and idempotent;
6. never prune on a verified append;
7. fall back to the established full path on uncertainty;
8. remain disabled for production routing until the scratch tests and canary pass.

SQLite/`.crush` support is a separate phase. JSONL test success must not be presented as fixing the active SQLite watcher source.

## Suspected weak links to challenge

| ID | Assumption | Required challenge |
|---|---|---|
| C1 | Stopping the watcher is sufficient to prevent production indexing. | Check refine, reconciliation, timers, manual scripts, service restart behavior, and queued work. |
| C2 | A scratch config prevents production mutation. | Require path assertions and fail-closed checks for Chroma, processed log, inventory, exports, and source roots. |
| C3 | Mocked models provide useful safety evidence. | Separate state-machine/data-integrity evidence from model-quality evidence; identify what still requires a later local/real canary. |
| C4 | Local embeddings are cost-free and harmless. | Check model downloads, GPU/CPU pressure, external fallback behavior, and whether the embedding host can make network calls. |
| C5 | Scratch full rebuild comparison is authoritative. | Ensure the comparison uses equivalent parser/chunker/fingerprint inputs and detects missing, duplicate, or unstable IDs. |
| C6 | Crash tests cannot affect production. | Verify every fault-injection test uses isolated locks, paths, processes, and temporary stores. |
| C7 | The implementation can be developed without indexing real sources. | Identify any behavior that depends on real transcript scale, malformed records, concurrent writers, or actual SQLite semantics. |
| C8 | The cost gate can be measured without paid calls. | Define proxy counters for tests and defer real cost measurement to one explicitly approved canary. |
| C9 | Paused sources can safely resume later. | Check restart reconciliation, stale checkpoints, pending events, source changes while paused, and fallback behavior. |
| C10 | The 3–5 day estimate remains valid under these safety requirements. | Re-estimate after isolation, checkpoint, identity, crash, and frontier work are included. |

## Required reviewer questions

1. What exact commands/services must be stopped or isolated to guarantee no background production indexing?
2. What path assertions should the test harness enforce before opening any store or source?
3. How can paid-provider calls be blocked at the configuration and test level, not merely by convention?
4. Which tests prove data-integrity safety without real model outputs?
5. Which tests require real local models, large fixtures, or a real source canary?
6. What is the minimum acceptable scratch-corpus comparison before production routing is considered?
7. How should a failed test clean up temporary stores and locks without touching production locks?
8. What does “paused safely” mean for changes that accumulate while the watcher is stopped?
9. What is the smallest genuinely useful implementation slice under zero-cost constraints?
10. What new risks are introduced by keeping the old full-rebuild fallback available?

## Defensible core — protect unless disproved

- Development can proceed without indexing the live corpus.
- Synthetic fixtures and deterministic transformation fakes can test checkpointing, replay, invalidation, fallback, and duplicate/loss invariants.
- The production watcher should remain paused while the new path is unreviewed.
- A temporary Chroma/checkpoint configuration is safer than using a copy of the production corpus as the default test target.
- The first real-source canary should be the final, explicitly approved step—not a prerequisite for ordinary implementation.
- SQLite/`.crush` must remain separately gated.

## Required verdict format

Return exactly these sections:

### Overall verdict

`PASS`, `PASS WITH CONDITIONS`, or `FAIL`

State whether the proposed workflow can proceed without production indexing or paid API calls.

### Claim-by-claim verdicts

| ID | Verdict (`agree` / `refute` / `restate`) | Evidence or reasoning | Corrected formulation if needed |
|---|---|---|---|
| C1 |  |  |  |
| C2 |  |  |  |
| C3 |  |  |  |
| C4 |  |  |  |
| C5 |  |  |  |
| C6 |  |  |  |
| C7 |  |  |  |
| C8 |  |  |  |
| C9 |  |  |  |
| C10 |  |  |  |

### Blocking conditions

Separate blockers for beginning isolated implementation from blockers for the later real-source canary.

### Recommended zero-cost test plan

Give an ordered plan naming the test boundary, service isolation, path guards, fake/local model strategy, fault-injection tests, and evidence required before any paid or live canary.

### Confidence

State `high`, `medium`, or `low`, with one sentence explaining what remains unverified.

## Review boundary

This is a safety and cost-isolation review only. Do not modify ConvMem, start or stop services, index any source, call a paid provider, mutate the production corpus, or claim that incremental indexing is production-ready.
