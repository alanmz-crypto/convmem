# Reranker `NoneType` diagnostic plan

**Status:** plan-only, review-required. This document authorizes no code,
configuration, corpus, ledger, service, or deployed-checkout change.
**Branch PR title:** docs: freeze-safe analysis plans for C6 hold, standing checks, and retrieval gaps

**Review source:** Kiro design-review lane, reviewing the read-only failure from
`convmem "background synthesis pointer Phase 1 shipped Phase 2 deferred"`.
The deployed checkout remains frozen at
`76126e07a97187f68d925dd8b431d2d03967084f` through 2026-08-07 00:00 UTC.

## Observed failure and likely data flow

The query path reached `sentence_transformers.CrossEncoder.predict()` with a
pair containing `None`. The likely path is a Chroma result whose `document`
field is missing or `None`; the primary semantic-search path in `query.py`
passes the Chroma result to `rerank.py` without normalizing it. The
fallback-row and ledger-lookup paths already use a title or empty-string
fallback and are less likely causes.

This is a diagnostic hypothesis, not proof about any specific ledger unit. Do
not inspect production payloads to confirm it while the freeze holds.

## Future isolated tests

All tests must use synthetic candidates and a mocked CrossEncoder. They must
not load live Chroma, model weights, ledger data, or paths under the live data
root.

Synthetic candidate lists must use a fixed, documented ordering (for example,
insertion order), and mocked scores must be assigned in a fixed sequence so
diagnostic output is deterministic across runs and platforms.

1. `rerank()` receives a candidate with `document=None` and raises a
   descriptive `ValueError` naming the candidate, rather than exposing an
   opaque sentence-transformers exception.
2. `rerank()` accepts an empty-string document with mocked scores and preserves
   result count and ordering behavior for valid inputs. This is a compatibility
   check for the existing fallback, not a claim that empty content has useful
   relevance semantics; a future implementation may flag it separately without
   silently dropping the candidate.
3. `query_units()` receives a synthetic Chroma row with `document=None` and
   verifies the query-layer boundary normalizes it before reranking.
4. `rerank()` rejects a `None` query with a descriptive input error.
5. Existing reranker, query-hardening, evidence-rerank, and MCP-rerank tests
   pass unchanged as the regression baseline.

Patch `rerank.get_model` or the module singleton in every test so no model is
loaded. Patch the symbol where it is looked up; do not accidentally patch a
different import path.

## Proposed handling policy for a future implementation

- Validate `query` and candidate shape at `rerank()` entry and fail loudly with
  context for internal callers.
- At the `query.py` boundary, normalize a `None` document to the existing
  metadata-title-or-empty-string fallback so one malformed result does not
  break every user query.
- Emit a non-fatal diagnostic without query text, document content, or stable
  user identifiers when coercion occurs.
- Do not silently drop the candidate, which would change ranking bias without
  evidence.

The query-layer resilience guard is not a substitute for finding the ingest
source of the malformed result. Root-cause analysis must remain a separate,
payload-free investigation.

## Acceptance criteria

A future implementation is acceptable only when:

- all five tests pass in an isolated worktree;
- the existing regression files pass without modification;
- `None` produces a descriptive error at the direct reranker boundary;
- the query path survives a synthetic `document=None` row and records only a
  privacy-safe diagnostic;
- valid non-`None` inputs retain existing ranking behavior;
- no live-corpus imports, model downloads, network access, or runtime writes
  are introduced; and
- independent review confirms the exact revision and test output.

**Verdict: PASS WITH NOTES — safe to implement as a future isolated test/code
change after the freeze and Ryan authorization. No implementation is authorized
by this plan.**
