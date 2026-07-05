# 2026-07-01 — Hard Parts saga expansion

## Summary

Expanded the Software Architecture: The Hard Parts builder digest with Chapters 9, 11, and 12 (pp. 249–364), covering data ownership, distributed workflows, and transactional sagas. The existing digest only covered pp. 20–95 (Part I fundamentals), missing the chapters that directly map to convmem's propose_decision → Kiro sign-off → record --approve-last pipeline — which is a distributed saga spanning multiple agent surfaces.

## What was added

- 5 new principles (sagas, three coupling forces, orchestration vs choreography, compensating transaction failure modes, weakest-saga rule)
- 8-pattern saga reference table (Epic through Anthology) with convmem default mapping
- Saga state machines section — connecting book's state machine pattern to convmem's existing ledger status model
- Decision pipeline saga analysis — failure mode table with 5 identified gaps (partial writes, missing compensating actions, no timeout nag, no retry, side-effect hazards)
- Target pattern recommendation: Fairy Tale(seo) over Epic(sao) for the decision pipeline
- 3 new anti-patterns, updated hooks, and updated cross-surface workflow guidance

## Source extracted

- `/home/lauer/Documents/Computing/Projects/Convmem/SuggestedBooksClaude/SoftwareArchitectureTheHardParts.pdf` pages 249–364
- Chapters 9 (Data Ownership and Distributed Transactions), 11 (Managing Distributed Workflows), 12 (Transactional Sagas)
- Includes all 8 saga pattern variants, saga state machines, compensating transaction techniques, and the Sysops Squad saga worked example

## Verification

- `bash scripts/deploy-builder-reference.sh` — PASS
- `bash scripts/verify-builder-reference.sh` — PASS (sha256 match, all 4 Crush copies)
- `bash scripts/validate-builder-reference-surfaces.sh` — PASS
- `SOURCES.md` updated with new page range (pp. 20–95, 249–364)

## Notes

- The saga chapters were the highest-value gap in the digest set: the decision pipeline is the one part of convmem that genuinely looks like a distributed system (multiple agent surfaces, approval gate, compensating actions needed), and the book has an entire framework for exactly this pattern.
- The five failure modes in the saga gap table should be triaged as concrete P2 items when the decision pipeline is automated (agent-driven approval chain).
