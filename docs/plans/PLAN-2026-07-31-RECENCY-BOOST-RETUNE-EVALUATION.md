# Recency-boost retune: execution-ready evaluation protocol

**Status:** design draft only. This protocol authorizes no config, register,
census, Shadow, Chroma, service, ledger, or deployment change. Execution is
deferred until after the deployed checkout freeze and requires Ryan's approval.
**Branch PR title:** docs: freeze-safe analysis plans for C6 hold, standing checks, and retrieval gaps

**Draft source:** Kiro design-review lane, used as a fallback after two empty
DeepSeek responses. The deployed checkout remains at
`76126e07a97187f68d925dd8b431d2d03967084f` through 2026-08-07 00:00 UTC.

## Evaluation boundary

### Read-only evidence recheck — 2026-07-31

Corpus search recovered Ryan's approved decision
`dec_prop_20260705_182232_2d24` in
`/home/lauer/.local/share/convmem/decisions-approved.jsonl` (rechecked
2026-07-31; timestamp `2026-07-05T18:22:32Z`). Its rationale records
that Manning P1a wired `recency_boost` through `query_units` and that the
retrieval evaluation had no regression. The broader parent roadmap decision
`dec_prop_20260629_212545_8aae` is not the specific no-regression evidence.
This historical record supports implementation history but does not replace
the held-out post-freeze retune evaluation or authorize a new weight.

**Retrospective plan-authorship snapshot (read-only, 2026-07-31 08:42 UTC):**
A read-only `convmem doctor` run recorded 12,452 active knowledge units at
plan-authorship time. The trigger condition `12,452 > 5714 × 2.0 = 11,428`
was met at that reading. This figure is historical plan-authorship evidence
only; it does not constitute a tuning result, does not reset the standing-check
register row, and does not authorize any config, register, census, Shadow,
Chroma, service, ledger, or deployment action. Execution remains deferred
until after the 2026-08-07 00:00 UTC freeze and requires Ryan's explicit
approval.

Capture one read-only corpus snapshot before scoring:

- active unit and summary counts;
- deployed revision SHA and active corpus/Chroma-root identity;
- current recency weight and half-life, read without editing them.

Do not reindex, rechunk, re-embed, register a collection, or alter the live
configuration. Run the comparison in a separate harness against the same
snapshot and candidate pool. Candidate values are selected before scoring and
are not tuned from individual query results.

## Sealed golden set

Build and hash a held-out set before any candidate is scored. The minimum set
is 15 queries:

| Slice | Minimum | Purpose |
|---|---:|---|
| Durable architecture | 4 | Protect decisions and stable design guidance. |
| Recent operational debugging | 4 | Test useful freshness. |
| Cross-surface navigation | 3 | Test retrieval across plans, code, and handoffs. |
| Corpus health/synthesis | 2 | Test standing-check and synthesis evidence. |
| Regression anchors | 2 | Preserve known retrieval behavior. |

Queries must come from existing tests or a separately authored review set.
Annotate relevance with the current query text and candidate-independent
review, then seal the query IDs, relevance labels, and source provenance
before scoring. Relevance labels must be authored or independently verified by
a reviewer who has not seen the candidate weights. Do not add queries after
seeing results.

## Required displacement pairs

For every candidate, record ranks and scores for these authoritative-versus-
chat comparisons:

| Pair | Durable/authoritative item | Freshness competitor |
|---|---|---|
| D1 | Architecture decision (`dec_prop_*` or `obs_*`) | Recent session artifact (`sess_*`) |
| D2 | Safety-boundary decision | Recent chat discussion |
| D3 | Standing-check plan or decision | Doctor/brief session chunk |
| D4 | Canonical CLI/API builder or plan | Recent session example |
| D5 | Escalation rationale decision or plan | Recent failure summary |

An inversion is a blocking review item when the authoritative durable unit
falls below the newer, less authoritative chat artifact in the top three.
Every inversion needs a written disposition; no candidate is accepted with an
unexplained inversion.

## Metrics and comparison matrix

Score the current behavior and at least two meaningfully different candidate
weight/half-life pairs against the identical sealed set. Report:

- P@5 = relevant results in the first five divided by five;
- NDCG@5 using graded relevance 0–3, with a binary fallback only if the set
  cannot support graded labels;
- means for all queries, durable queries, and operational queries;
- D1–D5 inversion count and a complete regression list.

A candidate is rejected when more than 20% of golden queries regress, or when
the corpus snapshot, deployed revision, or golden-set hash differs between
comparison rows.

## Reproducible result artifact

The private evaluation result should use schema `recency-retune-eval-v1` and
include these fields:

```json
{
  "schema": "recency-retune-eval-v1",
  "run_id": "",
  "measured_at_utc": "",
  "scoring_reference_utc": "",
  "collection_count": 0,
  "summary_count": 0,
  "deployed_revision": "",
  "corpus_root_identity": "",
  "golden_set_sha256": "",
  "query_count": 0,
  "annotations_sealed": true,
  "config_label": "baseline-or-candidate",
  "recency_weight": 0.0,
  "half_life": 0.0,
  "p_at_5_all": 0.0,
  "p_at_5_durable": 0.0,
  "p_at_5_operational": 0.0,
  "ndcg_at_5_all": 0.0,
  "ndcg_at_5_durable": 0.0,
  "ndcg_at_5_operational": 0.0,
  "inversion_count": 0,
  "regression_count": 0,
  "evaluator": ""
}
```

Record `scoring_reference_utc` and use that identical fixed timestamp as the
recency clock for every baseline and candidate run in the same comparison
matrix. `measured_at_utc` records capture time; it must not substitute for the
shared scoring reference.

Do not put query text, unit content, or payload-bearing metadata in a
shareable report. Query IDs and aggregate metrics are sufficient for review;
the private working set must remain access-controlled.

## Acceptance and reset rules

Accept a candidate only when all of these hold:

1. Mean P@5 does not decline, or any decline is at most 0.02 and is explained
   by the durable slice without an operational regression.
2. Durable NDCG@5 is no more than 0.01 below baseline.
3. Operational NDCG@5 improves over baseline.
4. D1–D5 have zero unexplained blocking inversions.
5. Regressions are below 20% and every regression has a disposition.
6. Relevance labels are authored or independently verified by a reviewer who
   has not seen candidate weights before labeling.
7. The rationale is written before any separately authorized config change.
8. Ryan explicitly approves the candidate and the subsequent operation.

After an authorized implementation, repeat the fixed evaluation and record a
new `collection_count` baseline. Never reset the standing check by changing
only `last_verified`, by partially scoring the set, or after a rejected
candidate. This protocol does not close the standing-check register row.

**Verdict:** RECENCY RETUNE EVALUATION READY FOR POST-FREEZE REVIEW — no
runtime or register action is authorized by this document.
