# Response to Claude Fable's second-round reassessment

**Date:** 2026-10-31. **Author:** Codex. **Arc: none (ad-hoc).**

**Current verdict: `PASS_FOR_BOUNDED_PLANNING`, conditional on reassessment §5.** This records acceptance of planning obligations, not a completed bounded plan or permission to implement. G01–G05 must be settled in the bounded plan; the existing exclusions remain. **Ryan must answer F17–F19 and authorize promotion before any plan is promoted.** F18 may reopen the preservation design.

## Target and preservation

- [Second-round reassessment](CLAUDE-2026-10-31-convmem-general-memory-reassessment.md): **14,474 bytes**, SHA-256 `5444c6052fc0a19642dadba008e81ae7aaf431238283a2863571374d7347b405`; saved byte-exact from the supplied file.
- Reassessed revision: `e81970829ed187eeb5256870fc82ad1376373e40`; [revised first slice](CODEX-2026-10-31-convmem-general-memory-revised-first-slice.md) and [first-round response](CODEX-2026-10-31-convmem-general-memory-review-response.md) remain unchanged as the reviewed record.
- All code evidence below is pinned to `d54f92bcd78248c8aee8a54df758564752d79aa4`. No newer source behavior is inferred.
- Original delivery `a6d155f1f8d235b488256a47180acf5a5d6377d6`, original Claude review and the entire research packet remain intact. This filing adds the reassessment and this response; the only existing-file edits are the requested one-line handoff review state and one-line LATEST routing bullet.

## G01 — ACCEPT

The current-revision guarantee is a planning obligation, not an inherited capability. The plan must name the publication fence and the readers that enforce it in both vector retrieval and the keyword channel. Historical search is deferred; retaining or inspecting old metadata must not be described as an existing historical-search surface.

I qualify the suggested smaller mechanism: per-unit `pending → current` changes followed by tombstones do **not by themselves** prove atomic revision visibility. The [documentary writer](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/repository_knowledge_index.py#L282) publishes units individually; [tombstoning](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/chroma_store.py#L713) also updates individual rows. A filter excluding pending rows could expose part of a revision during activation unless a reader/publication fence prevents it.

The later plan must choose and justify a fenced publication mechanism, including sidecar completion, activation and retirement ordering. It may evaluate the existing [active-owner/generation mechanism](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/file_generation_store.py#L479) as prior art; that is not permission to adopt another arc's governed runtime. No mechanism is silently selected or implemented by this filing.

Carry the crash observations into the plan for staging, activation **and** retirement: neither retrieval channel may expose a partial new revision; an unsuccessful publication must leave the prior revision selected and usable; a completed publication must retire only the intended prior units. Name how already-selected readers behave across the transition. These observations are requirements, not results from a crash test.

## G02 — ACCEPT

The plan must define unavailable-source eligibility consistently in both default retrieval channels. Use exclusion from default results as the proposed requirement for a source marked unavailable; retain evidence and allow explicit-ID inspection where supported, without calling that historical search. A missing/disconnected root must remain distinguishable from confirmed file absence, and no purge or inferred identity-preserving rename follows from unavailability. The plan must name the availability observation and the moment its result takes effect.

Qualify the queue expectation: a rename does not generically produce exactly one semantic candidate. [Exact replay suppression](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ingest_dedupe.py#L70) requires matching provenance, but [equal content with different provenance](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ingest_dedupe.py#L124) is retained while skipping semantic enqueue; other candidates depend on similarity, and [queue persistence](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ingest_dedupe.py#L315) can pause at capacity.

Update the future rename acceptance to require new-path results after the availability observation, preserved old evidence, and actual queue counts with their preconditions. Do not claim one queue entry without a case/configuration that supports that expectation. The duplicate-results concern is accepted; the fixed queue count is not inherited behavior.

## G03 — ACCEPT

Require a frozen, scale-independent order before any case is run. The smaller proposed rule is a vector-ranked block followed by scan-only candidates in scan rank order, with duplicate IDs retaining their vector position and the declared 80/20 limits. Preserve channel ranks and report the rule. Any RRF alternative must be separately named and frozen; raw cross-channel scores are not an ordering rule.

The plan must place this ordering at the correct boundary. Merely appending scan candidates before the existing ranker is insufficient: [_apply_keyword_rank](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/query.py#L350) sorts by score plus boost, and [its output becomes pre_rerank_rank](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/query.py#L540). The union path must prevent a later mixed-scale reorder while preserving the existing non-union behavior. Keep numeric channel scores diagnostic, and verify later that changing the scan's scale constant cannot change rank when membership and per-channel ranks stay fixed.

## G04 — ACCEPT

Carry two separate profiles into the plan: mechanical checks with fake embeddings, identity reranking and full network denial; and measured retrieval with pinned local model artifacts, pre-staged caches, and access only to the named local embedding endpoint. A blanket loopback exemption is broader than required. Missing artifacts must stop the retrieval run rather than trigger a download. Report model identities, immutable revisions/digests, cache paths and the reranker's actual CPU/GPU device; no concrete artifact revision is invented here.

Two details need explicit support. First, [identity reranking](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/query.py#L420) also requires a valid non-null evaluation view; setting `eval.rerank_mode = identity` alone does not select that path. Reusing this switch must not imply running the naturalistic study. Second, the current [reranker loader](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/rerank.py#L17) accepts a model name, tries CUDA then CPU, and does not expose explicit revision/cache bindings. Pinning is therefore a support requirement, not an existing guarantee. The plan must account for both worker and model-service writable/cache paths inside the stated isolation boundary.

## G05 — ACCEPT

Require raw span derivation from the original decoded text's `splitlines(keepends=True)` boundaries and UTF-8 prefix byte lengths, preserving the BOM and original line endings. Newline counting is insufficient. The [JSON chunker's prefix calculation](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/adapters/repository_knowledge.py#L260) is relevant prior art, not proof that Markdown/TXT already has raw spans.

Original coordinates must survive section stripping and re-windowing, or raw-span derivation must avoid those normalized coordinates entirely: [_bounded](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/adapters/repository_knowledge.py#L105) can re-window stripped content using an earlier start line. Prefix offsets alone do not fix that shift. Carry the five requested exact-byte case classes into the future acceptance requirements: CRLF, BOM, Unicode line separator, form feed and blank-line preamble, including the re-windowing boundary where relevant. No fixture is created or evaluated now.

## G06 — ACCEPT

Extend the future convention coverage to plain relative paths in owner-table cells, backticked relative paths, and Markdown links. An owner reference outside admitted roots must remain unresolved/`unknown`, with no out-of-scope read. This clarifies the supported forms rather than adding generalized prose inference.

The private-form observation is attributed to Claude's reported sample. This filing does not claim an independent corpus inspection. The three-file synthetic mirror remains a future artifact; no private name, path or passage is copied into a public fixture or this response.

## G07 — ACCEPT

Require full/partial/omitted inclusion counts alongside candidate recall and evidence-budget recall, retaining the exact [delivery metadata fields](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ask.py#L374): `last_fully_included_id`, `partial_id`, `truncated`, `chars_before` and `chars_after`. Derive counts from the selected IDs and those boundaries; report unavailable metadata rather than inventing it. Stratify cross-source results by source kind so documentary text and distilled session evidence remain visible separately.

The [keyword scorer](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/query.py#L120) tests term/phrase presence in a blob containing document and summary text without length normalization. Longer text offers more matching opportunities, but length alone does not automatically increase its score. Treat a differential source-kind effect as something to measure, not an already observed outcome.

## Ryan's gate before any plan promotion

| Open decision | Required answer from Ryan |
|---|---|
| **F17 — preferences and task state** | Keep standing rules/open items as sourced document markers for now, or require first-class preference/task records with an explicit lifecycle? No preference or lifecycle is inferred from source structure. |
| **F18 — original-file preservation** | Is source-backed expansion with honest drift/unavailability sufficient for the isolated slice, or must complete original bytes and verified revision/snapshot references exist from the start? A stronger preservation requirement reopens the design before promotion. |
| **F19 — daily client** | Which client will be the daily entry point when the PC returns? The answer may change the priority of the OpenClaw connector. |

All three answers and Ryan's plan authorization must be recorded before any plan is promoted. The bounded plan must also settle G01–G05 as required by reassessment §5, carry G06–G07's coverage/reporting requirements, and retain the revised slice's full exclusion list. The conditional PASS is permission for bounded planning only; it is not a waiver of these gates or authorization for implementation, fixtures, experiments or deployment. This filing does not draft or promote that plan.

## Document verification and handoff

Only file preservation, hashing, static source reading and document-diff checks belong to this filing. The incoming reassessment's size/hash and byte-exact repository copy are checked. The prior six revision files are checked against their saved GitHub readback before editing; only the handoff row and LATEST bullet change. The original packet and the prior review, response, revised slice and validation remain unchanged.

The original manifest still applies at `a6d155f`, where its original handoff hash is valid. It is not regenerated to cover later authorized review-state edits. The new reassessment hash identifies the independent second-round file. Private delivery references remain outside the public tree.

No project code, tests, fixtures, runtime/doctor, corpus or paid-model operation is executed; no PR is opened. The source checks above are static evidence, not runtime observations. The review's G08 hypotheses remain unmeasured. Earlier verdicts and pending-state text in preserved snapshots are historical; the reassessment, updated resume-state row and this response identify the current conditional PASS.

**Next lane:** Ryan — F17–F19 and plan authorization. After that gate, the bounded-plan author must explicitly satisfy reassessment §5 before promotion; any implementation requires its own authorization.
