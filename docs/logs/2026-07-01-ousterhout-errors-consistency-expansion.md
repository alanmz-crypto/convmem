# 2026-07-01 — Ousterhout Ch10 and Ch17 expansion

## Summary

Expanded the Ousterhout builder digest with Chapter 10 (Define Errors Out Of Existence, pp. 95–109) and Chapter 17 (Consistency, pp. 164–168). The existing digest covered Chapters 4–9 (complexity, deep modules, information hiding) but skipped both of these directly applicable chapters.

## What was added

**Chapter 10 — Define Errors Out Of Existence:**
- 3 new principles: exception handling as complexity source, aggregate exception handling, crashing as valid design
- `ask()` timeout/fallback analysis mapping the three strategies from the chapter (throw the error, define it away via masking, promote and reuse as in RAMCloud example)
- Expanded the `mcp_server.py` section to cite Ch. 10 explicitly and add the exception aggregation pattern
- 1 new anti-pattern: silent fallback without degradation observability

**Chapter 17 — Consistency:**
- 4 new principles: cognitive leverage, three enforcement tiers, don't change existing conventions
- Expanded the Protocol Generation section to cite Ch. 17 explicitly — the generator enforces consistency across 5 surfaces by making drift structurally impossible
- 2 new anti-patterns: hand-editing generated files, adding second expression paths across surfaces

## Source extracted

- `/home/lauer/Documents/Computing/Projects/Convmem/SuggestedBooksClaude/APhilosiphyOfSoftwareDesign.pdf` pages 95–109 (Ch10) and 164–168 (Ch17)
- Ch10 sections: exception handling complexity, defining errors away (Tcl unset, Windows file delete, Java substring), exception masking, aggregation patterns, RAMCloud promote-and-reuse
- Ch17 sections: consistency as cognitive leverage, enforcement tiers (documentation → automated checkers → design), don't change existing conventions

## Verification

- `bash scripts/deploy-builder-reference.sh` — PASS
- `bash scripts/verify-builder-reference.sh` — PASS (sha256 match, all 4 Crush copies)
- `SOURCES.md` updated with new page range (pp. 34-92, 95-109, 164-168)
- Word count: 2965 (was 2355)

## Notes

- Ch. 10 maps to the partial-synthesis-vs-raw-fallback question that came up during the session review. The three strategies (throw, mask, promote-and-reuse) give the precise vocabulary for that trade-off.
- Ch. 17 maps directly to the protocol generation SSoT work — the generator is the enforcement tier that makes surface drift structurally impossible.
