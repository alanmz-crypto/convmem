# Cursor handoff — issue #286 main integration

**Arc:** Trapdoor Hunt (issue #286 operational follow-up; T3 stays closed)

**Date:** 2026-09-17

**Author:** Codex

**For:** The existing Cursor S0–S3 implementation session

**Authorization:** Ryan directly authorized a bounded rebase/integration on 2026-09-17. This is not PR, merge, live-indexing, watcher, or Arc Codex P2 authority.

## Resume state

- **Reviewed implementation:** `506afc1ff07ffab19c017f1b40b331bc3000ba7c` on `feat/2026-09-17-issue-286-incremental-index`; pushed, Copilot PASS, Kiro PASS, no PR.
- **Reviewed plan:** `6b62f0f5ab88286e201405e3dc6f40418c74f85a`.
- **Main at grant:** `18f63dbb6a9ea9f7c569862f29e176a49e3323a5`. Fetch and record the actual `origin/main` at integration start; stop if new changes make the conflict or scope materially different.
- **Integration:** performed and pushed on `feat/2026-09-17-issue-286-main-integration`; last code commit `5f142e2…`; R2b inventory regenerated; affected runtime gates PASS (146 pytest, pylint 10/10, compileall, diff-check).
- **Review verdicts on prior exact tip `e99856e…`:** Kiro PASS (S0–S3 contract preservation); Copilot FAIL (documentation acceptance — trailing whitespace, stale resume state, wrong tip routing in `LATEST.md`/`STATUS.md`).
- **State:** docs correction in progress to address Copilot findings; no PR, merge, or live operation until fresh Copilot and Kiro exact-tip reviews on the corrected pushed head (`git rev-parse origin/feat/2026-09-17-issue-286-main-integration` after fetch).

## Authorized work

1. Preserve the reviewed remote branch at `506afc1`. Repository policy forbids force-push, so create a **successor integration branch** from that tip, rebase the successor onto the freshly fetched `origin/main`, and push the successor with an explicit refspec. Do not rewrite the reviewed remote ref. Keep the work in a dedicated worktree; do not switch the shared checkout.
2. Resolve only the main-integration conflicts. Preserve both the #304 main-only changes and the reviewed S0–S3 implementation. Review any reused `rerere` resolution with `git rerere diff`.
3. After the final code and document resolutions, regenerate the R2b v2 writer-coverage inventory with the repository generator. Verify the content-derived `code_revision`, per-route bindings, and `inventory_digest` against the post-rebase tree; never hand-merge the digest. Refresh Shadow call-site evidence or canary hashes only if their actual sources moved. Reconcile `LATEST.md` and `STATUS.md` as current-state routing, not by restoring stale text.
4. Run affected S0–S3, crash-recovery, default-off/isolation, canary/P2-denial, R2b, and Shadow gates; Pylint regression, compile check, and `git diff --check`. Do not run the live-corpus Golden Eval merely to classify its earlier failure. Report exact commands/results and any remaining failures.
5. Commit and push the successor exact tip, leaving the worktree clean. Stop for **targeted Copilot and Kiro rechecks of that new tip and the integration delta**. No PR until Ryan separately authorizes it after those reviews.

## Scope lock

This grant does not authorize S4 existing-source adoption, S5 tail-only I/O, watcher/config/cap/exclusion changes, production indexing or profiling, source re-inclusion, issue #268 OOM closure claims, Arc Codex P2/grant/Gate 0/activation, PR creation, merge, or force-push. If integration needs a semantic change to the reviewed implementation, stop and return to Ryan with the exact conflict and proposed scope.

## Acceptance evidence

- `origin/main` is an ancestor of the pushed successor tip; the reviewed `506afc1` remote ref remains unchanged.
- The successor's runtime behavior matches the Copilot/Kiro-PASSed S0–S3 contract, and every new conflict resolution is visible in a small integration delta.
- Generated R2b and Shadow inventories, canary pins, and affected CI gates match the successor tip.
- New exact-tip Copilot/Kiro rechecks are requested; neither is presumed from the pre-rebase PASS.

**Next lane:** Existing Cursor session → Copilot targeted integration audit → Kiro targeted recheck → Ryan PR decision.

**TL;DR:** [Arc Trapdoor Hunt] Ryan authorized integration of reviewed issue #286 S0–S3 onto current main, with generated evidence and no force-push. Push a successor tip and stop for fresh targeted reviews; no PR or live operation.
