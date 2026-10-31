# Revised first slice: ordinary-document evidence, isolated and convention-aware

**Date:** 2026-10-31. **Author:** Codex. **Arc: none (ad-hoc).**

**State:** proposed replacement for Packet 1; not an execution plan or implementation grant. Responds to [Claude's review §5](CLAUDE-2026-10-31-convmem-general-memory-adversarial-review.md#5-revised-first-slice) and the [individual finding responses](CODEX-2026-10-31-convmem-general-memory-review-response.md). The review verdict remains `REVISE_BEFORE_PLANNING` pending reassessment. Original Packet 1 remains unchanged in the preserved research packet.

## Decision and deliverable

Determine whether a small, shared documentary path plus explicit conventions adds useful evidence access beyond plain file search. The target is `ordinary_document_v1`, a sibling scope of `repository_knowledge_v1`: manually configured local roots, UTF-8 `.md`/`.txt`, three project areas, no Git or manifest requirement, no LLM ingestion. The repository scope keeps its existing admission and authority guarantees.

At the end of a later authorized slice there would be: supported isolated documentary indexing; evidence-linked convention records; explicit document expansion with exact/drifted/unavailable states; a pool sweep and opt-in existing keyword-scan channel; and a locked 24-case mechanical evaluation with a public synthetic mirror. **None of these artifacts, fixtures or measurements is created or run by this revision.** The three project areas and one transcript area are a selection requirement, not a claim that their representative samples have already been selected or validated.

The retained broad goal includes memory for preferences, ongoing tasks, procedures and experience. This evidence slice is one enabling step; it does not define the whole product as document question-answering.

## Reuse map and bounded deltas

All source references here mean `d54f92bcd78248c8aee8a54df758564752d79aa4`.

| Packet 1 concept | Existing mechanism | Ordinary-document delta |
|---|---|---|
| Admission | `repository_knowledge_scope.py:587–643`: clean Git/manifest checks | Add sibling root/extension admission; preserve repository route precedence and checks. Parameterize eligibility and publication recheck in the shared indexer. |
| Identity and revision | `repository_knowledge_index.py:40–52`: deterministic unit IDs; file digest in provenance | Source key is canonical absolute path within admitted roots; revision is raw file SHA-256. Supply the scope plus source-revision pair as `source_identity` to the shared unit-ID machinery, alongside locator, chunk digest and adapter version. Rename creates a new source key; a changed file creates revision-distinct unit IDs. |
| Chunk/span | `adapters/repository_knowledge.py:71–163`: line windows and Markdown sections | Reuse boundaries; add raw UTF-8 line-to-byte mapping, raw span digest and file digest for this sibling scope. No assumption that normalized chunk text is raw bytes. |
| Packaging/provenance | `repository_knowledge_index.py:138–230`: direct embedding, projection and envelope | Parameterize source type, recipe, domain and source-specific provenance. Repository fields are not fabricated for ordinary files. Preserve raw bindings separately from prefixed/truncated search text. |
| Cache and idempotency | `_pending_relpaths`, sync state, `_replay_unchanged`, ingest dedupe | Namespace state by scope/root; unchanged file digest plus unchanged relevant parser/recipe/model/convention inputs skips embedding and publication. Do not copy Git-HEAD-wide invalidation into the sibling scope. |
| Change/retirement | Existing pending/indexed state and explicit retirement mechanics | Missing/unreadable sources become unavailable/unknown, never implicit retirement. Explicit exclusion is a distinct owner action. Changed-file costs are measured; section-only embedding reuse is deferred. |
| Writing | Shared production writer has explicit config/lock/attestation/census bindings | Make an isolated session/binding set a supported indexer input. No monkeypatch and no bypass of locking/publication checks. |
| Keyword candidates | `metadata_keyword_fallback.py:17–62` plus current scoring | Add an opt-in normal-path candidate union after the pool experiment; keep its existing failure fallback intact. No new lexical index. |

Existing Markdown/TXT content uses `splitlines`, joining and, for Markdown, stripping. Stored search documents have a prefix and an 8,000-character cap. The proposed raw-span binding is real new work, bounded to source evidence resolution; it does not add a second embedding pipeline or an archival blob store.

For each source key, sync state names the fully published indexed revision. Ordinary current-revision retrieval admits only units bound to that revision; prior units remain historical and require an explicit historical query. Missing sources retain their last indexed revision with unavailable/unknown source status, rather than silently deleting history. Publication failure leaves the old indexed revision selected and the new one pending; it must not expose a partial revision as current. This is indexing state, not a judgment about which real-world claim is true. Revision-distinct unit IDs prevent `_replay_unchanged` from attaching an old file-revision envelope to a new raw-span binding. No stable-across-revision unit-ID or chunk-cache guarantee is made.

## Isolation and dependencies

Future execution must start a fresh worker with `CONVMEM_CONFIG` set **before** importing ConvMem (`config.py:29–31`). Validate that Chroma, processed/sync state, exports, dedupe, locks, logs, writer attestations, census and convention sidecars all resolve beneath a fresh isolation root. Reject overlap with known production roots and symlink escapes. Input samples are authorized copies under that root; production source directories are not writable pilot inputs.

Reuse the containment patterns in `incremental_jsonl_isolation.py:79–175` and the writer arguments in `chroma_write_store.py:1096–1129`. The existing hermetic helper uses fake models and an empty Ollama host: mechanical checks may use deterministic fakes, but real retrieval observations require a separately configured, pinned local embedding model. Do not confuse fake-model CI results with semantic retrieval quality. No paid provider is needed.

The writer's resolved paths must be checked before storage opens, including defaults that the config file alone does not relocate. Any path outside the isolation root stops the run before a write. Packet 0 is not a prerequisite for isolated mechanical work; production-root additions, watchers, deployment and recovery qualification remain outside this slice and require their existing gates.

## Convention extraction and relation carrier

Parse only explicit supported forms: role/authority headers, Subject→Owner table rows and relative links, `Prepared:`, `Learned:`, dated `Correction` bullets, `Evidence:`, `Still open:`, `UNKNOWN`, `Retired`, and explicitly labelled standing rules/open items. Do not infer roles, dates, lesson outcomes, completion or ownership from prose that lacks the convention. Unknown syntax remains unparsed and counted.

Use an isolated, versioned JSONL sidecar under the ordinary-document state directory, reusing existing publication/locking boundaries where applicable. Each record carries a deterministic record ID, kind, literal value, source key, source revision, raw span binding, parser version and any unresolved target. Chroma scalar metadata holds the sidecar reference and simple selectors; it is not a list-valued relation store. Records and their source-revision binding must agree before the index reports the source as complete; interrupted or missing sidecar publication is pending/unknown, not a valid convention result.

The relation vocabulary is `supersedes`, `corrects`, `owns`, `depends-on`, `unknown`. A literal dated correction supplies correction evidence; it does not authorize mutating another claim. A missing or ambiguous target stays unresolved. Relative links resolve only within admitted roots. Ownership declarations are claims from the source, not proof of authority. Existing `relates_to`, decision suppression and ask behavior remain untouched. Application of corrections is Packet 2.

Capture an owner's content hash when a derived view is indexed. Later hash change means **heuristic stale**; no change means **unchanged since capture**; missing baseline, unknown owner or unreadable root means **unknown**. Never label this authoritative freshness at `Prepared:` time. A view may already have been stale at first capture. A `Retired` marker is extracted content, not a purge command. A standing rule is source evidence, not a newly active agent instruction.

The public mirror, when authorized, consists of **three fabricated files**: an owning record, a derived view with an owner table, and a lessons/open-items record. Their combined content exercises every supported marker and relation, including unknown/ambiguous targets; a fabricated owner revision exercises the freshness heuristic. Names, passages, links and dates are invented independently of private source details. This is a fixture specification only; no fixture is included in this branch.

## Explicit source expansion and preservation limit

Reuse existing explicit `expand` entry points and bounded output controls. For ordinary-document hits, resolve raw byte offsets against a source revision using the file and span digests. Return `exact` only when the indexed revision and requested raw span verify; do not normalize CRLF, UTF-8 or surrounding whitespace before verification. Expose range/output truncation separately from verification status. A changed file returns `drifted`; an unreadable source returns `unavailable`. Any current replacement excerpt is labelled with its own revision and never presented as indexed-original evidence.

Exactness and availability are independent of the stored search projection. The first slice does not guarantee retention of full original files or old raw spans after source changes. Retained normalized text can still be useful as a labelled projection, but cannot satisfy a raw-byte claim. There is no revision-level Restic guarantee. **F18 remains Ryan's decision:** if complete retained originals or verified snapshot references are required from the start, revise the preservation design before implementation.

Do not call expansion automatically from `ask`. Its eight-hit/12,000-character context construction, both ask prompts and the distill recipe remain unchanged. The explicit expansion call uses its own bounded return; allocating expanded context inside synthesis is later work.

## Proposed capability declaration

One declaration for `ordinary_document_v1`, using `eval_naturalistic/v2/adapters/capability.py`. These values describe the intended limited design **after verification**, not present implementation:

| Dimension | Target value | Boundary |
|---|---|---|
| occurrence_identity | `DERIVED` | Parser/path/span identities; no native occurrence identifier. |
| source_instance_binding | `DECLARED` | Configured path binding; no issuer attestation. |
| revision_asof_binding | `REVISION_PINNED` | Requires implemented raw-file digest and span binding; not historical replay. |
| evidence_completeness | `PARTIAL_KNOWN` | Selected Markdown/TXT scopes and bounded spans only. |
| canonical_verification | `UNVERIFIED` | No study canonical-payload certification; a byte hash alone does not imply it. |
| temporal_reproducibility | `MUTABLE` | Current local source may change or disappear. |
| attachment_material_span_completeness | `PARTIAL_KNOWN` | Attachments and out-of-scope linked material omitted. |
| preservation_replay_capability | `UNSEALED` | No sealed revision snapshot or replay guarantee. |
| lineage_assurance | `DECLARED` | Provenance records a claimed source binding, not independent authorship. |

Known omissions include attachments, unsupported formats, out-of-scope references, original authorship, unexpressed facts and correction application. If a required target lies in an omission, report it as unsupported/pending; retain it in the case denominator. This declaration does not qualify for the study's primary scoring or replay audit (`eval_naturalistic/v2/adapters/reduction.py:75–105`). No study profiles, schemas or sealed samples are modified.

Map the orthogonal availability axes from `eval_naturalistic/v2/evidence.py` per requested source revision:

| Observation | source_presence | verbatim_evidence_availability |
|---|---|---|
| Readable source; revision/span match | `PRESENT` | `AVAILABLE` for verified raw bytes actually returned |
| Readable source changed; old raw revision not retained | `PRESENT` | `UNAVAILABLE` for the old revision |
| File positively absent on an accessible root | `ABSENT` | `UNAVAILABLE` unless exact evidence was independently retained |
| Root disconnected, inaccessible or incompletely checked | `UNKNOWN` | `UNAVAILABLE` after a failed retrieval, otherwise `UNKNOWN` |

Summary evidence is independent: label retained extracts as such and report actual availability; use `NOT_APPLICABLE` where no summary evidence is offered. Neither an unavailable raw revision nor an unavailable summary implies that a present source is absent.

## Locked 24-case design and retrieval order

Before a future experiment, freeze corpus revision digests, question text, exact evidence targets, expected availability, query preparation, model/config identity, budgets and timing method. Keep private artifacts outside the public tree. Ryan or an independent evaluator holds **six cases**, two per group, until settings are frozen; the other 18 are development cases. No post-holdout tuning is represented as held-out performance. No sealed naturalistic-study material is selected or inspected.

| Group | Cases | Coverage required |
|---|---:|---|
| Original detail | 8 (6 development, 2 held out) | Exact terms/identifiers, literal detail, difficult location, and source-span resolution. |
| Current/history evidence | 8 (6 development, 2 held out) | Explicit owner/correction evidence, unknowns, derived-view change, and at least one late-arriving older file. These test evidence retrieval, not automated truth resolution. |
| Cross-source evidence | 8 (6 development, 2 held out) | Owner links, lesson/evidence pairs and documentary/transcript references across the selected areas. |

Use three ordinary-document areas plus one transcript area. Transcript evidence limitations are recorded, not silently fixed by this slice; unsupported targets remain visible. The three-file public mirror checks deterministic mechanics in CI without private data. It does not substitute for the private 24 cases or establish semantic recall; future reports separate public mechanical results from private retrieval counts.

Run only mechanical retrieval/evidence comparisons, in this order:

1. Current retrieval algorithm with pools **20, 50, 100** over the same eligible isolated corpus.
2. Opt-in union of vector candidates with the existing metadata keyword scan, preserving scope/tombstone filtering and deduplicating IDs before reranking. No BM25 or other new index.
3. Plain `rg`/file-open retrieval baseline over exactly the same admitted source revisions, with a frozen literal/token query procedure and bounded opens. It is a file-search baseline, not a fresh-agent continuation experiment.
4. Oracle evidence as a diagnostic ceiling only; it cannot win a retrieval comparison.

“Current” means the current retrieval algorithm on the same admitted pilot corpus, not a claim that the unmodified product can admit ordinary files. Also report current-product admission gaps separately. This prevents the comparison from crediting ranking for files one arm never received. No model-generated answers or LLM grader are used in this smaller slice. Answer quality and product value remain unmeasured.

Freeze a maximum 100 candidates entering reranking for the matched comparison. One proposed fixed union is up to 80 vector plus 20 scan candidates, deduplicated without opportunistic refill; report channel counts and all retrieval/scan work. Compare against vector-100, with the same reranker, top-eight output limit and 12,000-character evidence budget. This is a proposed evaluation setting, not a default change. Raw pre-cap union recall may also be shown, explicitly outside the matched budget. Pool 20/50/100 necessarily varies candidate work; report that cost rather than calling the arms cost-equivalent.

Report relevant-target candidate recall@effective-pool, recall in the final evidence budget, unresolved/unsupported counts and p95 retrieval latency for every arm, separately for 18 development and six held-out cases and by group. Report keyword scan corpus size and scan overhead, embedding counts, units published and dedupe counts. Pin warm/cold conditions; with only 24 observations, p95 is descriptive and near the maximum, not a stable production estimate. Timing failures and timeouts stay in the report.

If fewer than 100 eligible units exist, state the actual counts and collapsed arms. Do not enlarge the corpus with private material silently or claim that a tiny fixture settled the pool question. Golden Q02 remains a regression target; if its prerequisites are unavailable, report pending rather than claiming a pass.

The alternative's stop threshold is evidence sufficiency on at least **6/8 original-detail and 6/8 current/history cases** where file search supplies the required evidence at least as well as the best matched ConvMem arm. If met, stop expansion of generic ingestion breadth; propose convention depth and separately scoped #263 evidence work as the next decision. Do not call this product-value proof. If increased pools remove the misses, defer the keyword channel's default; if the channel adds no benefit at its measured cost, leave it off. A lexical index requires documented surviving misses and a subsequent decision.

## Acceptance observations for a later authorized implementation

| Observation | Required outcome |
|---|---|
| Same sources, config and relevant recipe/model/parser inputs rescanned | Zero embeddings and zero newly published units or duplicate convention records. |
| One paragraph appended | Correct new revision and references; actual changed-file embedding count reported. No section-only cache guarantee. |
| Rename across admitted roots | New path/source identity; old reference remains historical and becomes unavailable when unresolved. No inferred retirement or continuity. |
| Exact, edited and disconnected source cases | Exact raw byte match, honest drift, or unavailable respectively; disconnect produces zero tombstones. Include CRLF/UTF-8/whitespace and bounded-output cases. |
| Explicit relation/marker extraction | Public synthetic expected owners, corrections, lessons, open items and unknowns match; each relation has evidence or unresolved status. No correction application. |
| Owner changed/unchanged/unknown | Heuristic stale / unchanged since capture / unknown; no invented freshness at preparation date. |
| Isolation | Every effective writable path contained; attempted production overlap rejected before opening storage. No production writes. |
| Ask/regression compatibility | Prompt hashes, context size and excerpt count unchanged on three characterization cases; existing characterization/golden fixtures unchanged. Run only inspected, isolated tests after authorization. |
| Retrieval comparison | All 24 cases accounted for with held-out and development results separate, effective pools, candidate/final recall and p95 latency; no default changed from an oracle or unsupported result. |

These are future acceptance requirements, not assertions that tests passed. At design completion, the sample lock, fixture, runner and supported isolation interface still require separate authorization and implementation.

## Explicit exclusions and next decision

Excluded: E4 and all continuation/product-value experiments; all ask/distill prompt rewrites; automatic source expansion in synthesis; a new lexical index; a parallel documentary pipeline; a chunk embedding cache; stable rename identities; full-file archival/snapshot guarantees; generalized LLM convention extraction; correction application; new first-class task/preference lifecycle; PDF/OCR/Thai-tokenizer/table/media support; graph/database replacement; watcher/production changes; Switchboard implementation.

F17–F19 remain recorded for Ryan in the response. The three material scope reductions from review §5 are no prompt-framing change, no identity-preserving rename claim, and no section-only embedding-cache claim. Raw span mapping and conservative freshness labels correct evidence assumptions rather than conceal additional work. If F18 requires retained originals, or F19 changes client priority, revise this document before promoting it to a bounded implementation plan.

**Next lane:** Ryan for those decisions and revised-slice review. No new arc, implementation, fixtures, runtime, corpus writes, paid calls or PR are authorized by this document.
