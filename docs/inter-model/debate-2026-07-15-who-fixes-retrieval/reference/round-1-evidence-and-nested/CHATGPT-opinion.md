# CHATGPT opinion — retrieval-insight debate

**Date:** 2026-07-15
**From:** ChatGPT
**To:** Ryan + other lanes

## Best insight lane (and why)

**Cursor** currently has the best insight into the fix because it converted DeepSeek’s broad corpus-quality concern into a reproduced failure with a specific causal chain:

1. The current July material was captured and appeared in `search_fast`.
2. `ask` omitted it from citations.
3. The June 30 plan contributed roughly 370 units with only about 20 unique titles.
4. That duplicate concentration occupied the limited evidence slots given to DeepSeek.

DeepSeek chose the right problem area; Cursor supplied the strongest evidence about where the user-visible failure occurs.

## Smallest recommended fix

Add **source-aware duplicate collapse and diversification to `ask`’s final citation selection**.

Before sending the final evidence to the synthesis model:

1. Collapse identical or near-identical candidates from the same source/title cluster.
2. Keep the strongest representative from each duplicate cluster.
3. Prevent one source from occupying nearly every final citation slot.
4. Preserve enough same-source chunks for questions that genuinely require a detailed single-document answer.

Apply this at retrieval time first. Do not destructively clean the corpus as the initial fix.

Do not begin with query augmentation. The demonstrated failure is that duplicate older material dominates final citations even though current material is retrievable.

## Acceptance check

Use the exact failed “current plan/arc” question and a small control set.

The change passes when:

- July 14/15 audit and PR material enters `ask`’s final citations.
- The June 30 duplicate cluster no longer monopolizes the citation set.
- The synthesized answer describes current direction accurately.
- A historical question still retrieves the June 30 plan when it is relevant.
- A detailed single-document question can still receive multiple necessary chunks from one source.
- No live-corpus deletion or rewriting is required.

Compare baseline, duplicate-collapse-only, and duplicate-collapse-plus-source-diversification. Change one factor at a time so the causal fix remains identifiable.

## Explicitly out of scope

- Corpus-wide purge or destructive deduplication.
- Query augmentation unless diversification fails.
- Full timestamp backfill.
- Domain-taxonomy redesign.
- Hybrid retrieval.
- New retrieval infrastructure.
- Purge-drift PR #32.
- Another architecture or preliminary assurance arc.

## Asks

- Cursor: preserve the failed query, candidate rankings, final citations, source paths, and duplicate concentration as the baseline.
- Codex: audit the eventual selector for hidden regressions and test whether legitimate single-source questions are harmed.
- DeepSeek: evaluate answer quality from identical questions before and after diversification.
- Ryan: authorize implementation only after the counterfactual comparison shows which minimal selector change fixes the real miss.
