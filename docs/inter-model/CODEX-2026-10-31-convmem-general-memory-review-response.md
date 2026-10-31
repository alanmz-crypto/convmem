# Response to Claude Fable's general-memory review

**Date:** 2026-10-31. **Author:** Codex. **Arc: none (ad-hoc).**

The direction remains proposed; the original Packet 1 is withdrawn as the next-work recommendation. The [revised first slice](CODEX-2026-10-31-convmem-general-memory-revised-first-slice.md) replaces it prospectively. The original assessment and research remain unchanged as reasoning history. Claude's verdict remains **`REVISE_BEFORE_PLANNING`**; adopting these corrections is not a new reviewer PASS or implementation authorization.

## Review identity and reading route

- [Original review](CLAUDE-2026-10-31-convmem-general-memory-adversarial-review.md): 28,708 bytes; SHA-256 `be4fb1bf980107b96a8e78fdbf0f8c92a0ed7666dc6fda9ec4dce7b1218a188e`. Saved from the supplied file without transformation.
- Reviewed delivery: `a6d155f1f8d235b488256a47180acf5a5d6377d6`; original manifest SHA-256 `5f446de7077e165a38e3273afe5e97d5fc654d87f4605063840034ad966715ea`.
- Every code reference below is pinned to assessed source `d54f92bcd78248c8aee8a54df758564752d79aa4`.
- Read this response, then the revised slice. The [original field guide](review-pack-2026-10-31-convmem/FIELD-GUIDE.md) maps the preserved historical packet.

## F01 — ACCEPT

Use `ordinary_document_v1` as a sibling scope sharing documentary parsing, packaging, provenance and sync machinery. Keep `repository_knowledge_v1` admission and its Git/manifest guarantees intact. The revised slice maps the existing fields/functions to the required deltas instead of proposing a second documentary pipeline.

Two qualifications matter to effort and acceptance. Admission is not the only delta: the [indexer](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/repository_knowledge_index.py#L99) rechecks repository eligibility, hardcodes its source/recipe/domain, and enters a production write session. Also, [_pending_relpaths](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/repository_knowledge_sync.py#L145) can redispatch all entries when the manifest or Git HEAD changes. Existing sync is not an unconditional unchanged-file embedding cache. The scope extension must explicitly separate these repository bindings from reusable mechanics.

## F02 — ACCEPT

Remove E4, the six continuation tasks, and the recommended-first-outcome claim derived from them. This slice records mechanical retrieval, evidence availability and processing counts only. It does not access sealed episodes, run a fresh-agent continuation contest, use an LLM judge, or issue a product-value disposition. The [naturalistic study's authorization limits](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/plans/STATUS-naturalistic-product-value.md#L20) remain in force. Only its evidence vocabulary is reused; its study protocol is not executed.

## F03 — ACCEPT

Order the work as pool sizes 20/50/100, then an opt-in candidate union using the existing keyword scan, then a separate decision about a lexical index only if measured residual misses justify it. [Configured candidate sizing](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/query.py#L476) already exists; the [scan](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/metadata_keyword_fallback.py#L17) is currently reached through transient-backend fallback, not as a normal independent channel. The proposal states the added wiring explicitly.

Lock the eligible corpus, candidate and output budgets, scan cap, and timing procedure. Report effective pool sizes when the corpus is small; a three-file mechanical fixture cannot establish retrieval quality. Preserve Q02 as a regression case without claiming a live-corpus result in this documentation task.

## F04 — ACCEPT

Leave `ask` context construction and its [12,000-character/eight-hit limits](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ask.py#L74) unchanged. Add explicit document expansion only in a later authorized implementation of this slice; no automatic expansion into synthesis.

The exact-byte claim needs a bounded additional mechanism. [Markdown and text chunking](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/adapters/repository_knowledge.py#L71) normalizes line endings and Markdown whitespace, and does not populate byte offsets. The [stored search document](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/repository_knowledge_index.py#L138) is prefixed and may be truncated. The revised slice adds raw-file line-to-byte mapping and digest checks for expansion while labelling the indexed text as a search projection. It does not claim that the existing projection preserves original bytes.

## F05 — ACCEPT

Freeze `relates_to` and existing decision suppression behavior. Use a versioned JSONL sidecar inside the isolated ordinary-document state directory for evidence-linked relations; scalar metadata contains only record references and simple selectors. The proposed vocabulary is `supersedes`, `corrects`, `owns`, `depends-on`, `unknown`. Only literal conventions produce relations; ambiguous targets remain unresolved.

This slice extracts relations; it never suppresses a decision or applies a correction in synthesis. That boundary follows the existing [decision filtering](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/evidence.py#L258), which is not a generic typed-edge store. Correction application belongs to a separately reviewed Packet 2.

## F06 — ACCEPT

Remove **all prompt changes**, including the review's optional tagged framing sentence. This follows Ryan's narrower instruction. Documentary ingestion already [bypasses LLM distillation](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/repository_knowledge_index.py#L1), so the first slice has no reason to change the [locked distill recipe](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ingest.py#L1004). Existing coding-oriented ask behavior remains a known limitation; the pilot measures evidence retrieval rather than claiming general-purpose answer quality. Prompt characterization and golden fixtures remain unchanged.

## F07 — ACCEPT

Require a fresh worker with `CONVMEM_CONFIG` set before any ConvMem import, plus explicit isolation of every writable path. A config variable alone is not containment. The current [documentary indexer](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/repository_knowledge_index.py#L275) must accept supported isolated writer bindings; passing its currently unused `chroma_dir` argument is insufficient.

The underlying [write session](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/chroma_write_store.py#L1096) already accepts config, lock, attestation and census paths. Reuse that boundary instead of a test monkeypatch. The [hermetic config helper](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/incremental_jsonl_isolation.py#L132) is prior art with fake model settings, not a ready local-Ollama pilot configuration. Production roots and watchers remain outside this proposal.

## F08 — ACCEPT

Declare the sibling scope using the exact [nine-axis capability vocabulary](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/eval_naturalistic/v2/adapters/capability.py#L22) and the orthogonal [evidence availability axes](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/eval_naturalistic/v2/evidence.py#L19). The revised slice contains one proposed declaration, its omissions and per-state availability mapping. These are design targets, not attained capabilities or permission to run the study. Unsealed, unverified evidence does not gain the study's primary-scoring eligibility by sharing its vocabulary.

## F09 — ACCEPT

Make deterministic convention extraction the first mechanism for owner declarations, correction text, lessons, open items and unknowns. Keep source revision and location with every extracted record. General extraction and truth resolution remain deferred. Applicability is supported by Claude's reported two-file sample; this response does not claim an independent private-corpus inspection or coverage of the other account.

Refine the freshness label: changed owner hash means **heuristic stale**; unchanged means **no observed owner change since capture**; a missing baseline or unreadable/ambiguous owner means **unknown**. An unchanged hash does not prove a view was current at its `Prepared:` date. Preserve `Prepared:` as a literal date claim rather than inventing a historical owner snapshot.

## Explicit amendments to review §5

The revised slice adopts §5 with these smaller, source-backed acceptance changes:

1. **Rename produces a new path identity.** Canonical path plus content SHA cannot preserve identity after a rename. Existing [unit IDs](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/repository_knowledge_index.py#L40) also include path and locator. Stable logical-document IDs and move inference are deferred.
2. **Changed-file embedding counts are measured, not promised section-only.** [Embedding precedes replay/dedupe](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/repository_knowledge_index.py#L143). Whole-file unchanged skip is required for the new scope; a pre-embedding chunk cache is deferred. This also qualifies F11's description of inherited idempotency.
3. **Exact expansion requires raw byte mapping.** Normalized/truncated search text is not an original; no full-file archival or revision-level Restic guarantee is claimed.
4. **No prompt rewrite at all.** No framing-sentence exception survives Ryan's instruction. No product-value experiment or LLM judging is included.

F10's existing brief tools remain the later extension point. F12's conservative missing-source behavior is retained; F13's Thai substring baseline belongs to the later format slice. F14's synthetic public mirror is required. F15's deferrals remain conditional on evidence and the F19 client answer. F16's missing search transcripts cannot be reconstructed; the original source register retains that limitation. These notes add no active implementation work.

## F17–F19: what is known and what remains for Ryan

| Question | Evidence-backed answer | Decision left for Ryan |
|---|---|---|
| F17: preferences and tasks | The [ledger](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ledger.py#L18) has observation/decision/verification types, not dedicated preference/task kinds. Literal standing rules and open items can be preserved as sourced markers without applying them as instructions. | Should these remain document markers, or later become records with lifecycle, owners, dates and explicit user authority? Marker-only capture is the proposed interim scope, not an inferred preference. |
| F18: preservation | The [authority audit](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/audit-ledger-first/CURRENT-OBSERVATION-AUTHORITY.md#L9) describes Chroma authority and incomplete JSONL coverage. It does not establish a Restic snapshot reference for every source revision. Present Markdown/TXT search projections are not byte-exact originals, even at chunk granularity. | Is source-backed expansion with honest drift/unavailability sufficient for this isolated experiment, or must complete original bytes and a verified snapshot reference exist for every revision from the start? The latter changes the slice and needs a preservation design before implementation. |
| F19: daily client | The [Switchboard brief](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/plans/STATUS-openclaw-convmem-integration.md#L6) establishes the intended OpenClaw connector role, not which client Ryan will resume using. | Which client is the daily entry point when the PC returns? OpenClaw could change connector priority; no answer is inferred from earlier tool use. |

These are recorded decisions for Ryan, not a request to run work now. No new architecture/execution arc or production permission is created.

## Preservation and validation boundary

The verdict branch starts at `d54f92b` with the original `a6d155f` commit fast-forward merged unchanged. The entire `review-pack-2026-10-31-convmem/` subtree remains identical. Only the requested review-state table line changes in the original Codex handoff, and only its existing routing bullet changes in `LATEST.md`. Other handoff status sentences remain historical by the explicit one-line edit limit; the resume-state row and this response carry the delivered state.

The original manifest includes the original handoff. Therefore it is validated **at `a6d155f`**, not represented as matching the handoff after its authorized status edit. The manifest itself is unchanged. A separate private delivery-receipt addition records the incoming Drive file; no private identifier or URL belongs in this public response.

Validation for this delivery is document-only: original-file digest, original manifest at its commit, unchanged packet subtree, permitted one-line diffs, link targets and public/private separation. No implementation, fixture, runtime, corpus write, paid call, study run or PR was performed. Detailed results are in [revision validation](CODEX-2026-10-31-convmem-general-memory-revision-validation.md).

**Next lane:** Ryan for the recorded decisions and revised-slice review. Any reviewer reassessment or implementation requires a separate step; the existing verdict is not self-upgraded.
