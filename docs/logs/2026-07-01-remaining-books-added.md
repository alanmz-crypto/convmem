# 2026-07-01 — Remaining 5 books added to builder-reference

## Summary

Added builder-reference digests for all 5 unused books from the ~/Documents/Computing/Projects/Convmem/ source folders:

| Book | File | Words | Convmem value |
|------|------|-------|---------------|
| Designing Data-Intensive Applications | ddia-builder-digest.md | 1230 | Ledger as system of record, Chroma as derived data, watch daemon as stream processor, transaction design, consensus across surfaces |
| How to Take Smart Notes | smart-notes-builder-digest.md | 987 | Zettelkasten → ledger mapping, atomicity, linking discipline, bottom-up organization |
| Architecture Patterns with Python | arch-patterns-python-builder-digest.md | 1009 | Repository pattern (ChromaStore), Unit of Work (approve pipeline), aggregates (decision clusters), event-driven watch/refine |
| The Pragmatic Programmer | pragmatic-programmer-builder-digest.md | 945 | DRY across protocol surfaces, orthogonality, tracer bullet approach, Design by Contract |
| Building a Second Brain | second-brain-builder-digest.md | 870 | CODE → convmem pipeline mapping, PARA organization, progressive summarization, brief as daily review |

## What was added

- 5 new digest files in `docs/builder-reference/`
- `README.md` index updated with all 9 books and read-when-touching guidance
- `SOURCES.md` updated with all source paths and page ranges
- Each digest includes: principles, convmem-specific mapping, convmem Hooks, anti-patterns, cross-references to related digests

## Source used

- DDIA: `annas-arch-a4d0064a0249.pdf` (585pp)
- Pragmatic Programmer: `ThePragmaticProgrammer.pdf` (497pp)
- Architecture Patterns with Python: `ArchitecturePatternswithPythonforbuildingandSoftwareArchitectureTheHardParts.pdf` (475pp)
- How to Take Smart Notes: `annas-arch-5bcb8f950533.pdf` (180pp)
- Building a Second Brain: `annas-arch-eaa2571df81d.pdf` (231pp)

## Verification

- `bash scripts/deploy-builder-reference.sh` — PASS (5 warnings: word count below 1500 target for new digests)
- `bash scripts/verify-builder-reference.sh` — PASS
- Crush copies: 4 existing digests deployed. New 5 are repo-only (not added to Crush global_context_paths — would add ~5k tokens)

## Notes

- All 9 books from the source folders are now in the builder-reference system:
  - 4 original (Ousterhout, Manning, Zeller, Hard Parts) — expanded with missing chapters this session
  - 5 new (DDIA, Pragmatic Programmer, Arch Patterns Python, Smart Notes, Second Brain)
- The new digests are intentionally thinner (~900-1200 words vs 1500+ target) — they cover broader, less convmem-specific topics. DDIA is the most actionable addition.
- If Crush should load these too, the deploy script needs updating to include the additional Crush copies.
