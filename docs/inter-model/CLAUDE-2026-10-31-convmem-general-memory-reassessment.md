# Reassessment: revised first slice after author response

**Date:** 2026-10-31. **Reviewer:** Claude Fable 5.1 (independent, read-only). **Arc:** none (ad-hoc).
**Supersedes nothing.** The original review (28,708 bytes, SHA-256 `be4fb1bf…a188e`) stays as delivered; this file records the second-round verdict on Codex's response and revised slice. Public-safe: no private URL, file name or personal detail beyond what the public tree already states.

## 1. Target and integrity

| Item | Value | Verified how |
|---|---|---|
| Review target | `e81970829ed187eeb5256870fc82ad1376373e40` (`docs/2026-10-31-general-memory-fable-verdict`) | fetched; one commit on top of `a6d155f`; `git diff --stat d54f92b e819708 -- . ':!docs/'` is empty, so all code citations still hold |
| Delta vs original delivery | six files: my review added byte-exact (digest matches), three new Codex documents, one table line in the handoff, one routing bullet in `LATEST.md`; `review-pack-2026-10-31-convmem/` byte-identical | `git diff --stat a6d155f e819708` |
| Original delivery / assessed source / `main` | `a6d155f` / `d54f92b` / `main` still at `d54f92b` | `ls-remote` |
| Package manifest (Drive) | 67 entries; the six revision files' digests equal the Git blobs at `e819708`; 11 sampled `source-evidence/` digests equal the blobs at `d54f92b` | decoded and compared |
| Compilation / ZIP (Drive) | 172,509 and 510,725 bytes as the guide states | **size only**; neither downloaded nor hashed — the Git commit is the primary source and the manifest cross-check covers the revision text |
| Private companion | re-read; unchanged from round one | — |

Documents read in full: `CODEX-…-review-response.md`, `CODEX-…-revised-first-slice.md`, `CODEX-…-revision-validation.md`, the start-here guide. Code re-inspected at `d54f92b`: `repository_knowledge_sync.py`, `repository_knowledge_index.py`, `adapters/repository_knowledge.py`, `ingest_dedupe.py`, `provenance_binding.py`, `chroma_store.py`, `file_generation_store.py`, `serving_index_repository.py`, `query.py`, `rerank.py`, `evidence.py`, `incremental_jsonl_isolation.py`, `eval_naturalistic/v2/{evidence,adapters/capability,adapters/reduction}.py`.

## 2. Verdict

**`PASS_FOR_BOUNDED_PLANNING`**, with the plan requirements in §5 carried into the bounded plan before any implementation authorization. This is not implementation, fixture, runtime or deployment approval; F17–F19 remain Ryan's decisions, and F18 can still reshape the slice.

Why PASS now: every F01–F09 disposition is an evidence-backed ACCEPT; the four amendments to my §5 (rename makes a new identity, changed-file embedding is measured not promised, raw-byte mapping is new work, no prompt change at all) are each correct against the source and make the slice smaller and more honest than mine. Codex's new code claims that I checked are all accurate: `_pending_relpaths` redispatches every entry when the manifest or Git HEAD changes; Markdown/text chunking normalizes and leaves `byte_start/byte_end` unset (only the JSON chunker fills them, `adapters/repository_knowledge.py:260`); the stored search text is prefixed and capped at 8,000 chars; the hermetic config uses fake models and an empty Ollama host; the capability values used exist in the enums; the availability mapping matches `evidence.py`.

Why not unconditional: four design gaps remain where the slice states a guarantee without naming the mechanism that provides it (G01–G04). None changes the slice's shape; all must be decided in the plan, because each would otherwise be discovered during implementation and silently resolved.

## 3. F01–F09 status

| Finding | Status | Residual |
|---|---|---|
| F01 sibling scope, not a parallel pipeline | **Partly resolved** | Reuse map is precise and the two qualifications are correct. Open: the current-revision/publication mechanism (G01) and the rename retrieval consequence (G02). |
| F02 E4 removed | **Resolved** | Mechanical comparison only; no fresh-agent contest, LLM judge or product-value claim; study material untouched. |
| F03 pool sweep before index | **Partly resolved** | Order and matched 100-candidate budget accepted. Open: the union arm's pre-rerank ordering rule (G03) and reranker pinning (G04). |
| F04 ask budget / expansion | **Partly resolved** | No auto-expansion; raw-byte mapping named as new work. Open: line-boundary semantics for the byte map (G05). |
| F05 relations carrier | **Resolved** (contingent on G01) | Sidecar JSONL, five-term vocabulary, extraction only. "Complete" reporting depends on the publication mechanism. |
| F06 no prompt change | **Resolved** | Stricter than my proposal; known framing limitation stated. |
| F07 isolation | **Resolved as design** | Fresh worker, `CONVMEM_CONFIG` before import, all-path check, overlap rejection. Open implementation detail: model caches and loopback (G04). |
| F08 capability vocabulary | **Resolved** | Declaration values valid; primary-scoring ineligibility correctly stated. |
| F09 convention extraction first | **Resolved as design** | Conservative freshness labels are an improvement on my wording. Fixture coverage note in G06. |

## 4. Remaining findings

Severity: **P** = must be settled in the plan; **m** = plan detail; **H** = hypothesis.

**G01 (P) — "Only units bound to the fully published revision are current" names no mechanism, and the one the words suggest does not exist.**
*Claim:* revised slice, reuse map paragraph: "Ordinary current-revision retrieval admits only units bound to that revision; prior units remain historical and require an explicit historical query… Publication failure leaves the old indexed revision selected and the new one pending."
*Evidence:* vector retrieval filters only `superseded` (`chroma_store.py:406-434`); the keyword scan filters only `is_superseded` (`metadata_keyword_fallback.py:35`); no read path consults sync state; no search surface exposes `include_superseded` (`convmem.py`, `mcp_server.py`, `query.py` have no such option), so no "explicit historical query" exists. Units are written one `add_unit` at a time (`repository_knowledge_index.py:282-287`), so an interrupted batch leaves a partial new revision visible to both channels. Two existing mechanisms could supply the guarantee: per-source tombstoning (`supersede_units_for_source`, `chroma_store.py:713`, keeps history as metadata), or the generation store's per-owner active pointer (`file_generation_store.py:483-531`), which is the incremental-JSONL publication fence.
*Consequence:* the acceptance rows "publication failure must not expose a partial revision" and "prior units historical" cannot be observed without a mechanism; an implementer would invent one.
*Smallest correction:* choose in the plan. The smaller choice for a sibling of `repository_knowledge_v1`: write new-revision units with a scalar `revision_state="pending"`, flip to `"current"` after the batch and sidecar publish succeed, then tombstone the prior revision with `supersede_units_for_source`; add `revision_state != "pending"` to the two read filters in the isolated scope. Declare historical retrieval **deferred** (tombstoned units remain inspectable through `units_metadata(include_superseded=True)`, nothing more). The generation store is the more complete alternative but imports the JSONL arc's gates.
*Verification:* crash-injection acceptance — abort after k of n unit writes: zero new-revision units in either channel, prior revision intact, sync state still naming the prior revision; tombstone count equals prior-revision unit count after a successful publish.

**G02 (P) — Rename leaves two current sets in retrieval.**
*Claim:* "Rename creates a new source key… Missing sources retain their last indexed revision with unavailable/unknown source status, rather than silently deleting history."
*Evidence:* with no retirement, the old path's units stay current-eligible; the new path's units are not exact-suppressed because exact suppression requires identical provenance identities (`ingest_dedupe.py:70-79`, `provenance_binding.py:210`), so they are accepted and the pair is queued as a review-only semantic candidate. Default retrieval then returns both.
*Consequence:* the rename acceptance row passes while search shows duplicates whose older copy expands to `unavailable`.
*Smallest correction:* add to the plan: after an availability sweep marks a source `unavailable`, its units are excluded from default results (a scalar `source_status` on the unit, updated by the sweep inside the isolated scope) or ranked below available ones; the semantic-candidate queue entry is an expected, counted outcome.
*Verification:* rename fixture — default results contain only new-path units; old-path units reachable only by explicit id; queue shows one semantic candidate.

**G03 (P) — The union arm's candidates enter ranking on incompatible score scales.**
*Claim:* "up to 80 vector plus 20 scan candidates, deduplicated without opportunistic refill… same reranker."
*Evidence:* scan rows carry `score = min(keyword/6, 0.99)` (`metadata_keyword_fallback.py:49-52`); vector rows carry `score = 1 - distance` (`query.py:521-524`). `_apply_keyword_rank` orders by that `score` plus a 0.02 keyword boost (`query.py:350-375`), that order becomes `pre_rerank_rank`, and fusion weights it 2:1 over the cross-encoder rank (`query.py:379-402`). A scan-only candidate's pre-rerank rank is therefore an artifact of which scale it came from, which the research itself warns about (Bruch et al.).
*Smallest correction:* freeze the rule in the evaluation procedure: scan-only candidates take pre-rerank positions after all vector candidates (81–100), or fuse by RRF over per-channel ranks; report both and never the raw mixed-scale order.
*Verification:* a fixture where a scan-only candidate is the target — its final rank must not depend on the keyword scale constant.

**G04 (m) — Model dependencies under isolation are half-specified.**
*Evidence:* the comparison needs the cross-encoder `BAAI/bge-reranker-v2-m3` (`query.py:39`, `rerank.py:17-26`), fetched from Hugging Face into the cache on first use; the isolation env relocates `XDG_CACHE_HOME` (`incremental_jsonl_isolation.py:194`) and `install_network_denial` (`:339`) blocks every socket including loopback, which would also stop local Ollama embeddings. The slice pins the embedding model but does not mention the reranker, its revision, or the cache.
*Smallest correction:* pin reranker model + revision, pre-stage both model caches under the isolation root, and define two isolation profiles: mechanical CI (fake embeddings, `eval.rerank_mode = identity`, full network denial) and retrieval run (loopback to the pinned Ollama host only, pre-cached reranker, non-loopback egress denied). Report the reranker's CPU/GPU device, since it dominates p95 at 100 candidates.
*Verification:* retrieval run starts with the network denied except loopback and completes without a download.

**G05 (m) — "Line-to-byte mapping" must use the chunker's own line boundaries.**
*Evidence:* the chunkers split with `str.splitlines()` (`adapters/repository_knowledge.py:72,126`), which also breaks on `\v`, `\f`, `\x1c-\x1e`, `\x85`, ` `, ` `; a byte map built by counting `\n` disagrees on such files (checked: `"a b\x0cc\r\nd\n"` is 4 lines by `splitlines`, 2 by newline count). The pre-heading section is `strip()`ped before re-windowing (`:147`, `:105-116`), so leading blank lines shift re-windowed line numbers; `_utf8` keeps a BOM as a character.
*Smallest correction:* specify that the sibling scope derives raw spans from `splitlines(keepends=True)` on the decoded text with prefix-encoded byte offsets (the JSON chunker's technique, `:260-261`), never from newline counting; include CRLF, BOM, a Unicode line separator, a form feed and a blank-line preamble in the exact/drift fixture.
*Verification:* exact-byte round trip on those five cases.

**G06 (m) — Fixture coverage for conventions.**
Owner references in the sampled private file appear as plain relative paths inside table cells and backticks, not only as Markdown links; the slice's "table rows and relative links" should say so, and the three-file public mirror should include that form plus an owner reference that resolves outside admitted roots (expected `unknown`).

**G07 (m) — Evidence-budget recall should report inclusion counts.** Documentary chunks are up to 6,000 chars, so two hits can fill the 12,000-char budget; report `last_fully_included`/`partial` from the delivery metadata alongside recall, and report cross-source results by source kind, since `_keyword_score` rewards long verbatim `document` text over short distilled summaries.

**G08 (H) — Unchanged.** My three hypotheses stand as hypotheses: exact text matters on this corpus; convention extraction covers most of Packets 2 and 4; a grep baseline ties on self-describing documents. The slice's stop threshold tests the third correctly.

## 5. Requirements for the bounded plan

1. G01 decided: pending→current flip + tombstone (or the generation store), read filters named, historical retrieval declared deferred, crash-injection acceptance added.
2. G02: unavailable-source handling in default results, rename acceptance updated.
3. G03: union ordering rule frozen before any case is run.
4. G04: two isolation profiles; reranker and embedder pinned and pre-cached.
5. G05: raw-span derivation rule and the five byte-level fixture cases.
6. Everything in the revised slice's exclusion list stays excluded; F17–F19 answered by Ryan before implementation, with F18 able to reopen the preservation design.

## 6. Access limits

- The full ZIP and the compilation were not downloaded; their sizes match the guide, and the package manifest's digests for the six revision files and 11 sampled source files match Git. The `source-evidence/` copies were therefore verified by digest, not by reading the ZIP.
- Second-account private files remain unreachable; nothing new was read from the private corpus this round.
- No runtime, no tests, no fixtures, no writes to repository, corpus or Drive except this file, which is saved separately as the guide asks.
- Every finding above is a code and document reading at `d54f92b` / `e819708`; none is an observed runtime behaviour.

**Review state:** second-round verdict delivered; next lane is Ryan (F17–F19 and plan authorization), then the bounded plan carrying §5.
