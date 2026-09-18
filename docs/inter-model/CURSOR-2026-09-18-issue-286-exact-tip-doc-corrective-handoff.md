# Cursor handoff — issue #286 exact-tip documentation correction

**Arc:** Trapdoor Hunt, issue #286 (coordinated from Arc Codex)

**Date:** 2026-09-18

**Author:** Codex coordination lane

**For:** The existing #286 Cursor integrator, sole shared-code writer through branch disposition

**Authorization:** Ryan delegated the writer choice to the Codex coordinator, which assigned this existing Cursor integrator through disposition. Ryan's earlier bounded integration grant includes routing-document reconciliation; this handoff confines correction to that existing scope after Copilot's FAIL. It grants no code change, PR, merge, or live operation.

## Resume state

- **Target branch:** pushed `feat/2026-09-17-issue-286-main-integration` at `e99856e49e42ad670d16ad0c22e8523afafb8ba1`. Preserve reviewed predecessor `506afc1ff07ffab19c017f1b40b331bc3000ba7c`; do not force-push either ref.
- **Kiro:** PASS on `e99856e` for S0–S3 contract preservation, with 20 R2b plus 96 focused tests passing. **Copilot:** FAIL on that same exact tip for the three documentation acceptance findings below; Copilot explicitly accepted runtime safety and R2b inventory continuity.
- **No Sol-High gate:** the reviewers did not assert incompatible facts. Kiro's S0–S3 behavioral PASS and Copilot's documentation FAIL can both hold. This is a bounded corrective and then fresh exact-tip reviews, not conflict adjudication.
- **No PR:** Ryan decides PR disposition only after the corrected tip receives both new reviews.

## Correct only these findings

1. In `docs/inter-model/CURSOR-2026-09-17-issue-286-main-integration-handoff.md`, remove trailing spaces at lines 3–6. Use blank lines instead of Markdown hard-break whitespace. Update the resume state at lines 14–15: the integration was performed and pushed; the prior tip failed exact-tip documentation acceptance and a docs correction is in progress. Preserve the original bounded authorization as history, clearly separate from current state.
2. In `docs/inter-model/LATEST.md` and `docs/inter-model/STATUS.md`, stop routing exact-tip review to last runtime commit `5f142e2` as if it were the branch head. Label `5f142e2` only as the last code commit if useful. Route reviewers to the **current pushed head** of `feat/2026-09-17-issue-286-main-integration` and require `git rev-parse origin/feat/2026-09-17-issue-286-main-integration` after fetch. Do not embed a would-be self-referential HEAD SHA in files committed to that same branch; the final SHA is reported in the handoff after push.
3. Reconcile the routing state with the actual verdicts: Kiro PASS on old exact tip `e99856e` for S0–S3 behavior; Copilot FAIL on that tip for documentation acceptance; corrected successor needs **fresh Copilot and Kiro exact-tip reviews**. No PR, merge, S4/S5, production indexing, watcher/config change, Arc Codex P2, or live activation follows from either old verdict.

## Acceptance and stop

- Keep changes to the three documentation files above. If a code, test, generated inventory, or semantic S0–S3 change is needed, stop and return the proposed scope to Ryan.
- In the isolated #286 worktree outside shared ROOT, verify `git diff --check origin/main..HEAD` exits 0 and `git diff --name-status e99856e..HEAD` lists only the three docs. Inspect the final rendered links and ensure the stale pending-state sentence is gone. No full suite is needed for this docs-only correction; preserve the reported earlier test evidence without claiming new tests ran.
- Commit and push the successor branch by explicit refspec with no force-push. Leave the worktree clean. Return the full new `git rev-parse HEAD` and `git rev-parse origin/feat/2026-09-17-issue-286-main-integration` values, the diff-check result, and the three-file delta to Ryan and the Codex coordinator. Stop for fresh exact-tip Copilot/Kiro reviews. Do not open a PR.

**TL;DR:** [Arc Trapdoor Hunt] Fix only the whitespace, stale resume state, and wrong tip routing that made `e99856e` fail Copilot acceptance. Push a new docs-only successor tip and stop for fresh Copilot/Kiro reviews.
