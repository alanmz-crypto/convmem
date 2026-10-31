# Claims to challenge in the ConvMem assessment

**Arc:** none (ad-hoc strategic assessment). **Prepared for:** Claude Fable adversarial review, 2026-10-31.

This is a claim register, not a certification or execution plan. Code observations are pinned to `d54f92bcd78248c8aee8a54df758564752d79aa4`. The proposed changes have **not** been implemented. General-life examples below are **synthetic examples**, not private records or established facts about a person. Private evidence, if supplied separately, must be reviewed separately.

The review should distinguish a false factual premise from a reasonable but unproved product hypothesis. A research paper's result does not establish ConvMem's performance.

## C01 — Source state and deployed state differ

- **Class:** code-observed / historical runtime.
- **Claim:** the assessed source is `d54f92b`; the October 22 workstation snapshot records runtime `1a68675`. Git main includes the doctor acknowledgment merge `4b4796b` although some routing documents still describe its PR as open. A merge does not establish deployment.
- **Evidence:** [assessed commit](https://github.com/alanmz-crypto/convmem/commit/d54f92bcd78248c8aee8a54df758564752d79aa4), [runtime snapshot](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/plans/STATUS-codex-jsonl-production-integration.md), [acknowledgment merge](https://github.com/alanmz-crypto/convmem/commit/4b4796b).
- **Confidence / limit:** high for Git/source facts; historical documentation only for the PC. No present PC observation.
- **Challenge:** locate contradictory newer deployment evidence. Identify any recommendation that incorrectly treats main, the migrated runtime, and the PC as identical.

## C02 — General document ingestion is missing from the inspected routing

- **Class:** code-observed.
- **Claim:** arbitrary Markdown is rejected after special inter-model, steering and repository-knowledge checks. The inspected routing has no general PDF/DOCX/XLSX/CSV/OCR adapter. This is narrower than saying the entire project cannot read documents.
- **Evidence:** [`detect_format` and `_PARSERS`](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/adapters/detect.py), [repository scope](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/repository_knowledge_scope.py).
- **Confidence / limit:** high for these entry paths; an alternate supported path could invalidate the broader recommendation.
- **Challenge:** search for such an alternate path and determine whether a thin adapter is sufficient. Avoid weakening existing repository-manifest admission rules merely to admit ordinary documents.

## C03 — Ordinary retrieval is vector-first, with important exceptions

- **Class:** code-observed.
- **Claim:** unscoped `query_units` starts with `max(top_k, top_k_candidates)` capped by `MAX_QUERY_RESULTS`, with `top_k_candidates` defaulting to 20. Keyword ranking mostly operates on that pool. There are explicit ledger-ID extras and a backend-transient keyword fallback; scoped retrieval over-fetches. It is inaccurate to say every query always considers exactly 20 records.
- **Evidence:** [`query_units`](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/query.py#L448), [historical recall issue #320](https://github.com/alanmz-crypto/convmem/issues/320).
- **Confidence / limit:** high for code; this review did not measure current corpus recall.
- **Challenge:** determine whether a larger pool alone fixes material misses before adding a second index. Test independent lexical candidates against equal-budget alternatives rather than presuming improvement.

## C04 — Original transcript expansion already exists

- **Class:** code-observed.
- **Claim:** `expand_record`, CLI full expansion and MCP expansion provide bounded original transcript access with availability/drift states. Normal `ask` formats the retrieved `document` text and does not automatically use that expansion path. Non-session records are explicitly returned as `not_session` with direction to open their source.
- **Evidence:** [`expand_record`](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/chunk_expand.py#L443), [`_format_context`](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ask.py#L475), [MCP surface](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/mcp_server.py), [issue #263](https://github.com/alanmz-crypto/convmem/issues/263).
- **Confidence / limit:** high for separation of the inspected paths. Expansion alone cannot discover a phrase absent from indexed summaries.
- **Challenge:** identify the smallest integration that improves grounded answers; check whether automatic expansion increases latency, leaks irrelevant context or creates source-drift ambiguity.

## C05 — Current prompts retain coding-specific assumptions

- **Class:** code-observed / inference.
- **Claim:** `ASK_PROMPT` and follow-up prompt describe evidence as past AI coding sessions. Distillation requests short technical solution/decision/explanation/pattern units and ignores dead ends. These choices plausibly impair general-purpose memory, but that effect has not been measured here.
- **Evidence:** [answer prompts](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ask.py#L25), [distillation prompt](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/distill.py#L19), [extensible domain taxonomy](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/domains.py).
- **Confidence / limit:** high for wording; moderate for predicted effect. Domain labels themselves are not a hard coding-only enum.
- **Challenge:** compare neutral prompts against the existing prompts on identical evidence, including rejected options whose rejection remains useful. Check for regression on the existing coding corpus.

## C06 — Relationship handling needs scrutiny before generalization

- **Class:** code-observed / inference.
- **Claim:** `filter_superseded_decisions` suppresses an in-result parent decision when another qualifying decision relates to it, subject to provenance identity checks. The synthesis prompt likewise treats child `relates_to` as replacement. This is not general typed temporal reasoning.
- **Evidence:** [decision suppression](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/evidence.py#L258), [answer contract](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/ask.py#L25).
- **Confidence / limit:** high for inspected semantics; whether existing producers guarantee replacement is a separate contract question.
- **Challenge:** establish whether `relates_to` has a stronger documented invariant than the assessment assumes. Test support, correction, dependency and supersession separately before declaring a bug or changing semantics.

## C07 — Thai lexical handling is limited, but a model migration is unproved

- **Class:** code-observed / proposal.
- **Claim:** `_search_tokens` uses an ASCII token pattern. This does not establish useful Thai word segmentation; pure Thai and mixed-language queries can follow different fallback behavior. It does not prove that current semantic embeddings fail Thai retrieval.
- **Evidence:** [tokenization](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/query.py#L115), [SEA-BED](https://aclanthology.org/2026.acl-long.397/), [PyThaiNLP tokenizer documentation](https://pythainlp.org/docs/5.1/api/tokenize.html).
- **Confidence / limit:** high for lexical code; unknown current cross-language quality.
- **Challenge:** test exact names, amounts, transliterations and cross-language questions before choosing tokenization or changing embeddings. Require local resource measurements.

## C08 — Some incremental ingestion is historically live; coverage remains uneven

- **Class:** historical runtime / code context.
- **Claim:** the October 22 snapshot records Codex admission and same-source publication fencing as live. It distinguishes that operation from Stage 1/2 owner acceptance, leaves Cursor/Crush on legacy routes, and does not select live Kiro sources. The open Crush cost issue documents repeated paid work after database changes.
- **Evidence:** [specific arc snapshot](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/plans/STATUS-codex-jsonl-production-integration.md), [issue #393](https://github.com/alanmz-crypto/convmem/issues/393).
- **Confidence / limit:** dated, source-backed operational record; no fresh replay or measurement in this assessment.
- **Challenge:** find later closure or runtime evidence, and determine which existing reuse/generation components new adapters can inherit. Do not recommend rebuilding already-shipped JSONL work.

## C09 — A JSONL-only recovery assumption is unsafe

- **Class:** code/documentation-observed.
- **Claim:** authority remains record- and path-specific: existing Chroma observation/search paths, approved decision intent and exports are not one interchangeable canonical log. The proposed source-first pipeline is a future direction for new evidence, not a claim that current indexes are fully disposable.
- **Evidence:** [authority map](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/audit-ledger-first/CURRENT-OBSERVATION-AUTHORITY.md), [recovery guidance](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/RECOVER.md).
- **Confidence / limit:** high for documented boundaries; exact current backup usability was not qualified here.
- **Challenge:** identify any new source/extraction store that creates a second authority or weakens existing recovery. Specify coexistence and rebuild boundaries before implementation.

## C10 — This assessment did not produce a fresh live quality score

- **Class:** observed review limit / historical evidence.
- **Claim:** no new end-to-end retrieval benchmark or provider-backed quality run was completed. The migrated runtime doctor exited nonzero because model-service access and workstation configuration were unavailable. That is not evidence that the PC itself is unhealthy. The old #320 score is historical, and Q08/Q10 fixture wording has since changed.
- **Evidence:** [current golden fixture](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/tests/fixtures/golden_questions.jsonl), [historical issue](https://github.com/alanmz-crypto/convmem/issues/320), [research interpretation boundary](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/RESEARCH.md). The doctor observation is an author-reported session result, not a public reproducible test artifact.
- **Confidence / limit:** high about what this assessment did not execute; no present performance conclusion.
- **Challenge:** flag any report wording that converts code inspection, old results or missing cloud configuration into a fresh performance claim.

## C11 — Preserved-source retrieval is a strong baseline, not a universal winner

- **Class:** literature / inference.
- **Claim:** LongMemEval reports losses from some compressed representations; MemoryBench and filesystem-memory studies show that elaborate memory does not consistently outperform simpler approaches in their settings. These findings justify a strong raw-evidence control, not rejection of all extraction or graphs.
- **Evidence:** [LongMemEval](https://arxiv.org/html/2410.10813v2), [MemoryBench v4](https://arxiv.org/html/2510.17281v4), [filesystem study](https://arxiv.org/html/2607.26637).
- **Confidence / limit:** moderate cross-study convergence, with synthetic data, model/harness variation and preprint limitations.
- **Challenge:** inspect the actual ablations and task mix. Identify cases where structured extraction wins enough to justify its cost. Do not compare scores across incompatible papers as a shared leaderboard.

## C12 — Two timelines help, but cannot adjudicate truth by themselves

- **Class:** literature / proposal.
- **Claim:** learned/recorded time and effective time should remain distinct when known. A newly ingested old record must not automatically win. Source ownership, explicit corrections and unresolved disagreement still matter.
- **Evidence:** [Zep bitemporal design](https://arxiv.org/html/2501.13956); the suggested ingest-order reversal test is our proposal.
- **Confidence / limit:** high that the distinction is relevant; unknown extraction reliability on this corpus. Dates can remain unknown or approximate.
- **Challenge:** replay a synthetic original agreement, a correction, a late archive and a hypothetical scenario. Check current, effective-date and knowledge-at-the-time questions without manufacturing precision.

## C13 — Structured extraction and calculations deserve separate contracts

- **Class:** literature/documentation / proposal.
- **Claim:** retaining document hierarchy, native locators and tables can preserve distinctions lost in plain Markdown. Numerical answers need deterministic calculations or a qualified spreadsheet engine; parsing formulas is not evaluating them.
- **Evidence:** [Docling model](https://docling-project.github.io/docling/concepts/docling_document/), [OmniDocBench](https://arxiv.org/html/2412.07626), [openpyxl formulas](https://openpyxl.readthedocs.io/en/stable/simple_formulae.html).
- **Confidence / limit:** high for documented mechanisms; unmeasured parser/OCR accuracy on the intended files. Structured extraction is not lossless truth.
- **Challenge:** compare native extraction and a richer parser on 20 pages. Check exact values and table relationships, not only text similarity. Test stale or absent formula caches.

## C14 — Scoped lessons may improve future work, but promotion needs evidence

- **Class:** literature / proposal.
- **Claim:** small lesson records linked to observed outcomes, applicability and exceptions are a plausible extension. Stable item-level updates are preferable to untested wholesale rewriting. Generated reflection is not independent confirmation or user authority.
- **Evidence:** [Reflexion](https://arxiv.org/html/2303.11366), [ACE](https://arxiv.org/html/2510.04618), [MemoryGraft](https://arxiv.org/abs/2512.16962).
- **Confidence / limit:** promising mechanism, bounded studies; no demonstrated ConvMem benefit or asserted vulnerability.
- **Challenge:** compare equal-budget evidence-only, summaries and lesson-assisted continuation. Include a task where the lesson should not apply, and repeated summaries of one episode that must not count as independent support.

## C15 — The first pilot is a proposal with observable stop conditions

- **Class:** proposal.
- **Claim:** a bounded text-source pilot, followed by temporal maintenance and contrasting document/table tasks, can expose the largest product failures cheaply. Proposed 48 cases and six continuation tasks are engineering instruments, not evidence of universal reliability or authorization for the formal naturalistic study.
- **Evidence:** research report experiments E1–E6 and Packet 0–4; [current naturalistic boundary](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/plans/STATUS-naturalistic-product-value.md).
- **Confidence / limit:** unexecuted planning judgment. Pending formats must be reported separately from passes and failures.
- **Challenge:** propose a smaller first slice if this plan bundles too much. Require current ConvMem, ordinary source search, matched-budget candidate and oracle-evidence diagnostic comparisons. State what result would stop expansion.

## C16 — Deferring optional integration is a prioritization judgment

- **Class:** inference / proposal.
- **Claim:** existing CLI/MCP access appears sufficient to prove cross-domain value before further optional Switchboard integration/publication work. This is not a cancellation of that work, a change to its authorization, or a claim that its safeguards are needless.
- **Evidence:** [MCP implementation](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/mcp_server.py), [Switchboard status](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/plans/STATUS-openclaw-convmem-integration.md).
- **Confidence / limit:** moderate strategic judgment; effort and business value have not been measured comprehensively.
- **Challenge:** identify a concrete user workflow that cannot succeed without this connector, or a near-complete delivery whose benefit exceeds the pilot. Document length alone is not proof of overengineering.

## Jargon TL;DR

| Term | Meaning here |
|---|---|
| Code-observed | A property found in the pinned source, not proof of deployed behavior. |
| Historical runtime | A dated record of operation, not a current host measurement. |
| Candidate pool | Records considered before final ranking and answer-context selection. |
| Derived view | A brief, claim or lesson computed from identified source evidence. |
| Effective time | When a claim applies in the world, if the evidence establishes that time. |
| Learned time | When the system recorded the evidence or assertion. |
| Oracle evidence | Preselected correct supporting passages used to diagnose reasoning separately from retrieval. |
| Idempotency | Repeating the same input/configuration does not duplicate results or repeat expensive work unnecessarily. |
| Source ownership | An explicit convention about which record maintains a particular fact, not a universal guarantee that its claim is true. |
