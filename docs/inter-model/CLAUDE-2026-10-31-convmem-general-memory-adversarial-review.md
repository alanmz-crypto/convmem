# Adversarial review: ConvMem general-purpose memory direction

**Date:** 2026-10-31. **Reviewer:** Claude Fable 5.1 (independent, read-only). **Arc:** none (ad-hoc strategic review).
**Reviewed packet:** `CODEX-2026-10-31-convmem-general-memory-fable-review-handoff.md` and `review-pack-2026-10-31-convmem/`.
**Review mode:** document and code-evidence review in a detached worktree. No implementation, no live runtime, no test-suite run, no corpus or service writes, no paid model calls. Private details stay in the private companion; this file names no private URL, file name or person beyond what the public packet already names.

## 1. Target

| Item | Value | How verified |
|---|---|---|
| Delivery commit | `a6d155f1f8d235b488256a47180acf5a5d6377d6` (`docs/2026-10-31-general-memory-fable-review`) | fetched and checked out detached; `git log` shows it is one docs-only commit on top of the assessed source |
| Packet manifest SHA-256 | `5f446de7077e165a38e3273afe5e97d5fc654d87f4605063840034ad966715ea` | `sha256sum` of `PACKET-MANIFEST.json` matches; all 10 listed files match byte count and digest |
| Assessed source commit | `d54f92bcd78248c8aee8a54df758564752d79aa4` | `git diff --stat d54f92b a6d155f -- . ':!docs/'` is empty, so every code citation below holds for both commits; `origin/main` was still `d54f92b` at review time (no drift to report) |
| Private companion | `PRIVATE-EVIDENCE.md`, `BACKUP-RECEIPT.json` in the private Drive folder | read through the Drive connector; the receipt's delivery commit and manifest digest match the two values above |
| Private source files | 2 of 9 Ryan-account files read (the room-search lessons guide; the relocation "pack-last" derived list), metadata of a third; the second account was **not** reachable from this session | see §6 |
| Public issues | #263, #320 read via web fetch (GitHub API was unavailable here) | content matches the packet's description |
| Literature spot-checks | Zep/Graphiti (2501.13956), LongMemEval (2410.10813v2), Filesystem-Based Memory (2607.26637, via a mirror because arXiv rate-limited), plus my own knowledge of Mem0, DOS RAG and Contextual Retrieval | 4 of 28 register entries checked against the source; none misrepresented |

Code inspected at `d54f92b`: `adapters/detect.py`, `adapters/repository_knowledge.py`, `repository_knowledge_scope.py`, `repository_knowledge_index.py`, `repository_knowledge_sync.py`, `query.py`, `metadata_keyword_fallback.py`, `ask.py`, `distill.py`, `domains.py`, `evidence.py`, `ledger.py`, `chunk_expand.py`, `open_source.py`, `mcp_server.py`, `brief.py`, `meta_format.py`, `ingest.py` (selected), `chroma_write_store.py` (write session), `config.py`, `incremental_jsonl_isolation.py`, `watch.py` (event intake), `source_reconciler.py` (header), `eval_naturalistic/v2/{evidence,adapters/capability}.py`, `tests/fixtures/golden_questions.jsonl`, `docs/RECOVER.md`, `docs/audit-ledger-first/CURRENT-OBSERVATION-AUTHORITY.md`, `docs/plans/STATUS-{codex-jsonl-production-integration,naturalistic-product-value,openclaw-convmem-integration}.md`.

## 2. Verdict

**`REVISE_BEFORE_PLANNING`.**

The *direction* survives the challenge: preserve original evidence first, make current state a source-backed view, test explicit lessons before autonomous extraction, defer graphs and connector work until a measured failure demands them. Every code claim in `CLAIMS.md` (C01–C10) is accurate at `d54f92b`; the literature I sampled is represented faithfully; and the two private files I read match the companion's description closely enough that the corpus-fit premise is credible (not proven) for Ryan's account.

What does not survive is the packet's **active first slice (Packet 1)** as written. It would build, as new work, four things the repository already has in a narrower form, sequence a new lexical index ahead of a nearly free experiment that could make it unnecessary, change a locked prompt recipe, and run an informal continuation experiment that collides with a separately governed arc. None of this is a false premise; it is a wrong-shaped first move. The revised first slice in §5 replaces Packet 1; once the author adopts it (or rebuts it with evidence), I would expect `PASS_FOR_BOUNDED_PLANNING`. No implementation or deployment is approved by this review.

## 3. Findings

Severity: **B** = blocks planning as written; **M** = must be fixed in the plan; **m** = improvement; **Q** = open question; **H** = hypothesis (labelled, not established).

### Blockers

**F01 (B) — Packet 1 re-specifies machinery that already exists; the plan must start from `repository_knowledge_v1`, not beside it.**
*Claim/path:* RESEARCH.md §4 Packet 1 ("Add ordinary Markdown/TXT ingestion behind a separate source contract, stable revision/span references, stage caching, independent lexical candidates"); ASSESSMENT.md row 1 ("Ordinary local documents need a first-class ingestion route").
*Evidence:* `repository_knowledge_index.py:1` is a documentary, **no-LLM** indexer; it stores the verbatim chunk as the unit `document`, carries `locator`, `start_line/end_line`, `byte_start/byte_end`, `file_sha256`, `git_commit`, `manifest_sha256` and a provenance envelope (`adapters/repository_knowledge.py:362-409`, `repository_knowledge_index.py:99-230`). Unit ids are content-addressed (`make_repository_unit_id`, lines 40-52) and unchanged chunks replay their provenance (`_replay_unchanged`, 65-96). `repository_knowledge_sync.py:145` only dispatches relpaths whose sha changed (`_pending_relpaths`) and `_apply_retirements` tombstones retired paths with `superseded_by`. Markdown is chunked by heading section (`chunk_markdown`), text by line windows. What stops this being "ordinary document ingestion" is admission only: each file must be Git-tracked, Git-clean and listed with its sha in a hand-maintained manifest (`repository_knowledge_scope.py:504-520`, `573-645`), and `detect.py:90` rejects any `.md` outside that scope.
*Consequence:* building a parallel "source contract" creates the second identity scheme and second documentary pipeline that C09 warns against, and doubles the surface the recovery/authority docs must describe.
*Smallest correction:* define the first slice as a **sibling scope** (`ordinary_document_v1`): directory roots from config, identity = canonical path + content sha256, no Git/manifest requirement, reusing the chunkers, the documentary indexer (parametrised `source_type`/recipe) and the sync state. Keep the manifest route untouched.
*Verification:* a design note mapping each Packet 1 noun (revision, span, cache, idempotency) to the existing field or function, with the delta listed; a test that indexes a temp directory of `.md/.txt` through the shared indexer into an isolated Chroma dir.

**F02 (B) — The informal continuation experiment (E4, "six continuation tasks") duplicates the governed naturalistic study and can contaminate it.**
*Claim/path:* RESEARCH.md §5 E4; §1 "Recommended first outcome".
*Evidence:* `docs/plans/STATUS-naturalistic-product-value.md` §1–2: a landed, independently reviewed C0/C1 symmetric design with sealed samples and blinded adjudication, explicitly "methodology validation, not product evidence"; "V2-04+ and G6 are not authorized". E4 is the same comparison (fresh agent with ordinary file tools vs ConvMem) run informally with hand-written tasks and an uncalibrated grader.
*Consequence:* either the informal result is quoted as product value (which the arc forbids), or the episodes/tasks used informally are later unusable as sealed material. The packet's one-line disclaimer does not prevent either.
*Smallest correction:* drop E4 from the first slice. Keep E1/E3/E5 (mechanical, no product disposition). If a continuation check is wanted early, run it as a **labelled smoke test** on synthetic fixtures only, with no pass/fail verdict recorded, and list the fixtures as excluded from the later study.
*Verification:* the plan names which evaluation contracts in `eval_naturalistic/` the slice reuses, or states that it records no product-value observation.

### Must-fix in the plan

**F03 (M) — A new lexical index is sequenced before a free experiment that may remove the need for it.**
*Evidence:* `query.py:476-479` caps candidates at `min(max(top_k, 20), 100)`; keyword scoring (`:540`), cross-encoder rerank (`:554`) and rank fusion (`:557`) all operate inside that pool. Issue #320's only documented miss (Q02) is the raw neighbour at rank 22: a pool of 25 recovers it; the issue itself asks for a 20-vs-100 pool sweep with latency. A whole-collection exact-text scan **already exists** (`metadata_keyword_fallback.py:17-62`, reading Chroma metadata rows including `document`) but is reachable only on `ServingBackendTransient` (`query.py:511-517`).
*Consequence:* Packet 1 would spend the slice on an index whose benefit is unmeasured on this corpus, when two cheaper arms exist: raise `top_k_candidates`, and union the existing scan's top-N as a second candidate channel before rerank.
*Correction:* order the retrieval work as (1) pool sweep 20/50/100 on the locked cases, (2) existing keyword scan as an opt-in candidate channel, (3) a real lexical index only for misses that survive (1)+(2). Report latency per arm.
*Verification:* candidate-recall@pool and p95 latency per arm on the locked cases; the public golden Q02 as a regression guard.
*Note (H):* the private corpus (names, amounts, identifiers, Thai strings) makes me expect exact-text matching to matter; that is a hypothesis the sweep will test, not a reason to skip it.

**F04 (M) — "Bounded source reading into synthesis" collides with a fixed 12,000-character context budget the proposal never mentions.**
*Evidence:* `ask.py:74` `_MAX_CONTEXT_CHARS = 12000`, `:77` `_ASK_TOP_K = 8`; `_format_context` (`:475`) formats the unit `document` only; `chunk_expand.expand_record` is never called from `ask.py`; `expand` is a separate MCP tool (`mcp_server.py:803`).
*Consequence:* auto-expanding even two hits to "a complete short document" displaces the other six excerpts; the proposal's "read enough original context" silently trades breadth for depth without a rule.
*Correction:* specify the budget rule in the plan (e.g. expansion is a second stage invoked only for the top-k hits that the synthesis prompt marks as load-bearing, with a per-hit character cap and the original excerpt list preserved), or keep expansion as the explicit `expand` tool and have the first slice only make document hits **expandable** (today they return `not_session`, `chunk_expand.py:443-485`).
*Verification:* a characterization test showing context size and excerpt count before/after expansion on three cases.

**F05 (M) — The temporal/correction layer must not reuse `relates_to`; the packet does not say what it will use.**
*Evidence:* `relates_to` is required for decisions and verifications (`ledger.py:204`) and points at observations in the README example, yet `filter_superseded_decisions` (`evidence.py:258`) treats any decision→decision link as replacement, and `ASK_PROMPT` (`ask.py:25`) tells the model "the child decision replaces the parent — follow the child only". I found no document stating that invariant. Chroma metadata holds scalars only (`domains.py` docstring), so a unit cannot carry a list of typed edges.
*Consequence:* Packet 2 ("start with relations explicitly present in documents") will either overload the one existing edge or need a store the proposal has not named.
*Correction:* in the plan, (a) state that `relates_to` semantics are frozen and not reused; (b) name the carrier for typed relations (a sidecar JSONL/SQLite beside the existing decision logs is the obvious fit, not Chroma metadata); (c) start from the corrections Ryan's files already express explicitly (see F09) rather than inferred ones.
*Verification:* a written relation vocabulary (supersedes / corrects / owns / depends-on / unknown) with one fixture per relation and the existing supersession test still green.

**F06 (M) — "Neutralize coding-only prompt assumptions" is not free and should not be in the first slice.**
*Evidence:* `distill.py:19-36` is a locked, hashed recipe (`locked-distill-prompt-v1`, `ingest.py:1004-1012`); transform reuse is bound to semantic transform inputs (PR #399 per the Codex arc brief). `ASK_PROMPT` and `FOLLOWUP_ASK_PROMPT` (`ask.py:25, 47`) hard-code "past AI coding sessions".
*Consequence:* changing `DISTILL_PROMPT` creates a new distill generation, invalidates checkpoint reuse and splits the 21k legacy units into two recipes; the pilot does not need it because the documentary path bypasses distillation entirely (`repository_knowledge_index.py:1`).
*Correction:* leave `DISTILL_PROMPT` alone. Parametrise only the one framing sentence of the ask prompts by source mix (documents vs sessions), under a prompt version tag, and guard with the existing `test_ask_characterization.py`.
*Verification:* the characterization test and the public golden fixture unchanged on the coding corpus.

**F07 (M) — The documentary indexer is hard-wired to the production write session; the first slice must run isolated.**
*Evidence:* `repository_knowledge_index.py:275` opens `production_chroma_write_session(entrypoint=...)` and ignores its `chroma_dir` argument (the function is flagged `unused-argument`); tests monkeypatch the session (`tests/test_repository_knowledge_adapter.py:198`). `config.py:29-30` honours `CONVMEM_CONFIG`; `incremental_jsonl_isolation.write_hermetic_config` (`:132`) writes an isolated config with its own `chroma_dir`. `docs/RECOVER.md:57` records that `index` keeps a retained exemption from the Restic gate and that "replacement indexing can supersede/delete existing units".
*Consequence:* a pilot that "just runs index" on new roots writes to the live corpus under an exemption the policy itself calls an owner boundary, not a safety proof.
*Correction:* the slice runs only under `CONVMEM_CONFIG` pointing at a hermetic config; any production-root change remains Packet 0 and Ryan-gated. Make the isolated path a supported parameter rather than a test monkeypatch.
*Verification:* an assertion in the slice's runner that the resolved `chroma_dir` is under the isolation root; the known-production-roots check in `incremental_jsonl_isolation.py:79`.

**F08 (M) — The source contract has an unacknowledged sibling vocabulary in the repository.**
*Evidence:* `eval_naturalistic/v2/evidence.py:19-39` (`SourcePresenceV2`, `VerbatimEvidenceAvailabilityV2`, `SummaryEvidenceAvailabilityV2`) and `eval_naturalistic/v2/adapters/capability.py:35-97` (`RevisionAsofBindingCapability`, `PreservationReplayCapability`, `TemporalReproducibilityCapability`, `EvidenceCompletenessCapability`, …) already define the evidence properties the proposal wants to build, and `ConditionNeutralEvidenceAvailabilityV2` (`evidence.py:194`) was written for issue #263. They are used only by the evaluation harness.
*Consequence:* a runtime contract written in new words will not be measurable by the evaluation that already speaks these words.
*Correction:* express the ordinary-document scope's guarantees as a capability vector in that vocabulary (which values it attains, which it does not), and cite it in the plan.
*Verification:* one capability-manifest entry for `ordinary_document_v1`.

**F09 (M) — The corpus already carries an explicit source-ownership / correction / lesson convention; the plan should read it, not invent a general schema first.**
*Evidence (private, see §6):* the lessons guide I read declares `Role: explainer … not an owning record`, has 12 numbered lessons each with `Learned:` / `Evidence:` / `Still open:` lines, 18 dated `Correction <date>:` bullets, `UNKNOWN` markers, a documented `Retired` rule and relative links to seven owning records (including one named "Source_Of_Truth"). The derived list declares `Authority: derived view — it owns no fact … the source wins`, a six-row Subject→Owner table, and `Prepared: <date>. Snapshot, not live state`.
*Consequence:* Packets 2 and 4 are largely **parsing problems** for this corpus, not modelling problems; a deterministic extractor of these markers gives source ownership, corrections, lessons, unknowns and a freshness check (owner content changed after `Prepared`) with no LLM and no new truth-resolution logic. The packet credits "explicit lessons already present in your field guides" (§H) but does not make them the first mechanism.
*Correction:* add deterministic convention extraction to the first slice; defer generalised extraction until files that lack the convention are in scope.
*Verification:* extractor output on a **synthetic** public fixture that mirrors the convention; stale/fresh verdicts on a fabricated owner change.
*Limit:* verified on 2 files from one account; whether the second account's files follow any convention is unknown (§6).

### Improvements

**F10 (m) — Packet 4's "project working set" already exists as `brief` / `brief-project`.** `mcp_server.py:687-760` and `brief.py` compute recent decisions, monitor units, inter-model handoff staleness (`_handoff_staleness`, `:350`) and a `generated_at` stamp (`:717`). The proposal should extend this tool with source-revision inputs rather than add a new one.

**F11 (m) — Idempotency is already satisfied for the no-LLM path; say so and measure it.** Whole-file skip via `processed.json` (`ingest.py:1433`, with the deliberate repository-knowledge exception) plus sha-based pending dispatch in the sync layer means an unchanged scan performs no embedding. A changed file re-embeds every chunk locally (`repository_knowledge_index.py:143` runs before replay) — cheap, but the E5 metric should count it. The "expensive processing" concern only arises if the slice adds LLM extraction, which it should not.

**F12 (m) — Deletion semantics are already conservative, and intentionally so.** A `FileDeletedEvent` merely queues the path (`watch.py:626-649`); a missing file is skipped at detection, so units persist and `expand` reports unavailability; intentional removal is the manual `exclude --purge` route. E3's "an unavailable disk must never trigger mass deletion" holds today by absence of any deletion inference. The plan should state this and keep it, rather than design a scan-completion rule the first slice does not need.

**F13 (m) — Thai handling is correctly described but one consequence is unstated.** `_search_tokens` (`query.py:115`) drops every non-ASCII character, so a pure-Thai query yields no tokens and `_keyword_score` falls back to whole-query substring matching. That is adequate for exact phrases and useless for partial ones; the Packet 3 tokenizer test should include that baseline explicitly.

**F14 (m) — The 48-case suite will be private by construction and therefore CI-invisible, repeating #320's failure mode.** Cases built from private files cannot live in the repository; the golden eval is already skipped in CI for needing the live corpus. The plan needs a small synthetic public mirror (fabricated files that reproduce the conventions and failure types) so the *mechanics* run in CI, with the private cases reported separately by Ryan.

**F15 (m) — Deferrals are justified, with one open dependency.** Switchboard is a read-only connector whose PR is RED on unrelated defects (`STATUS-openclaw-convmem-integration.md` §2); nothing in the pilot consumes it. Graph replacement is argued correctly from the vendors' own tables (Zep's single-session-assistant regression and Mem0's full-context lead checked). The one caveat is F05: typed relations need *some* carrier, and that should be anticipated as a sidecar, not mistaken for a graph database.

**F16 (m) — Research accounting is honest but unauditable.** "184 slots / 30 searches" is correctly labelled as not evidence strength; raw transcripts were not kept (`SOURCE-REGISTER.json` limits), so selection bias cannot be checked. The four primary sources I did check were represented accurately, including each paper's own caveats.

### Open questions

**F17 (Q) — Breadth.** The proposal covers documents, current state, lessons and project resumption. It does not say how **preferences** (standing rules such as "do not list the obvious") and **task state** (open TODO ledgers with owners and dates, which the private files use heavily) are represented; both appear in the corpus and neither is a document-QA problem. Should they be first-class record kinds in Packet 4, or stay inside the convention extractor as "standing rule" and "open item" markers?

**F18 (Q) — Authority of the verbatim copy.** For non-Git folders the only "preserved original" the slice can offer is the verbatim chunk stored in Chroma (as the repository-knowledge path does), backed by Restic. That keeps Chroma authoritative (consistent with `CURRENT-OBSERVATION-AUTHORITY.md`) and avoids a blob store, but it means a byte-exact original is preserved only at chunk granularity. Is that acceptable to Ryan, or is a Restic snapshot reference per source revision required from the start?

**F19 (Q) — Daily client.** Deferring Switchboard assumes OpenClaw is not the client Ryan resumes work from. If it is, the calculus changes.

## 4. Strongest alternative

**Baseline-first: measure before building.** Run the null hypothesis the handoff itself raises — a fresh agent with plain local tools (`rg`/grep, file open, directory listing) against the same three Markdown areas — on a locked 24-case set, alongside current ConvMem, current ConvMem with `top_k_candidates=100`, and an oracle-evidence arm as a diagnostic only.

*Likely advantage:* Ryan's documents are self-describing (owner tables, dated corrections, relative links). On "original detail" and "what is current" cases a grep-and-open agent may tie or beat vector-first ConvMem at lower cost, which would mean ordinary-document ingestion is **not** the bottleneck and the valuable work is the convention layer (F09), transcript evidence (#263) and cross-workspace reasoning — the things grep cannot do.

*Fair experiment:* same model, same token budget, same tool-call cap, same file access, one run per arm per case, pass/fail/pending reported separately, errors labelled (candidate recall / ranking / omitted context / synthesis), no LLM judge without the stale / topical-but-wrong / fabricated-citation calibration set. If the grep arm matches ConvMem on ≥ 6 of 8 original-detail cases and ≥ 6 of 8 current/history cases, I would choose this alternative's conclusion (skip generic document ingestion; build F09 + #263 first). If ConvMem wins only with the larger pool, F03's order stands and the lexical index stays deferred.

This alternative is compatible with §5: it is the first acceptance observation of the revised slice, run before the sibling scope is wired by default.

## 5. Revised first slice

**Name:** `ordinary_document_v1` — isolated, convention-aware Markdown/TXT evidence for three project areas.

**Deliverable (what exists at the end):**
1. A sibling scope beside `repository_knowledge_v1`: configured directory roots, `.md`/`.txt` only, identity = canonical path + content sha256, chunked by the existing heading/line chunkers, indexed verbatim through the existing documentary indexer with a distinct `source_type` and recipe id, tracked in the existing sync state (pending/indexed/retired by sha). No manifest, no Git requirement, no LLM.
2. Deterministic convention extraction into scalar metadata plus a sidecar record: role/authority header, owner table rows, `Prepared:` date, `Learned:` dates, `Correction <date>:` bullets, `Still open:`, `UNKNOWN`, `Retired`. A derived view is reported **stale** when any owner's content hash differs from the hash recorded when the view was last indexed (heuristic, labelled as such).
3. Document hits become expandable: `expand_record` resolves `byte_start/byte_end` for document units and reports `exact` / `drifted` / `unavailable` like session chunks.
4. A pool-size sweep (20/50/100) and an opt-in keyword candidate channel using the existing metadata scan, both behind config, both measured before either is defaulted.
5. A locked 24-case set (8 original detail, 8 current/history including one late-arriving older file, 8 cross-source), 6 held out, built from the three Markdown areas plus one transcript area; a synthetic public fixture (three fabricated files reproducing the conventions) so the mechanics run in CI.

**Dependencies:** `CONVMEM_CONFIG` + hermetic config (isolation root); local Ollama embeddings; the existing documentary indexer accepting a non-production session as a supported parameter. **Not** dependent on Packet 0 while isolated; any production-root or watcher change remains Packet 0 and Ryan-gated.

**Exclusions (removed from the author's Packet 1):** a new "separate source contract" (replaced by the sibling scope); a new lexical index (replaced by sweep + existing scan); `DISTILL_PROMPT` or general ask-prompt rewrites (replaced by one tagged framing sentence); automatic source expansion inside `ask` (replaced by expandable document hits + an explicit budget rule for a later slice); the 48-case suite and six continuation tasks (replaced by 24 locked cases and no product-value claim); explicit correction *handling* in synthesis (replaced by correction *extraction*; application is Packet 2).

**Added (not in the author's proposal):** isolation via `CONVMEM_CONFIG`; pool-size sweep; convention extraction and heuristic freshness; capability-vector alignment with `eval_naturalistic/v2`; public synthetic fixture; baseline grep arm.

**Acceptance observations (all isolated, all reported as counts):**
- Unchanged rescan: 0 embeddings, 0 new units; one appended paragraph: only that section re-indexed; rename across roots: identity preserved, locator updated; edit of a cited section: `drifted`; directory disconnected: `unavailable`, 0 tombstones.
- Candidate recall on the 24 cases for each arm (current / pool 100 / +keyword channel / grep baseline / oracle), plus p95 latency.
- Every citation resolves to the exact bytes it was indexed from, or reports drift honestly.
- Convention extractor reproduces the synthetic fixture's owners, corrections, lessons and unknowns; a fabricated owner change flips the derived view to stale.
- No write touches a known production root (assertion in the runner).
- Existing golden fixture and `test_ask_characterization.py` unchanged.

**Stop condition:** if the grep baseline ties ConvMem on the original-detail and current/history groups, do not expand ingestion breadth; pivot the next slice to F09 depth and #263 transcript evidence.

## 6. Evidence limits

- **Private corpus:** the private companion and the backup receipt were read. Of the nine Ryan-account files it names I read two in full and the metadata of one more; all three are Markdown. Their structure matches the companion's description closely. The **second account's files were not reachable** from this session, so every claim about spreadsheets, PDFs, Thai documents and media in the companion is **unverified** here, and so is the "three Markdown areas" generalisation beyond Ryan's own files. The private ZIP archive was not opened; the public packet was verified from Git instead.
- **Runtime:** no live PC, no preserved cloud runtime, no doctor run, no test-suite run. Statements about the watcher, the production write session and the Restic gate are code and policy readings, not observed behaviour. The 21,420-unit corpus figures come from the 2026-07 authority audit and were not re-counted.
- **Literature:** four of 28 register entries were checked at source (two arXiv pages, one mirror because arXiv rate-limited the third, one issue pair); the rest rest on the register's own caveats and my prior knowledge. "Faithfully represented" applies to the sampled set.
- **Issues:** #263 and #320 were read through a web fetch of the issue pages; the three commits #263 references were not individually inspected and none of their verbatim-evidence code is reachable from the retrieval path at `d54f92b` (the only `verbatim` adapters are under `eval_naturalistic/v2/`).
- **Hypotheses labelled above:** F03's expectation that exact-text matters on this corpus; F09's expectation that convention extraction covers most of Packets 2 and 4; §4's expectation that a grep baseline ties on self-describing documents. None is established.
- **Not done, deliberately:** no fixture, prototype or test was written; no corpus, service, config or Drive file was changed; no paid model was called.

**Review state:** verdict delivered; author revision of Packet 1 pending; no implementation authorised.
