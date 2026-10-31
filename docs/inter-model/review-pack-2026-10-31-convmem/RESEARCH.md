<!-- Generated from the preserved research.html; no new research results added. -->

Research brief · 31 October 2026

# ConvMem: reliable memory for work across your PC

Build around recoverable original evidence, then add the smallest useful layers of current state, lessons, and task context. Require each layer to improve real work over a strong source-search baseline.

This research refines the earlier assessment of [ConvMem](https://github.com/alanmz-crypto/convmem) at main `d54f92b`. The intended system remains local to your PC and useful across AI clients and domains. Drive supplied representative work in the preceding review; its connector limitations are not product requirements.

Scope: 30 Exa searches across six workstreams, requesting 184 result slots. These include duplicates, paper versions, mirrors, and rejected results; they are not 184 independently validated studies. Recommendations below draw on primary papers, official implementations, and documentation. Twenty-eight selected references are listed at the end, grouping versions and related documentation. Private Drive content was not submitted to web search. No project source, corpus, Drive file, service, or external publication was changed. Only local research artifacts were created.

## 1. What the research changes

**Move preservation and retrieval ahead of general fact extraction.** Extracted facts can be excellent search keys and compact views, but should not be the only surviving representation. LongMemEval finds that aggressive fact compression can lose useful information; research on raw-memory search and filesystem stores provides additional reasons to test preserved evidence first. These results vary by model and task, so they support a controlled pilot, not a universal claim that summaries are bad. [[1]](https://arxiv.org/html/2410.10813v2) [[2]](https://arxiv.org/html/2607.26637) [[3]](https://arxiv.org/html/2511.21726v1)

**Make current state a reproducible view.** A project brief should name the source revisions that produced it and become stale when they change. It should not become another competing authority document. This is my architectural recommendation: it combines ConvMem's existing provenance with the source-ownership conventions already present in your files.

**Pull cheap, idempotent capture into the first implementation.** Do not wait for a later optimization arc to avoid processing unchanged material. Preserve or register source revisions promptly, make them searchable, and queue optional expensive derivations. LightMem supports separating online interaction from consolidation, but its compression and timestamp-based update policies should not be copied wholesale. [[4]](https://arxiv.org/html/2510.18866v4)

**Evaluate continuation and maintenance, not just answers.** A useful system must apply a correction on the next task, preserve old history, avoid repeating failed work, and keep citations valid after files change. MemoryBench and RealMem motivate these dimensions, but both use constructed interaction settings; they do not establish performance on your projects. [[5]](https://arxiv.org/html/2510.17281v4) [[6]](https://arxiv.org/html/2601.06966)

**Recommended first outcome:** a fresh AI session can resume job preparation, relocation planning, or room-search research; identify what is established and what changed; retrieve the exact evidence; and apply a relevant prior lesson without reprocessing unchanged history.

## 2. Ideas worth adopting or testing

### A. Preserve evidence; let memory have several views

Separate four logical layers: original source revisions; extracted passages/tables with native locations; optional assertions and lessons; and query-specific working context. These need not be four databases. Keep the existing Chroma deployment while adding missing source and extraction contracts. A new embedding model should not require reparsing a textbook, and corrected OCR should not erase the original page.

HippoRAG 2 is instructive: its graph design adds passage nodes to address context loss in entity-focused representations. LongMemEval similarly supports keeping source content available alongside extracted keys. Borrow the preservation principle before adding automatic entity graphs. [[7]](https://arxiv.org/html/2502.14802) [[1]](https://arxiv.org/html/2410.10813v2)

**Boundary:** “preserve” does not mean duplicate everything forever. Define which revisions need retention, how unavailable originals are represented, and how intentional deletion affects derived records and backups. Extraction JSON is faithful to the extracted representation, not proof that extraction captured the source perfectly.

### B. Add independent exact-text search before replacing embeddings

ConvMem currently reranks a small vector-selected candidate pool. A lexical boost inside that pool cannot recover an exact name, quotation, identifier, or amount outside it. Add an independent lexical channel over original passages and metadata, combine candidates with semantic results, then rerank. QMD is a useful local implementation reference for separate lexical/vector search, source retrieval, and MCP access; it is not a recommendation to replace ConvMem or copy its entire runtime. [[8]](https://github.com/tobi/qmd)

Use reciprocal rank fusion as an initial baseline, not an article of faith. A primary fusion analysis finds normalized score combinations stronger in its tested settings and shows that RRF is parameter-sensitive. Compare both only after the independent channels work. Keep the original query and strong exact matches visible. [[9]](https://arxiv.org/html/2210.11934v4)

**Low-cost extension:** index each passage with its actual title, section, project and relevant date. Keep those annotations separate from the quoted source. Anthropic's contextual retrieval experiments support context enrichment, but its reported 49% and 67% reductions are retrieval-failure reductions in its own evaluation, not projected answer-quality gains for ConvMem. Test deterministic prefixes before paying a model to generate them. [[10]](https://www.anthropic.com/engineering/contextual-retrieval)

### C. Retrieve narrowly, then read enough original context

Use small passages for discovery, then expand selected matches to include qualifications, headings, neighbouring paragraphs or a complete short document. ConvMem already has bounded transcript expansion; connect it to ordinary answers and extend it to document locations. Expansion cannot fix discovery failure, so measure these stages separately.

Before creating summary trees, test grouping selected passages by source and restoring their original order. DOS RAG matched or exceeded more elaborate methods under matched token budgets on three long-document QA benchmarks. This is a cheap hypothesis for ConvMem, with English-document and benchmark limitations. [[11]](https://aclanthology.org/2025.emnlp-main.1656/)

For questions that span projects, allow a bounded follow-up search. Preserve the original question and explicit entity names in every subquery. Decomposition research reports both benefits and harmful cases; ChainRAG highlights entity loss when later subqueries replace a name with vague language. Do not add query expansion to every lookup. [[12]](https://arxiv.org/html/2507.00355v1) [[13]](https://arxiv.org/html/2502.14245v1)

### D. Remember when a claim applied and when it was learned

Store recorded/learned time separately from effective time when known. Permit unknown, approximate and future-effective dates. A file discovered today can describe a situation from last year; ingestion order must not decide current truth. Also preserve whether a statement is a proposal, scenario, report, confirmation, correction or disputed assertion.

Zep's bitemporal design is useful inspiration, but its described invalidation procedure gives new information priority along the ingestion timeline. That is a poor default for late-arriving archives. ConvMem should initially follow explicit correction and source-ownership relationships, and return unresolved conflicts together rather than invent a winner. [[14]](https://arxiv.org/html/2501.13956)

**High-value test:** ingest an old plan, a correction, and then an older document found later. Repeat in a different order. Answers about what applied on a given date should agree when the available evidence is the same. Answers about what the system knew at that earlier time may legitimately differ.

### E. Make the write path cheap and every derived view visibly fresh or stale

Track a stable logical source identity separately from location and content hash. Cache stages by their complete inputs: source content, contextual metadata, parser/options, extraction model and embedding configuration as appropriate. Two identical copies may share processing while retaining distinct locations; a rename should not trigger new paid reasoning. LlamaIndex demonstrates transformation caching and document-ID/hash tracking without making its framework necessary. [[15]](https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/)

Capture and optional consolidation should have separate budgets. New source evidence should remain discoverable while a derived brief is pending. Mark that brief stale rather than serving it as current. Publish replacement generations only when complete; reuse ConvMem's existing publication and recovery mechanisms where they meet this requirement. LightMem provides evidence for moving expensive consolidation out of the immediate interaction path, but total offline work must still be counted. [[4]](https://arxiv.org/html/2510.18866v4)

**Deletion rule:** a one-file update, interrupted scan or disconnected disk is not a complete inventory. Only a completed scan of a named scope can establish disappearance. Distinguish unavailable, unreadable, unindexed and intentionally deleted sources. This rule is particularly valuable for a PC with removable drives.

### F. Keep document structure and numerical meaning

Docling is a strong parser candidate because its document model retains hierarchy, tables, reading order, bounding boxes where available, and provenance. Its structured JSON should be retained alongside optional Markdown for reading. Compare it with a lighter native PDF extraction path on your own pages; feature lists are not evidence of accuracy on your corpus. [[16]](https://docling-project.github.io/docling/concepts/docling_document/)

Use native structure for DOCX, CSV and XLSX. Spreadsheet memory must distinguish displayed values from recomputed answers and preserve formulas, cell types, units and locations. `openpyxl` does not evaluate formulas; `data_only` reads cached values, which may be absent or stale. Use explicit deterministic calculations or a qualified spreadsheet engine on a copy, recording the input revision and calculation. [[17]](https://openpyxl.readthedocs.io/en/stable/simple_formulae.html)

Run a 20-page parser comparison across digital PDFs, scans, columns, tables and Thai/mixed-language pages. Score exact names/dates/amounts, row-column relationships, reading order, locators, seconds/page and peak memory separately. OmniDocBench provides a useful evaluation decomposition; its Chinese/English coverage does not establish Thai performance. [[18]](https://arxiv.org/html/2412.07626)

Dependency choices: [Docling's code is MIT](https://github.com/docling-project/docling), while model licenses are separate. PyMuPDF is a viable local comparison with [AGPL/commercial licensing](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright); decide deliberately how it would integrate with the public MIT project. No licensing issue requires a storage rewrite. Pin tested package/model versions and verify offline startup after model prefetching.

### G. Treat Thai and cross-language retrieval as measured capabilities

A Unicode-aware regex alone does not solve Thai word boundaries. Test a Thai tokenizer such as PyThaiNLP's local engines, exact-name/alias handling, and four retrieval directions: Thai-to-Thai, English-to-Thai, Thai-to-English, and mixed-language. Include numbers, transliterations, OCR noise and plausible wrong-person/date distractors. [[19]](https://pythainlp.org/docs/5.1/api/tokenize.html)

SEA-BED evaluates 17 models across 169 datasets, nine task categories and ten Southeast Asian languages, finding no uniform winner. BGE-M3 and multilingual E5 are reasonable isolated comparison candidates, not predetermined upgrades. Preserve the current embedding index until a candidate earns its rebuild and local-runtime cost. [[20]](https://aclanthology.org/2026.acl-long.397/)

PaddleOCR publishes an explicit Thai recognition model, but its recognition benchmark is not full-document or table accuracy. Use it where native extraction fails and verify important names and figures against page images. [[21]](https://huggingface.co/PaddlePaddle/th_PP-OCRv5_mobile_rec)

### H. Add lessons that can improve the next attempt

A useful lesson records applicability, the source episode, what happened, the observed result, a proposed better procedure, and counterexamples or retirement conditions. Start with the explicit lessons already present in your field guides. Retrieve a few relevant lessons beside current evidence. A rejected option should retain why and when it was rejected; it should not become a universal prohibition.

Reflexion and Voyager demonstrate outcome-informed memory in bounded tasks. ACE contributes a particularly useful mechanism: identified lesson entries and small deterministic updates, rather than repeatedly rewriting a large memory summary. These studies do not establish general personal-assistant improvement, and ACE acknowledges that weak reflection can add harmful noise. [[22]](https://arxiv.org/html/2303.11366) [[23]](https://arxiv.org/html/2510.04618)

Keep observations, inferred lessons and approved preferences distinct. Repeating one AI-generated summary ten times does not create ten independent confirmations. MemoryGraft shows how successful-looking stored experiences can influence later agents in its experimental setup; the practical response is to preserve origin and prevent retrieved content from granting authority. This is a targeted design test, not a claim that ConvMem currently has that vulnerability. [[24]](https://arxiv.org/abs/2512.16962)

### I. Offer a compact project working set through existing tools

A “resume project” result can contain current objectives, constraints, decisions, unresolved questions, recent changes, applicable lessons and source links within a token budget. Its contents should be derived from identified sources and expanded on demand. Do not insert every memory into every turn. Anthropic's engineering guidance supports selective retrieval and progressive disclosure; MemGPT supplies an earlier architecture for bounded working context and external recall. [[25]](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) [[26]](https://arxiv.org/abs/2310.08560)

This should remain an additive CLI/MCP capability, not a new agent framework. Keep memory retrieval separate from permission to execute actions. Domain-specific helpers can use the same evidence service for study, money, household projects or software without forcing every task into one representation.

## 3. What not to adopt yet

**A graph database replacement.** Mem0's own reported comparison places full context above its memory variants on absolute answer score; its graph variant adds cost and is not better on every category. Zep's aggregate improvement coexists with worse recall of assistant-message content in one breakdown. These are vendor-run studies, but their own results already argue against assuming graph complexity is a universal upgrade. [[27]](https://arxiv.org/html/2504.19413) [[14]](https://arxiv.org/html/2501.13956)

**Automatic rewriting of the whole memory collection.** Filesystem research finds search-economy gains from organization without a universal accuracy advantage, and shows organization can degrade as stores grow. Preserve inspectable sources and use bounded changes to derived views. [[2]](https://arxiv.org/html/2607.26637)

**Late chunking as the first retrieval change.** It is promising for cross-paragraph context and has been studied with the nomic embedding family, but requires compatible token-level encoding/pooling. A changed early paragraph can affect several chunk vectors. Test structural prefixes and source expansion first. The paper reports task-dependent results rather than universal gains. [[28]](https://arxiv.org/html/2409.04701v3)

**Optional connector/publication work as the main product milestone.** Existing CLI/MCP access is enough for the pilot. Preserve Switchboard's work and evidence, but prioritize it when a demonstrated workflow cannot proceed without it. Likewise, do not make a full corpus migration, all-file OCR or a new benchmark platform prerequisites for a small useful slice.

## 4. A bounded implementation sequence

**Packet 0 — establish the restart baseline.** Reconcile current source, preserved runtime, deployed PC revision and complete backup state. Qualify recovery and host health before live writes or unattended capture. This does not block fixture-based research or isolated implementation while the PC is in transit.

**Packet 1 — original-evidence pilot.** Add ordinary Markdown/TXT ingestion behind a separate source contract, stable revision/span references, stage caching, independent lexical candidates and bounded source reading. Preserve explicit source-ownership and correction statements in the pilot evidence from the start; Packet 2 generalizes their handling. Use the three textual project areas from the prior assessment. Neutralize coding-only prompt assumptions. Deliver a fresh-session continuation demonstration and failure breakdown, not a new framework.

**Packet 2 — updates and trustworthy current state.** Add explicit source ownership/corrections, separate learned/effective times, derived-view freshness and update/delete propagation. Start with relations explicitly present in documents. Return ambiguity rather than require automated universal truth resolution.

**Packet 3 — prove a different representation.** Compare PDF parsers and targeted Thai OCR; add structured spreadsheet ingestion and reproducible calculations. Require one exact study-passage task and one numeric task. This prevents three Markdown-heavy domains from being mistaken for all-format capability.

**Packet 4 — useful procedural memory and project resumption.** Index existing explicit lessons as scoped records and compose a small project working set. Measure whether these reduce repeated errors on new tasks. Automate lesson extraction only if the manually grounded version helps.

**Only then expand.** Broaden ingestion, test multilingual embedding replacements, selective decomposition, late chunking, or graph-assisted retrieval according to the observed failure distribution. Keep one reliability track and one product slice active. A successful isolated experiment is not automatic authorization to deploy it or ingest the entire PC.

## 5. Experiments with clear decision value

**E1 — Does extraction earn its cost?** Compare current ConvMem, raw-passage lexical/semantic retrieval, and that same retrieval augmented with extracted claims. Hold sources, generator, embedder, answer prompt and context budget fixed. Measure all-required-evidence recall, citation support, false certainty, write/query cost and latency. Promote claim extraction only for failures it demonstrably fixes.

**E2 — Can it survive out-of-order history?** Replay an initial plan, an explicit correction, a late-arriving old file, a hypothetical scenario and a partial retraction. Ask current-state, effective-date and knowledge-at-the-time questions after each step. Include unknown effective dates; manufactured precision is a failure.

**E3 — Are citations and deletion semantics honest?** Rename a file, move it across a root, alter a cited passage, add an identical copy, disconnect the directory, and delete a source intentionally. Check exact/drifted/unavailable states, scope-bound deletion and dependent-view invalidation. An unavailable disk must never trigger a mass deletion inference.

**E4 — Does memory help continuation?** Give a fresh AI the same task and access to the same collection with ordinary file-search tools versus ConvMem. Use two bounded tasks per pilot domain. Assess preserved constraints, next valid action, missing questions, repeated work, elapsed time and successful completion. Supplying preselected relevant evidence is an oracle condition for diagnosis, not a fair ordinary-search baseline.

**E5 — Are ingestion economics sustainable?** Measure unchanged rescan, one append, middle edit, parser/model-version change and interruption during replacement. Report actual extraction, embedding and paid calls, time, peak memory, active duplicates and stale records. Background consolidation costs belong in the total.

**E6 — Does a remembered lesson transfer appropriately?** Compare original evidence alone, ordinary summaries, and original evidence plus scoped lesson cards. Use a later analogous task and a deliberately different task where the lesson should not apply. Check outcomes and repeated mistakes, not how thoughtful the generated plan sounds.

Start with **48 engineering cases**: eight each for original detail, current/history, cross-source reasoning, unknown/conflicting/hypothetical information, procedural reuse, and structured answers. Treat Thai/English, paraphrase distance, duplicates and source changes as cross-cutting tags. Reserve 12 cases, preferably separated by source family, for untouched checks. Add six continuation tasks. Later-format cases can remain explicitly pending until the adapter exists. Report passed, failed and pending counts separately; an unsupported case is neither a pass nor evidence of coverage.

Each case should name source revisions, query time, required evidence, forbidden conclusions and a resource budget. Include an oracle-evidence diagnostic and a complete-document control when the collection fits. Label errors by extraction, candidate recall, ranking, omitted context, temporal interpretation and synthesis. Calibrate any LLM judge against stale, wrong-but-topical and fabricated-citation answers. Report case counts as well as percentages.

**Proposed acceptance rule:** no invented confirmations or unsupported numerical answers on the locked critical cases; all citations must resolve honestly; unchanged ingestion must avoid repeated expensive work. These are local release observations, not guarantees of universal reliability. A small acceptance suite does not replace ConvMem's separately governed naturalistic study.

## 6. Selected sources and how much to trust them

Numbers below refer to the links in the report. Academic and vendor studies have different settings and graders; their scores should not be compared as a shared leaderboard. Preprints are useful evidence to examine, not settled conclusions. Official documentation establishes an interface or mechanism, not superior product performance.

**[1] LongMemEval.** [Original paper, ICLR 2025.](https://arxiv.org/html/2410.10813v2) Five memory abilities, source granularity and extraction experiments. Evidence conversations are constructed and edited; not a personal-file deployment.

**[2] Filesystem-Based Memory for LLM Agents.** [July 2026 preprint.](https://arxiv.org/html/2607.26637) Organization, growth and search-cost comparisons. Small per-condition samples and model/harness dependence limit generalization.

**[3] SUMER.** [Goal-Directed Search Outperforms Goal-Agnostic Memory Compression.](https://arxiv.org/html/2511.21726v1) Raw-memory search with reinforcement learning. Training and benchmark choices are part of the result; it does not show that a simple untrained search loop reproduces the gain.

**[4] LightMem.** [Original paper, version 4.](https://arxiv.org/html/2510.18866v4) Lightweight stages and offline consolidation. Borrow the separation of costs; test compression and update semantics independently.

**[5] MemoryBench.** [Version 4.](https://arxiv.org/html/2510.17281v4) Feedback-based learning across tasks and languages; complex memory does not consistently win. Simulated users and assisted grading remain limitations.

**[6] RealMem.** [Original project-oriented memory study.](https://arxiv.org/html/2601.06966) Useful evolving-project design; interactions are synthesized despite the name.

**[7] HippoRAG 2.** [Original paper.](https://arxiv.org/html/2502.14802) Passage-preserving graph retrieval with error analysis. Heavy reference models and extra retrieval stages complicate local transfer.

**[8] QMD.** [Official repository.](https://github.com/tobi/qmd) Inspectable local lexical/vector search and source-reading interface. Implementation reference, not an independent quality comparison.

**[9] Hybrid fusion analysis.** [Bruch, Gai and Ingber.](https://arxiv.org/html/2210.11934v4) Comparative fusion evidence; no universal parameter choice for this corpus.

**[10] Contextual Retrieval.** [Anthropic's original engineering report.](https://www.anthropic.com/engineering/contextual-retrieval) Vendor-run retrieval experiment. Retrieval-failure rates are not answer accuracy or ConvMem forecasts.

**[11] Stronger Baselines / DOS RAG.** [EMNLP 2025 paper.](https://aclanthology.org/2025.emnlp-main.1656/) Source-order reading under matched budgets. English long-document benchmarks differ from changing personal projects.

**[12] Question Decomposition for RAG.** [Original paper.](https://arxiv.org/html/2507.00355v1) Useful compound-query experiments; additional calls and harmful single-hop cases.

**[13] ChainRAG.** [Original paper.](https://arxiv.org/html/2502.14245v1) Entity preservation in multi-step retrieval; its full graph architecture is unnecessary to test that principle.

**[14] Zep / Graphiti.** [Original paper.](https://arxiv.org/html/2501.13956) Bitemporal graph design and vendor evaluation. Aggregate gains conceal some category regressions; new-ingestion priority requires caution with archives.

**[15] LlamaIndex ingestion.** [Official pipeline documentation.](https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/) Transformation caching and document management. Complete-scope deletion semantics must be distinguished from partial watcher batches.

**[16] Docling.** [Document model](https://docling-project.github.io/docling/concepts/docling_document/), [technical report](https://arxiv.org/html/2408.09869v4), and [local deployment options](https://docling-project.github.io/docling/usage/advanced_options/). Structured extraction and locators; actual parser correctness still requires a corpus-specific check.

**[17] Spreadsheet execution.** [openpyxl formula documentation](https://openpyxl.readthedocs.io/en/stable/simple_formulae.html) and [LibreOffice recalculation](https://help.libreoffice.org/latest/en-US/text/scalc/01/calculate.html). Parsing formulas, reading caches and recalculating are distinct operations.

**[18] OmniDocBench.** [Original benchmark paper.](https://arxiv.org/html/2412.07626) Separate text, table, formula and reading-order metrics; Chinese/English coverage cannot establish Thai results.

**[19] PyThaiNLP.** [Official tokenizer documentation.](https://pythainlp.org/docs/5.1/api/tokenize.html) Local segmentation choices and dictionaries; select with names and mixed-language tests.

**[20] SEA-BED.** [ACL July 2026 paper.](https://aclanthology.org/2026.acl-long.397/) Region-specific embedding evaluation. Useful candidates include [BGE-M3](https://huggingface.co/BAAI/bge-m3) and [multilingual E5](https://arxiv.org/html/2402.05672), subject to local evidence.

**[21] Thai OCR.** [Official PaddleOCR model card](https://huggingface.co/PaddlePaddle/th_PP-OCRv5_mobile_rec) and [multilingual documentation](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html). Developer-reported recognition metrics do not establish complete-document fidelity.

**[22] Reflexion and Voyager.** [Reflexion paper](https://arxiv.org/html/2303.11366) and [Voyager project](https://voyager.minedojo.org/). Outcome-informed lessons and skill reuse in bounded environments.

**[23] ACE.** [Agentic Context Engineering paper.](https://arxiv.org/html/2510.04618) Itemized lessons and incremental updates. Reflection quality and task suitability constrain benefits.

**[24] MemoryGraft.** [Primary preprint.](https://arxiv.org/abs/2512.16962) Experience-memory poisoning in a specific agent setup; motivates source-origin and promotion-boundary tests, not a diagnosis of ConvMem.

**[25] Context engineering.** [Anthropic engineering.](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) Firsthand guidance on bounded context and selective reading; operational guidance rather than a controlled product benchmark.

**[26] MemGPT.** [Original paper.](https://arxiv.org/abs/2310.08560) Working context versus external recall; older model/context assumptions.

**[27] Mem0.** [Original paper.](https://arxiv.org/html/2504.19413) Vendor research with cost-quality tradeoffs; excludes unanswerable/adversarial cases in the reported evaluation. Retrieved-context token counts are not total lifetime processing cost.

**[28] Late Chunking.** [Version 3.](https://arxiv.org/html/2409.04701v3) Contextual token encoding before chunk pooling. Promising, but task-dependent and a change to embedding/runtime and incremental-cache assumptions.

Prepared as a research recommendation, not an implementation or deployment. The next reviewable deliverable should be a bounded source-retrieval pilot with a locked case set, explicit non-goals, and before/after evidence.
