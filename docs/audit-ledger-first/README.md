# Audit: ledger-first readiness (salvaged 2026-07-24)

**Who/What:** Eight-file Qwen/Cursor audit baseline for observation ledger-first /
Shadow Ledger Phase 0 research, previously untracked on the shared checkout.

**When:** Salvaged to GitHub so one workspace can take over after multi-chat
coordination (see `docs/inter-model/COORD-2026-07-24-shadow-ledger-workspaces-BOARD.md`).

**Why:** Draft Architecture [#115](https://github.com/alanmz-crypto/convmem/pull/115)
depends on these files existing with the listed corrections; Cursor Execute remains
forbidden until Ryan HITL + Execution plan.

**How:** Each file includes an Architecture #115 corrections block applied at
salvage. Treat this directory as **docs evidence**, not runtime authorization.

| File | Role |
|---|---|
| CURRENT-OBSERVATION-AUTHORITY.md | Authority map (Chroma-first today) |
| CANONICAL-OBSERVATION-PROPOSAL.md | Provisional end-state schema (not Phase 0 envelope) |
| LEDGER-FAILURE-MATRIX.md | Failure / gap matrix |
| REPLAY-AND-PROJECTION-CONTRACT.md | Replay/projection contract (post-cutover rebuild scoped) |
| EXISTING-DATA-MIGRATION-ASSESSMENT.md | Migration inventory notes (snapshot counts) |
| TRANSITION-OPTIONS.md | Shadow vs cutover options |
| BACKUP-RESTORE-IMPLICATIONS.md | Backup/restore (Phase 0: Chroma-first unchanged) |
| LEDGER-FIRST-READINESS-VERDICT.md | YELLOW verdict + gates |

**Does not authorize:** production shadow hooks, cutover, restore-order flip, Neutral extraction, or live Restic changes.
