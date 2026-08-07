# ChatGPT — Next Top Two Retrieval Problems and Execution Plan

**Date:** 2026-07-15
**Baseline:** `main` after PR #38, merge commit `48e816f`
**Status:** Proposed for inter-model debate and Ryan HITL selection
**Scope:** Retrieval observability and verification only. No new reranker, hybrid retrieval, boosting rule, or citation-diversity behavior in this arc.

## Executive recommendation

The two highest-value problems remaining are:

1. **The `ask` retrieval pipeline is still opaque.** The final `results` and citations do not show where a candidate entered, moved, survived, or disappeared. Implement a bounded, versioned `ask(trace=True)` contract.
2. **Retrieval changes still lack a dedicated regression gate.** The repository has synthesis-answer evaluation, but not a deterministic stage-aware retrieval evaluation that can prove a ranking or filtering change improved the intended cases without damaging others.

These should be executed in that order. Traceability provides the evidence surface; the retrieval evaluator turns that surface into a repeatable gate.

Do **not** begin another retrieval-behavior experiment until both are operational.

---

# Problem 1 — Retrieval decisions are not explainable

## Why this is now the top problem

PR #38 corrected two observed failures:

- uncapped recent decisions could occupy the evidence context;
- nested `docs/inter-model/**` documents could be skipped by ingest recognition.

Those fixes were found through manual inspection and debate. The next failure may happen at any of these distinct stages:

1. standalone retrieval-query construction;
2. semantic query candidate generation;
3. evidence reranking;
4. ledger-id deduplication;
5. recent-decision filtering, deduplication, and cap;
6. semantic/recent blending;
7. superseded-decision filtering;
8. final `top_k` selection;
9. context truncation;
10. synthesis and citation use.

Today, the caller sees late output but cannot reliably determine which stage removed or promoted a source. That makes every retrieval defect more expensive to diagnose and encourages speculative ranking changes.

## Recommended outcome

Add an optional trace to the Python `ask()` contract, then expose it through CLI and MCP without changing default output.

```python
ask(
    question,
    ...,
    trace=False,
    trace_limit=20,
)
```

When `trace=False`, behavior and returned payload must remain backward-compatible.

When `trace=True`, add a bounded trace object:

```json
{
  "trace": {
    "schema": "convmem.ask.trace.v1",
    "request": {},
    "stages": [],
    "final_context": {},
    "citation_map": []
  }
}
```

## Required trace contract

### Request metadata

Record:

- original question;
- expanded `retrieval_query`;
- `top_k` and internal `fetch_k`;
- `raw`, `evidence`, `domain`, and `site`;
- evidence recency configuration used;
- trace limit and whether any stage was truncated.

### Candidate identity

Every candidate entry should use a stable diagnostic identity where available:

- result id;
- `ledger_id`;
- title;
- type;
- domain and site;
- source path;
- semantic score;
- evidence/rank score and boost fields;
- `evidence_status`;
- rank at that stage.

Do not copy full documents into the default trace. A short bounded snippet is acceptable only if necessary. Prefer metadata because traces may be passed through MCP clients.

### Required stages

At minimum:

1. `semantic_initial`
2. `evidence_reranked` when evidence mode is enabled
3. `ledger_deduped`
4. `recent_considered`
5. `recent_after_scope`
6. `recent_after_dedupe`
7. `recent_capped`
8. `blended_candidates`
9. `superseded_filtered`
10. `final_context`
11. `citations_returned`

A stage may be marked `skipped` with a reason rather than omitted. Stable stage names matter more than an elegant first implementation.

### Drop and movement reasons

Where a candidate disappears or moves materially, record a machine-readable reason, such as:

- `duplicate_ledger_id_semantic_wins`
- `domain_mismatch`
- `site_mismatch`
- `recent_budget_cap`
- `superseded_parent`
- `outside_top_k`
- `context_char_limit`

This is more valuable than merely dumping ten arrays.

## Design boundary

The trace must observe current behavior, not redesign it.

Explicit non-goals:

- no new retrieval algorithm;
- no score normalization change;
- no new recent-decision quota;
- no new citation-diversity policy;
- no automatic query rewriting beyond the current history expansion;
- no default MCP payload growth;
- no durable logging of user questions or full retrieved documents.

## Preferred internal shape

Extract the pre-synthesis pipeline into a retrieval-only function used by `ask()`:

```python
retrieve_for_ask(...) -> RetrievalBundle
```

The bundle should contain:

- final results;
- formatted context inputs or enough information to build them;
- citations;
- confidence/warning inputs;
- optional trace.

This is not a general architecture rewrite. It is a bounded extraction that prevents the trace implementation and the later evaluator from duplicating retrieval behavior or invoking the LLM.

## MCP and CLI surface

### MCP

Add `trace: bool = False` to the existing `ask` tool.

- `trace=False`: exact existing response shape.
- `trace=True`: append the versioned trace.
- Do not make trace the default for agents.
- Keep `trace_limit` fixed initially or expose it with a conservative maximum.

A separate `ask_trace` tool is acceptable only if FastMCP/client schema compatibility makes an optional parameter unsafe. The preferred contract is one tool with an optional trace.

### CLI

Add:

```bash
convmem ask "..." --trace
```

Human-readable output may summarize stage counts and drop reasons. A JSON mode must preserve the complete bounded trace for comparison and evaluation.

## Tests and acceptance criteria

### Unit and contract tests

- Default `ask()` output is unchanged when trace is off.
- Default MCP `ask` JSON is unchanged when trace is off.
- Trace schema and stage names are stable.
- Candidate ranks and reasons are correct on controlled fixtures.
- Semantic overlap beats recent-decision injection and records the reason.
- Domain/site mismatch is visible in trace.
- Minority-cap exclusions are visible in trace.
- Superseded parents are visibly removed at the correct stage.
- Trace bounds are enforced.
- Full document bodies and secrets are not leaked.

### Live acceptance probes

Use at least these observed classes:

1. purge-drift query from PR #38;
2. nested debate-document query;
3. domain-scoped query;
4. site-scoped query;
5. decision supersession chain;
6. no-match or weak-match query.

For each probe, the operator must be able to answer:

- Was the desired source retrieved initially?
- If yes, where did it disappear or lose rank?
- Which recent decisions were considered, admitted, and capped?
- Which exact units reached synthesis?

## Suggested execution tasks

### T0 — Close the prior repair gate

Before new implementation:

- run the full test suite;
- run `convmem doctor`;
- record the PASS against merge commit `48e816f` or the current clean `main` head.

This is a prerequisite, not one of the two new feature priorities.

### T1 — Contract debate

Produce one agreed trace-schema document. R1 should attack ambiguity, path leakage, score naming, and stage ordering. Kiro should verify the proposed stages against actual `ask.py`, `query.py`, and `evidence.py` paths.

### T2 — Retrieval-bundle extraction

Extract current retrieval behavior without changing output. Add characterization tests before moving logic.

### T3 — Trace collection

Instrument stage snapshots, movement/drop reasons, and bounds.

### T4 — CLI/MCP exposure

Expose trace only through explicit opt-in. Prove default compatibility.

### T5 — Verification and independent audit

Run focused tests, full suite, doctor, and the six live probes. Codex or another read-only lane should inspect whether every claimed stage maps to real production behavior.

---

# Problem 2 — Retrieval quality has no dedicated regression gate

## Why this is second

`scripts/eval-synthesis.py` evaluates answer behavior: required facts, citation syntax, abstention, and optional judge scoring. That is useful, but it cannot isolate retrieval quality from synthesis quality.

A failed answer may mean:

- the right source was never retrieved;
- it was retrieved but dropped later;
- it reached context but synthesis ignored it;
- the golden answer expectation is stale.

A retrieval change can also improve one observed query while silently harming domain scope, supersession, negative controls, or ordinary semantic recall.

The roadmap already states: **do not ship hybrid retrieval without eval regression**. A dedicated retrieval evaluator is therefore the control needed before later ranking work.

## Recommended outcome

Create a separate retrieval evaluator that consumes the same production retrieval pipeline and trace schema but does not invoke synthesis.

Suggested entrypoint:

```bash
python3 scripts/eval-retrieval.py
```

Keep it distinct from `eval-synthesis.py`. Retrieval and synthesis should be diagnosable and gateable independently.

## Two-layer evaluation design

### Layer A — Hermetic hard gate

Use a controlled fixture corpus or mocked candidate pools to prove exact pipeline contracts:

- stage ordering;
- ledger-id deduplication;
- semantic-wins overlap behavior;
- recent-decision cap;
- domain/site filtering;
- superseded-decision removal;
- top-k and context selection;
- trace drop reasons.

This layer must be deterministic and CI-safe.

### Layer B — Live corpus canary

Use real Chroma and curated queries representing actual convmem work. This layer detects corpus-level drift and is expected to change when the corpus legitimately evolves.

It should:

- emit a provenance-stamped report;
- compare against an approved baseline;
- distinguish true regression from stale expectation;
- require Ryan HITL to update expected ids or baseline thresholds;
- avoid silently rewriting baselines.

The live canary may initially be a local/manual gate if CI cannot access the corpus.

## Proposed golden retrieval schema

Create `tests/fixtures/golden_retrieval.jsonl` or a similarly explicit location.

Each row should support fields such as:

```json
{
  "id": "ret_purge_drift",
  "question": "...",
  "evidence": true,
  "domain": null,
  "site": null,
  "top_k": 5,
  "expected_any_ledger_ids": ["obs_...", "dec_prop_..."],
  "expected_any_source_paths": ["docs/..."],
  "forbidden_ledger_ids": [],
  "max_recent_in_final": 2,
  "min_semantic_in_final": 3,
  "expected_drop_reasons": []
}
```

Do not require every test to use every field. Prefer explicit expectations over a single opaque score.

## Metrics

At minimum report:

- Hit@k for expected ids or source paths;
- reciprocal rank of the first acceptable result;
- desired-source survival by stage;
- number and proportion of recent decisions in final context;
- scope leakage count;
- forbidden/superseded result count;
- no-match control correctness;
- trace-schema/version and corpus provenance.

A mean score alone is insufficient. The report must identify which case and stage regressed.

## Initial case set

Seed the evaluator from failures and invariants already encountered, not invented benchmark trivia:

1. **Purge-drift topical recall** — semantic sources remain present under evidence mode.
2. **Recent-decision budget** — final top five contains at most the intended recent minority.
3. **Nested debate ingest/retrieval** — a nested planning document is retrievable after indexing.
4. **Snapshot exclusion** — `.kiro`/`snapshots` copies do not become active indexed evidence.
5. **Domain scope** — mismatched domain candidates do not leak into scoped output.
6. **Site scope** — mismatched site candidates do not leak into scoped output.
7. **Ledger identity overlap** — semantic candidate survives over duplicate recent injection.
8. **Decision supersession** — parent is absent when the replacing child is present.
9. **Weak/no-match control** — no irrelevant confident context is manufactured.
10. **Evidence-off ordinary recall** — default CLI behavior retains known topical sources.

Begin with 8–12 strong cases. Do not chase a large benchmark before the schema and failure reporting are trustworthy.

## Baseline and gate policy

- Hard-gate exact contract invariants from the hermetic layer.
- Hard-gate forbidden leakage and superseded-parent violations.
- Treat live Hit@k/MRR regressions as blocking only when corpus provenance matches the approved baseline.
- When provenance differs, classify the result as `STALE_BASELINE` or equivalent rather than PASS/FAIL guessing.
- Baseline updates require a written reason and Ryan approval.
- Never let an LLM judge control the retrieval hard gate.

## Relationship to existing synthesis evaluation

Keep `scripts/eval-synthesis.py` intact but revise assumptions made obsolete by PR #38. Its current comment says evidence mode buries topic-specific targets; that was true for the failure being repaired and should now be verified rather than preserved as a permanent design assumption.

The intended stack becomes:

1. retrieval contract tests;
2. hermetic retrieval evaluation;
3. live retrieval canary;
4. synthesis deterministic checks;
5. optional independent judge, advisory only.

## Suggested execution tasks

### T6 — Evaluation contract

Agree on fixture schema, metrics, provenance fields, and blocking policy.

### T7 — Hermetic evaluator

Build controlled cases against `retrieve_for_ask()` and trace output. No model or network dependency.

### T8 — Live corpus canary

Add the initial 8–12 real queries and machine-readable report. Reuse existing provenance/classification helpers where appropriate rather than creating a parallel framework.

### T9 — Baseline and failure reporting

Create an approved baseline and prove that a deliberate ranking/filter break produces a precise failing case and stage.

### T10 — Integrate with verification ritual

Document when to run retrieval eval:

- before and after any query, rerank, evidence, dedupe, scope, supersession, or context-budget change;
- before hybrid retrieval work;
- during release/major milestone verification.

Do not add it to every fast unit-test invocation if live Chroma makes it slow or environment-dependent. Keep hermetic tests fast and make the live canary an explicit higher gate.

---

# Ordered delivery plan

| Order | Deliverable | Behavior change allowed? | Gate |
|---|---|---:|---|
| 0 | PR #38 full-suite + doctor closure | No | PASS recorded |
| 1 | Versioned trace contract | No | Ryan HITL |
| 2 | Retrieval-only bundle extraction | No | Characterization tests |
| 3 | `ask(trace=True)` internal trace | No ranking change | Trace contract tests |
| 4 | CLI/MCP opt-in exposure | No default output change | Compatibility tests |
| 5 | Hermetic retrieval evaluator | No | Deliberate-break proof |
| 6 | Live retrieval canary + baseline | No | Provenance-aware report |
| 7 | Select next retrieval improvement | Only after evidence | New debate/plan |

## Stop conditions

Stop and return to debate if:

- extracting `retrieve_for_ask()` changes current ranked output;
- stage names cannot be mapped consistently to production behavior;
- trace requires exposing full private documents or unbounded local paths;
- MCP default response changes when trace is false;
- live evaluation expectations cannot distinguish corpus drift from code regression;
- the implementation starts adding ranking behavior before the gates exist.

---

# Recommended model lanes for this debate

This assigns work to existing capabilities; it does not create new roles.

- **ChatGPT:** architecture proposal and final synthesis of disagreements.
- **DeepSeek R1:** adversarial review of trace semantics, evaluator gaming, and false confidence.
- **Kiro:** repo-grounded mapping from proposed stages/tasks to actual files and tests.
- **Cursor:** execution runbook and implementation after HITL authorization.
- **Codex/read-only lane:** independent diff and acceptance-claim audit.
- **Ryan:** scope selection, baseline approval, and merge authorization.

## Questions for the other models

1. Is `retrieve_for_ask()` the smallest safe extraction, or can trace and evaluation share production logic without it?
2. Which trace fields could expose private corpus content or machine-specific paths, and what is the minimum useful redaction policy?
3. Should MCP use `ask(trace=True)` or a separate `ask_trace` tool for client compatibility?
4. Which metrics should be hard gates versus advisory for a mutable local corpus?
5. What exact provenance fingerprint is sufficient to distinguish code regression from corpus drift?
6. Which initial golden cases are strongest enough to block a retrieval merge?
7. Can a deliberate production-code break be demonstrated to fail the evaluator without also breaking unrelated unit tests?

# Final recommendation

Authorize **Problem 1: bounded retrieval traceability** first. Approve **Problem 2: dedicated retrieval regression evaluation** as the immediate dependent phase, with its contract debated in parallel but implementation beginning only after the trace schema and retrieval-only production path are stable.

The next behavior-changing retrieval idea should be selected from trace and evaluation evidence, not intuition.
