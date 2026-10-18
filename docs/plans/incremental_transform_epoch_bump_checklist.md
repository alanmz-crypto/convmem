# Incremental transform epoch bump checklist (Arc Codex #286)

Use this checklist when changing incremental transform behavior or inventoried
semantic inputs. A **compatible implementation change** does not bump
`transform_contract_version`. A **semantic change** does.

## Requires `transform_contract_version` bump

- Prompt template bytes (`llm.SUMMARIZE_PROMPT`, `distill.DISTILL_PROMPT`)
- Chunk size / overlap defaults used by the admitted Codex route
- Model identities that affect summarize/distill/embed requests
- Embedding dimension or normalization contract
- Parser / prefix / message selection or rendering limits
- ID, dedupe, provenance envelope, or prepared-payload interpretation contracts
- Any change that can alter chunk boundaries, selection, or transform output

## Does **not** require a bump

- New LLM sample from an otherwise unchanged request
- Coordinator bookkeeping unrelated to transform semantics
- R2b `implementation_revision` changes without semantic drift
- Deploy SHA, host, instrumentation, retry counters

## Process

1. Make the semantic change.
2. Bump `TRANSFORM_CONTRACT_VERSION` in `incremental_transform_contract.py`.
3. Refresh `PINNED_CONTRACT_INVENTORY_DIGEST` (re-run contract inventory tests).
4. Document compatibility in the PR (why reuse remains safe, or why not).
5. Extend hermetic tests in `tests/test_incremental_transform_compatibility.py`.

## Deferred (C5)

Staged-copy garbage collection after pre-publication crashes is **not** part of
this slice. Orphaned `prepared_staged/<receipt>` directories may remain until a
separate reclamation path (keyed on receipt digests) is reviewed.
