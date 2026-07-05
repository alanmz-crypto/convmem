# Manning - builder digest (convmem)

**Source:** *Introduction to Information Retrieval* · Chapters 6 and 7 (scoring,
term weighting, vector space model), pp. 100-161; Chapter 8 (Evaluation in
Information Retrieval), pp. 163-184

**Read when:** changing retrieval ranking, chunk sizing, reranking, evaluation,
golden-query workflows, evaluation design (graders, scoring rubrics,
pass/fail criteria), or anything that decides what context gets shown to an
LLM before it answers.

## Principles

- Retrieval is a pipeline, not a single operation. Tokenization, indexing,
  scoring, ranking, and evaluation all matter.
- Term statistics matter. The same document can score differently depending on
  how terms are weighted and how the query is interpreted.
- Ranking is the real product, not just matching. A retrieval system is useful
  when it consistently surfaces the best few candidates.
- Efficiency and quality are linked. A clean retrieval design makes it possible
  to search more data without turning the system into a latency problem.
- Evaluation is not optional. If the ranking changes, measure the effect
  against fixed queries or you will fool yourself.
- Relevance is contextual. A result can be “correct” in an abstract sense and
  still be wrong for the user’s actual task.
- Small representation choices can shift ranking quality. Chunking, overlap,
  normalization, and field selection are not details.
- There is no substitute for a good test collection. You need repeatable
  queries with expected hits if you want to compare retrieval changes honestly.
- Retrieval and generation should stay separate. The search layer should decide
  what evidence is relevant; the generator should decide how to phrase the
  answer from that evidence.

## What this means for convmem

- The goal is not “find anything that looks related.” The goal is “return the
  best evidence for the task the agent is actually trying to complete.”
- If chunking changes, the retrieval result distribution changes. That means
  chunking is an evaluation concern, not just an ingestion concern.
- If ranking changes, the agent’s behavior changes. That means ranking changes
  should be reviewed the way behavior-affecting code changes are reviewed.
- If the retrieval layer returns good evidence but the prompt builder buries it,
  the problem is in orchestration, not search.
- If the retrieval layer returns bad evidence, a longer prompt usually makes it
  worse, not better.

## Retrieval pipeline guidance

- Use term weighting, metadata filtering, and reranking as separate stages so
  each can be reasoned about independently.
- Keep a stable evaluation set for the repo. In practice that means a handful
  of repeatable questions that represent the actual tasks the agents do.
- Measure top-k quality, not just exact match.
- When possible, compare candidate retrieval strategies against the same query
  set and note both improvements and regressions.
- Chunk overlap should be enough to preserve continuity, but not so large that
  it floods the index with near-duplicates.
- Page metadata is valuable because it lets you trace the retrieved passage back
  to source material when you need citations or a manual audit.

## Ranking and evaluation

- A ranking score is an estimate, not a truth claim.
- Similarity search should be treated as a first pass. If the domain needs it,
  rerank the candidates with a more task-specific signal.
- If you care about the freshness of evidence, recency should be a deliberate
  signal rather than an accidental side effect.
- If you care about correctness, build evaluation around known answers and not
  just “looks about right.”
- If a query is ambiguous, the system should still make the ambiguity visible in
  the retrieved evidence instead of hiding it behind a plausible-looking answer.

## Convmem implementation notes

- `recency_weight` is a useful dial when the corpus contains both evergreen
  principles and fast-changing operational notes.
- `rerank` is worth keeping as a separate stage because it lets the system
  preserve a broad candidate set before applying more specific preferences.
- `chunk_size` should be chosen with page boundaries and evaluation in mind.
  The best chunk size is the one that preserves enough local context to make the
  evidence usable without losing too much recall.
- `golden-query` evaluation should cover at least: architecture question,
  debugging question, retrieval question, and a cross-surface “where should I
  change this?” question.
- When the agent asks for a “read when touching X” result, the retrieval layer
  should surface the builder-reference digest before it surfaces generic docs.

## Useful distinctions

- Exact term match helps when the task is anchored in a named function or
  identifier.
- Semantic retrieval helps when the task is expressed in user language rather
  than code language.
- Metadata filtering helps when the corpus is large enough that the right
  answer exists but is buried under unrelated material.
- Reranking helps when the first pass is broad and the final decision needs
  sharper discrimination.
- Evaluation helps when humans start trusting anecdotal wins more than measured
  behavior.

## convmem Hooks

- `recency_weight` is a ranking knob, not a truth source. Treat it like a term
  weighting parameter.
- `rerank` is the second-stage scoring layer. If it changes, measure impact on a
  fixed query set rather than trusting intuition.
- `chunk_size` and overlap affect recall and precision the same way document
  segmentation affects IR systems. Too small fragments dilute meaning; too
  large fragments bury the relevant signal.
- Golden queries are the right evaluation unit for this repo. A builder
  reference should help the agent answer “what should I touch?” with fewer
  guesses and better citations.
- Chroma similarity search is the retrieval primitive. Everything after that is
  policy and formatting.
- If a retrieval change improves one query and degrades another, that is
  normal. The point is to choose the tradeoff intentionally.
- Builder-reference digests are part of retrieval quality because they shape the
  question that the agent asks before it edits code.
- **Evaluation design is an IR problem.** When building a grader (PASS/PARTIAL/
  FAIL), treat it as an evaluation methodology question: define your test
  collection, choose your metric (P@k, MAP, or NDCG), measure inter-judge
  agreement (kappa), and avoid tuning on your test set.

## Anti-patterns for Agents

- Do not tune ranking and chunking at the same time without an evaluation pass.
- Do not assume keyword overlap is enough. Semantic similarity and exact-term
  retrieval solve different problems.
- Do not ship a new retrieval strategy without a stable query set.
- Do not confuse “top-k returned something plausible” with actual quality.
- Do not let the answer generator compensate for bad retrieval with more prompt
  text. Fix the retrieval first.
- Do not assume the same chunking and ranking settings should serve both code
  navigation and documentation guidance.
- Do not tune ranking parameters on the same queries you report results on.
  Hold out a validation set (Ch. 8, p. 165).
- Do not build a grader (PASS/PARTIAL/FAIL) without first defining your test
  collection, choosing a metric, and checking inter-judge agreement. A grader
  with no kappa check is an opinion, not an evaluation.
- Do not confuse P@k with MAP or NDCG. P@k is intuitive but ignores rank
  position within the top k. MAP and NDCG are more sensitive to ordering.
  Choose the metric that matches your task: if only top-1 matters, use P@1;
  if ranking quality across positions matters, use MAP or NDCG.

## Ranker stack in convmem (concrete)

When `ask()` runs with `evidence=True` (default for MCP), retrieval is not one
score — it is a pipeline:

```text
query text
  → ollama_embed (nomic-embed-text)
  → Chroma query_units (top_k_candidates, default 20)
  → optional domain/site filter
  → apply_evidence_rerank (evidence.py)
       · ledger graph boosts (unresolved +0.18, failed verification +0.14, …)
       · recency_weight time-decay (config query.recency_weight, half-life days)
  → dedupe by ledger_id
  → _filter_superseded_decisions
  → top_k to LLM context (_ASK_TOP_K = 8)
  → synthesis (llama3.1:8b or configured model)
```

Files to touch when tuning ranking — not prompts first:

| Knob | File | Config key |
|------|------|------------|
| Candidate pool size | [`query.py`](../../query.py), [`chroma_store.py`](../../chroma_store.py) | `query.top_k_candidates` |
| Final result count | [`query.py`](../../query.py) | `query.top_k_results` |
| Rerank on/off | [`config.example.toml`](../../config.example.toml) | `query.rerank` |
| Recency boost | [`evidence.py`](../../evidence.py) | `query.recency_weight`, `recency_half_life_days` |
| Evidence boosts | [`evidence.py`](../../evidence.py) | constants `_BOOST_*` |
| Chunk segmentation | ingest + [`config.example.toml`](../../config.example.toml) | `index.chunk_size`, `chunk_overlap` |

Semantic similarity is pass one. Policy (evidence graph, recency, superseded
decisions) is pass two. Treat them separately when debugging.

## Golden-query evaluation set (starter)

Use a fixed set before changing ranking. Expected ids are coordination-lane
examples from the live ledger — update when decisions supersede.

| Query | Expected top hit (ledger id) | Tests |
|-------|------------------------------|-------|
| "Global convmem protocol soak close" | `dec_prop_20260629_150527_46f0` | recency + coordination |
| "Arch Linux health prompt matrix" | `dec_prop_20260629_150516_6d70` | cross-surface deploy |
| "Continue alien workspace convmem fail" | `dec_prop_20260625_223006_528c` | alien cwd behavior |
| "Crush Tier A shell slice deploy" | `dec_prop_20260625_233830_b9af` | Crush-specific |
| "convmem protocol root fallback relates-to" | `dec_prop_20260623_161428_c311` | stable anchor — **lookup injection** when semantic miss (2026-07-05) |

Measure **P@5**: did the expected id appear in the top five `query_units`
results? If ask synthesis cites an older id while a newer decision exists in
`approved_decisions.jsonl`, that is a retrieval/recency failure — not an LLM
failure.

Script target: `scripts/eval-retrieval.py` (future) or manual
`convmem search "query"` after each ranking change.

## Recency gap case study (digest pilot)

[`docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md`](../../docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md)
Run 4 documented a split:

- **Digest header** listed Jul 2026 v4/org decisions (`dec_prop_20260701_*`).
- **Embedded `ask` synthesis** still anchored on Jun 25–29 ids (`dec_prop_20260625_203408_f9b3`, `dec_prop_20260629_054023_84ac`).

IR diagnosis:

1. `cross_project_digest.py` already calls `load_recent_decisions()` for the
   markdown header — authoritative fresh context exists.
2. `ask()` retrieval is purely semantic + evidence rerank — it does not inject
   recent approved decisions as forced excerpts.
3. Raising `recency_weight` alone may not surface a specific new decision if
   semantic similarity to the question is low.

Fix class: **query augmentation** (prepend recent decisions to context), not
prompt engineering. That is standard IR practice: pseudo-relevance feedback /
mandatory metadata fields for "state of the project" questions.

## Hybrid retrieval note

[`ask.py`](../../ask.py) can supplement weak unit hits with `query_raw`
summaries when confidence < `_LOW_CONFIDENCE` (0.55). That is a hybrid
fallback — useful when distillation lags, dangerous if it masks a broken
units index. When evaluating ranking changes, test with `--raw off` first.

## Builder-reference as retrieval policy

When an agent asks "what should I read before editing ask.py?", retrieval should
rank `manning-builder-digest.md` above generic handoff markdown. Surface rules
(Cursor `globs: **/Projects/convmem/**`) handle load; search ranking handles
in-session `search_fast` — keep both aligned.

## `search_fast` vs `ask` vs `query_units`

| Entry | File | LLM? | Use when |
|-------|------|------|----------|
| `search_fast` / `convmem search` | [`query.py`](../../query.py) | No | Fast citation lookup; **recency_boost** when `query.recency_weight` > 0 |
| `query_units` | [`query.py`](../../query.py) | No | Programmatic ranking inspection |
| `convmem ask` / MCP `ask` | [`ask.py`](../../ask.py) | Yes | Synthesized answer with citations |
| `query_raw` | [`query.py`](../../query.py) | No | Legacy summaries fallback (`--raw`) |

Tuning ranking: use `convmem search "query"` and inspect scores (`rank_score`,
`recency_boost` in MCP JSON) before touching `ASK_PROMPT`. If search is wrong,
synthesis cannot recover.

MCP `search_fast` should stay read-only and fast — do not add synthesis there;
that duplicates `ask` and breaks timeout budgets (Crush 120s).

## Evidence boost constants (reference)

From [`evidence.py`](../../evidence.py) — treat as tunable IR features, not magic:

| Signal | Adjustment | Label |
|--------|------------|-------|
| Unresolved observation | +0.18 | `unresolved` |
| Failed verification | +0.14 | `failed_verification` |
| Failed check | +0.14 | `failed_check` |
| Passed verification | −0.08 | `passed_verification` |
| Resolved | −0.10 | `resolved` |
| Decision unit | +0.02 | `decision` |

`rank_score = base_score + evidence_boost + recency_boost`. Log all three when
debugging a miss — the semantic score alone misleads.

## Recency decay formula

`recency_boost = recency_weight * exp(-age_days / half_life_days)` using metadata
timestamp ([`evidence.py`](../../evidence.py) `recency_boost()`). Default in
[`config.example.toml`](../../config.example.toml): `recency_weight = 0.1`,
half-life 30 days.

This is a **mild** prior — it will not override a strong semantic mismatch.
State-of-project questions need forced recent-decision context (see digest pilot).

## Superseded decisions in `ask.py`

`_filter_superseded_decisions` removes parent decisions when a child
`relates_to` points at them. IR view: duplicate/near-duplicate suppression in
the ranked list before context assembly.

If ask cites a superseded parent, check whether the child decision is in the
index and whether filter ran after rerank.

## Distillation and primary search

Units layer is primary; raw summaries are fallback when unit confidence is low.
Backfill path: `rm processed.json && convmem index` (see `convmem stats`
warning). Evaluating ranking on an empty units layer tests the wrong system.

[`distill.py`](../../distill.py) produces knowledge units from chunks — chunk
boundaries affect which terms appear in unit `document` fields and therefore
embedding geometry.

## Proposed fix pattern: recent-decision injection

When implementing recency-gap fix:

1. Extract `load_recent_decisions()` from [`cross_project_digest.py`](../../cross_project_digest.py)
   to a shared module (e.g. `ledger_recent.py`).
2. In `ask()`, detect coordination/state questions OR always prepend N recent
   decisions as non-semantic context blocks (formatted like search hits).
3. Add golden-query row: "v4 repo organization shipped" → `dec_prop_20260701_000837_8ab4`.
4. Re-run digest pilot ask block — header and synthesis should cite same id band.

Do not only increase `recency_weight` — measure P@5 first.

## `tests/test_evidence_rerank.py` as eval seed

Existing tests call `apply_evidence_rerank` with fixture metadata. Extend with:

- recency_weight > 0 shifts newer fixture ahead
- unresolved boost beats resolved penalty on equal semantic score

That is unit-level IR eval before CLI golden queries.

## Chunk size worked example

`chunk_size = 60`, `chunk_overlap = 10` in config — conversation adapters slice
messages into embeddable segments. Too small: ledger ids split across chunks,
hurting exact-id recall. Too large: one chunk dominates top-k for broad queries.

When changing chunk_size, re-index a **single** adapter source with `--file`
and `--force` before full corpus reindex — controlled experiment (Zeller
minimize principle applies to index experiments too).

## Manual eval commands

```bash
convmem doctor
convmem search "Crush Tier A shell slice deploy"
convmem search "cross-project digest recency gap"
# Inspect ledger_id in top results before changing evidence.py constants
```

Record baseline P@5 in a scratch file when tuning — Manning Ch. 8 discipline.

## Scenario: tuning `recency_weight` safely

1. Baseline: `convmem search` on five golden queries; save top-5 ids + scores.
2. Change `recency_weight` 0.1 → 0.2 in `~/.config/convmem/config.toml` only.
3. Re-run search — expect **some** ids to move, not all queries to change.
4. If coordination query still misses Jul 2026 id, recency alone is insufficient
   — implement forced recent-decision context in `ask.py`.
5. Revert config if P@5 regresses on evergreen queries (e.g. fallback root id).

Never tune `recency_weight` and `chunk_size` in the same commit.

## `domain` and `site` filters

`query_units(..., domain=..., site=...)` in [`query.py`](../../query.py) scopes
hits before rerank. Client work: pass `site=staging2.willowyhollow.com`.
Coordination: omit site; use domain prefixes in search text instead of
filtering to `general` only.

Wrong: broad semantic search on client question without `--site` — retrieves
unrelated project noise, looks like "bad ranking."

## Rerank model stage

When `query.rerank = true`, [`query.py`](../../query.py) may invoke cross-encoder
rerank ([`rerank.py`](../../rerank.py)) after candidate fetch. Three-stage mental
model:

1. Embed similarity (cheap, broad)
2. Cross-encoder rerank (expensive, sharper)
3. Evidence + recency policy (domain-specific)

Disable rerank temporarily to isolate stage-1 regressions — do not disable
evidence and rerank together.

## Brief staleness vs retrieval

[`brief.py`](../../brief.py) `_handoff_staleness` compares `LATEST.md` mtime to
newest inbox file — operational signal, not Chroma. An agent can have **fresh
brief** but **stale ask citations** if retrieval lacks recent decisions. Treat
these as independent subsystems in eval.

## Index inventory vs search quality

`inventory.jsonl` and `convmem stats` show source coverage; they do not replace
golden-query eval. A fully indexed corpus can still rank wrong id first if boosts
are miscalibrated.

## Future `eval-retrieval.py` shape

```text
golden_queries.jsonl  # query, expected_ledger_id, optional domain/site
→ query_units per row
→ report P@1, P@5, MRR
→ exit 1 on regression vs committed baseline
```

Start with five coordination queries from golden table above; expand when
touching `evidence.py` constants.
