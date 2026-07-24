# Ledger-first audit baseline (Qwen) — salvage status

**Salvaged:** 2026-07-24 onto docs branch for one-workspace takeover.  
**Verdict:** YELLOW — ledger-first direction sound; prerequisites before cutover.  
**Authority today:** Chroma remains Tier-1 for observations.

## Files

| File | Role |
|---|---|
| `CURRENT-OBSERVATION-AUTHORITY.md` | What is authoritative today |
| `CANONICAL-OBSERVATION-PROPOSAL.md` | Proposed canonical record (provisional / end-state) |
| `REPLAY-AND-PROJECTION-CONTRACT.md` | Replay / equality contract |
| `LEDGER-FAILURE-MATRIX.md` | Failure modes |
| `EXISTING-DATA-MIGRATION-ASSESSMENT.md` | Orphans / legacy decisions inventory |
| `TRANSITION-OPTIONS.md` | Transition options (shadow vs cutover) |
| `BACKUP-RESTORE-IMPLICATIONS.md` | Backup / restore implications |
| `LEDGER-FIRST-READINESS-VERDICT.md` | Overall YELLOW readiness |

## Required corrections before treating as clean baseline

Draft Architecture PR [#115](https://github.com/alanmz-crypto/convmem/pull/115)
(`ARCHITECTURE-shadow-ledger-phase0.md` @ `c9a5c70`) lists docs-only
corrections that are **not yet applied** in these salvaged files:

| File | Required correction |
|---|---|
| `REPLAY-AND-PROJECTION-CONTRACT.md` | Scope full rebuild to post-cutover; fix random-Chroma-ID claim; require exact document equality; stop checkpoint at corruption |
| `TRANSITION-OPTIONS.md` | Replace “zero production behavior change”; scope to unit mutations; distinguish delta proof from historic rebuild |
| `LEDGER-FAILURE-MATRIX.md` | Add post-Chroma/pre-shadow gap and bounded-lock/fsync semantics; corruption = readiness FAIL |
| `BACKUP-RESTORE-IMPLICATIONS.md` | Phase 0 banner: Chroma-first restore unchanged; shadow backup wiring not authorized |
| `LEDGER-FIRST-READINESS-VERDICT.md` | Mark inventory counts as snapshot values; separate Phase 0 delta gates from cutover gates |
| `CURRENT-OBSERVATION-AUTHORITY.md` | Preserve Chroma authority; explicit summary/decision-log exclusions |
| `EXISTING-DATA-MIGRATION-ASSESSMENT.md` | Runtime-stamp inventory; human classification + ID mapping as later gates |
| `CANONICAL-OBSERVATION-PROPOSAL.md` | Label schema provisional/end-state; do not substitute for Phase 0 event envelope |

## Do not

- Treat this directory as authorization for production hooks, cutover, Neutral, or restore-order flip
- Confuse this JSONL-oriented audit with the Phase 0 **shadow event envelope** locked in #115
