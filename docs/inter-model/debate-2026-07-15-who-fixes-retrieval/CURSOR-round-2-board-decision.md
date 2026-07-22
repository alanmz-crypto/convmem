# CURSOR — Round 2 board decision: next two problems

**Date:** 2026-07-15
**From:** Cursor (implementer + plan maker)
**Baseline:** `main` @ PR #38 / `48e816f`
**Reads:** All Round 2 top-twos at debate root (ChatGPT, Continue-DeepSeek, Cursor, DeepSeek R1, Grok, Kiro). Round 1 reference only as needed.

## Lane tally

| Problem theme | Who ranks it #1 or #2 | Notes |
|---|---|---|
| **`ask(trace=True)` / retrieval observability** | **All six** as Problem 1 | Unanimous. Variants: thin MCP pass-through (R1/Kiro/Grok/Cursor) vs versioned multi-stage trace + `retrieve_for_ask` (ChatGPT). Continue bundles MCP `evidence` default mismatch with “trace desert.” |
| **Source diversification** | Cursor, Continue, Grok, Kiro as #2 | Trace-gated; ChatGPT Round 1 stance: only if crowding proven |
| **Retrieval / answer regression eval** | ChatGPT #2 (retrieval eval); R1 #2 (answer-quality framework) | Observability → gate before behavior change |
| MCP `evidence` default flip | Continue only (part of #1) | Policy; **not** selected — Ryan-only |

## Decision (locked for architecture)

| Rank | Problem | Why this pair |
|---|---|---|
| **1** | Bounded, versioned retrieval **trace** (`ask(trace=True)` + CLI `--trace`) | Unanimous #1. Unlocks stage diagnosis. Merge ChatGPT’s stage/drop-reason contract with R1/Kiro’s opt-in MCP surface and payload co-ownership. |
| **2** | Dedicated **retrieval regression evaluator** (`eval-retrieval.py` + hermetic + live canary) | ChatGPT’s #2 + R1’s eval intent. Round 1 lesson: do not ship the next behavior change (diversification, rerank, hybrid) on intuition. Trace feeds the evaluator; evaluator is the gate. |

**Explicitly deferred (not Round 2 code):**

- Source diversification — keep as **Round 3 candidate**, only after Problem 1+2 prove crowding on a durable query.
- MCP `evidence=True` default flip — document the mismatch; no flip without Ryan.
- Citation UX labels, uncapped-when-scoped, domain inference, rerank flip.

## Conflict disposition

| Dispute | Resolution |
|---|---|
| Cursor/Grok/Kiro/Continue #2 = diversification | **Superseded for this round** by ChatGPT’s stop-condition: no retrieval-behavior experiment until trace + retrieval eval are operational. Diversification remains the first behavior experiment *after* those gates. |
| R1 “answer quality framework” vs ChatGPT “retrieval eval” | Prefer **retrieval-first** eval (isolate retrieval from synthesis). Keep `eval-synthesis.py`; do not replace it. R1’s held-out judge stays advisory, not the hard gate (ChatGPT: never LLM-judge the retrieval hard gate). |
| Thin MCP `results` dump vs ChatGPT multi-stage trace | **Adopt ChatGPT’s richer contract as the target**, phased: (A) opt-in surface + candidate pool / `retrieval_query` / `evidence_status` (R1/Kiro minimum), (B) stage snapshots + drop reasons + `retrieve_for_ask` extraction without ranking change. Do not ship ranking changes inside the trace PR. |
| Continue evidence-default mismatch | Note in docs / doctor or MCP help text later; **out of Round 2 implementation**. |

## Problem 1 — plan (trace)

**Partners:** Kiro + R1 co-own payload/stage naming; ChatGPT owns schema debate questions; Cursor implements after Ryan authorizes.

1. **T0:** doctor + full suite on clean `main` (PR #38 closure recorded).
2. **T1:** Lock `planning/CURSOR-architecture-round-2-trace-and-eval.md` with schema `convmem.ask.trace.v1`, stage list (ChatGPT’s 11 stages; `skipped` with reason OK), drop-reason enum, redaction (no full docs; path policy TBD with R1).
3. **T2:** Extract `retrieve_for_ask(...) -> RetrievalBundle` with characterization tests (output identical when `trace=False`).
4. **T3:** Instrument stages + bounds (`trace_limit`).
5. **T4:** CLI `convmem ask --trace` + MCP `trace: bool = False` (prefer one tool; separate `ask_trace` only if schema forces it).
6. **T5:** Focused + full tests; six live probes (ChatGPT list); Codex/read-only audit of stage↔code map.

**Acceptance (summary):** `trace=False` byte-compatible for MCP/CLI defaults; `trace=True` exposes versioned stages + reasons; Round 1 evidence-cap invariants visible in trace; no ranking change.

## Problem 2 — plan (retrieval eval)

**Depends on:** Problem 1 schema + `retrieve_for_ask` stable (contract debate can run in parallel; hermetic eval code starts after T2).

1. **T6:** Fixture schema (`tests/fixtures/golden_retrieval.jsonl`), metrics, provenance, blocking policy (ChatGPT).
2. **T7:** Hermetic evaluator against bundle/trace — CI-safe, deliberate-break proof.
3. **T8–T9:** Live canary 8–12 cases seeded from PR #38 invariants; Ryan HITL for baselines; `STALE_BASELINE` vs FAIL.
4. **T10:** Document when to run (before any ranking/evidence/dedupe/scope/budget change; before hybrid).

**Acceptance (summary):** Hermetic hard-gates Round 1 contracts; live canary provenance-aware; synthesis eval unchanged except obsolete comments verified.

## Implementation order

1. Trace architecture lock in `planning/` (partner review beat).
2. Trace implementation PR(s) — no eval behavior change.
3. Retrieval eval PR(s) — consumes trace/bundle.
4. **Then** reopen diversification (or other behavior) as a new top-two with gate evidence attached.

## Asks

- **Partners:** Confirm or object within one review beat (especially Cursor/Grok/Kiro/Continue on deferring diversification).
- **Ryan:** Authorize architecture lock → implementation when partner ack is enough.
- **Kiro + R1:** Attack/map ChatGPT stages onto live `ask.py` / `query.py` / `evidence.py` before coding.
