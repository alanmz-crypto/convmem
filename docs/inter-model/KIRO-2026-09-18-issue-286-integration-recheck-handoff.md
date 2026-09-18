# Kiro review handoff — issue #286 main integration

**Arc:** Trapdoor Hunt, issue #286 (coordinated from Arc Codex)

**Date:** 2026-09-18

**Author:** Codex coordination lane

**For:** Kiro design review lane

**Authorization:** Ryan requested this targeted review handoff. It requests a read-only recheck and grants no implementation, PR, merge, or live operation.

## Target and prior authority

- **Review this exact target:** `e99856e49e42ad670d16ad0c22e8523afafb8ba1` on pushed `feat/2026-09-17-issue-286-main-integration`. The last code commit is `5f142e2f988e41d7aec3f317bd142369a84183b0`; `e99856e` adds the integration handoff and current routing. No PR exists.
- **Reviewed predecessor:** `506afc1ff07ffab19c017f1b40b331bc3000ba7c` on `feat/2026-09-17-issue-286-incremental-index` received prior Copilot and Kiro PASS. **Reviewed plan:** `6b62f0f5ab88286e201405e3dc6f40418c74f85a`. **Integration base:** `origin/main` `18f63dbb6a9ea9f7c569862f29e176a49e3323a5` when rebased. Fetch and confirm the live refs before review; predecessor PASS does not automatically transfer.
- **Purpose:** confirm that the reviewed S0–S3 design and acceptance claim still hold on the integrated tree, and that the conflict resolutions and generated evidence are semantically consistent. The [Cursor integration handoff](https://github.com/alanmz-crypto/convmem/blob/e99856e49e42ad670d16ad0c22e8523afafb8ba1/docs/inter-model/CURSOR-2026-09-17-issue-286-main-integration-handoff.md) contains the bounded authorization and stop.

## Bounded recheck

1. Compare the previously reviewed patch series with the rebased series and inspect the final `18f63db..e99856e` tree. At handoff creation, the Kiro/Codex prefix adapters, `incremental_jsonl.py`, `incremental_jsonl_formats.py`, and focused route/replay tests were byte-identical between `506afc1` and `5f142e2`; confirm that independently. `git range-diff --no-patch ef4a7dd..506afc1 18f63db..5f142e2` paired all eleven implementation commits, with differences concentrated in generated inventory/routing reconciliation.
2. Check that the closed format registry, Kiro compatibility oracle, source/sidecar authority, complete-line outcome coverage, fingerprint/source IDs, prepared replay, rollback, and physical keep-set semantics retain the S0–S3 contract after integration. Confirm Codex history/rollout remain fresh-source and isolation-bound; the rolling production `history.jsonl` is outside this route's claim.
3. Review the conflict resolution in the R2b inventory and `LATEST.md`/`STATUS.md`: #304 main-only route coverage must survive, generated digests must bind the integrated tree, and the docs must not imply live or PR authority. Check Shadow inventory and canary pins if their source contracts moved. Treat Cursor's reported 146 focused pytest, pylint 10/10, compileall, and diff-check as reported evidence until verified.
4. Keep the Arc Codex Copilot `events.jsonl` extension separate. Its planning PASS is pinned to `9e2d0ef`, E0 remains ungranted, and E1–E4 wait for this branch's review/disposition. No shared-code writer overlap is planned: the existing #286 Cursor integrator is assigned through this branch's disposition.

Use a clean worktree **outside** the shared repository root for any R2b test or scan. The locked `.claude/worktrees/agent-…` under ROOT has produced phantom constructor sites. The clean-main full suite had one unrelated deterministic Golden Eval failure and zero R2b failures; compare only affected gates needed to judge this integration.

## Return to Ryan

Give a written **PASS or FAIL for `e99856e49e42ad670d16ad0c22e8523afafb8ba1`** on whether the previously reviewed S0–S3 contract carries through main integration. Identify the exact changed fact, file/line, and corrective boundary for any FAIL. If the target tip changes, stop and request a new exact-tip recheck. Review grants no PR or Execute. A material opposite Copilot verdict on the same exact tip is the only potential Sol-High conflict gate; deferral or a different revision is not one.

Do not re-open S4 adoption, S5 tail-only I/O, issue #268 OOM closure, Arc Codex P2, production indexing, watcher/config operations, bootstrap, or activation.

**TL;DR:** [Arc Trapdoor Hunt] Recheck the pushed #286 successor `e99856e` against the previously PASSed S0–S3 contract and integration evidence. Return an exact-tip PASS/FAIL; no implementation or live grant follows.
