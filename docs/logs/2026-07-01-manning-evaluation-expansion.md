# 2026-07-01 — Manning evaluation chapter expansion

## Summary

Expanded the Manning IR builder digest with Chapter 8: Evaluation in Information Retrieval (pp. 163–184). The existing digest only covered Chapters 6–7 (scoring, term weighting, vector space model, pp. 100–161), and the header incorrectly claimed it already included Chapter 8.

This gap mattered because this session built a PASS/PARTIAL/FAIL grader for Continue sessions — an evaluation-design problem. The formal vocabulary for test collections, precision/recall/F-measure, MAP, NDCG, kappa inter-judger agreement, and the prohibition on tuning on your test set was sitting unused.

## What was added

- Fixed digest header to accurately reflect coverage (Chs 6–7 + Ch 8, not "Chs 6 and 8")
- New **Evaluation methodology** section with subsections:
  - Test collections (corpus + queries + relevance judgments; tuning prohibition)
  - Set retrieval evaluation (precision, recall, F-measure; mapping to grader trade-offs)
  - Ranked retrieval evaluation (P@k, MAP, NDCG; mapping to golden-query P@5 and grader rubric)
  - Assessing relevance (kappa statistic; mapping to cross-agent grader consistency)
  - Marginal relevance and snippets (mapping to build_context)
  - Broader metrics (system effectiveness vs user utility)
- Updated convmem Hooks with evaluation design hook
- 3 new anti-patterns (tuning on test set, grading without test collection/metric/kappa, confusing P@k with MAP/NDCG)

## Source extracted

- `/home/lauer/Documents/Computing/Projects/Convmem/SuggestedBooksChatGPT/An introduction to information retrieval....pdf` pages 163–184
- All 8 sections of Chapter 8: test collections through snippets and references

## Verification

- `bash scripts/deploy-builder-reference.sh` — PASS
- `bash scripts/verify-builder-reference.sh` — PASS (sha256 match, 4 Crush copies)
- `bash scripts/validate-builder-reference-surfaces.sh` — PASS
- `SOURCES.md` updated with new page range (pp. 100-161, 163-184)

## Notes

- The original digest header claimed "Chapters 6 and 8, pp. 100-161" but Chapter 8 starts at p. 163 — the header was wrong for the entire lifetime of the digest. Fixed both the header and added the actual content.
