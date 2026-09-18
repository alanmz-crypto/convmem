# Copilot audit handoff — issue #286 main integration

**Arc:** Trapdoor Hunt, issue #286 (coordinated from Arc Codex)

**Date:** 2026-09-18

**Author:** Codex coordination lane

**For:** GitHub Copilot audit lane

**Authorization:** Ryan requested this targeted review handoff. It requests a read-only audit and grants no correction, PR, merge, or live operation.

## Target and prior authority

- **Review this exact target:** `e99856e49e42ad670d16ad0c22e8523afafb8ba1` on pushed `feat/2026-09-17-issue-286-main-integration`. Its last code commit is `5f142e2f988e41d7aec3f317bd142369a84183b0`; the target-tip commit updates handoff and routing docs. There is no PR.
- **Base:** `origin/main` was `18f63dbb6a9ea9f7c569862f29e176a49e3323a5` when the successor was built. Fetch and confirm the live refs before review. The reviewed predecessor `506afc1ff07ffab19c017f1b40b331bc3000ba7c` remains pushed on `feat/2026-09-17-issue-286-incremental-index` with prior Copilot and Kiro PASS. Those verdicts do not cover this rebased tip.
- **Purpose:** establish whether main integration preserves the previously reviewed S0–S3 fail-closed safety and isolation contract. The [Cursor integration handoff](https://github.com/alanmz-crypto/convmem/blob/e99856e49e42ad670d16ad0c22e8523afafb8ba1/docs/inter-model/CURSOR-2026-09-17-issue-286-main-integration-handoff.md) names the original grant and stops.

## Bounded audit

1. Compare predecessor and successor, then review the actual `18f63db..e99856e` merge patch. At handoff creation, a path-limited `git diff --exit-code 506afc1..5f142e2 -- incremental_jsonl.py incremental_jsonl_formats.py adapters/kiro_session_jsonl.py adapters/codex_history_jsonl.py adapters/codex_rollout_jsonl.py adapters/jsonl_prefix.py` was clean, as were the focused route/replay test paths. Independently verify this; the predecessor-to-successor difference also includes main-only #304 Claude protocol/doctor changes, so a raw whole-tree diff is not the incremental-code delta.
2. Verify the R2b inventory was regenerated from the post-integration tree: content-derived `code_revision`, per-route bindings, `inventory_digest`, and no lost #304 route. The predecessor-to-successor inventory diff appears to change only revision/digest fields; verify that finding. Check Shadow inventory and canary pins only where their actual sources moved. Do not hand-accept generated hashes.
3. Check the safety boundary most exposed by integration: default-off and isolated-root routing; no production Codex history adoption; complete-line coverage and prefix/sidecar continuity; prepared replay and rollback ordering; physical keep sets across both Chroma collections; refusal on corrupt checkpoint/cache, replacement, truncation, and interior rewrite. Confirm main-only changes do not create a bypass to writer governance, watcher, or Arc Codex P2.
4. Assess Cursor's reported affected-gate results against this exact successor: 146 focused pytest passed, pylint 10/10, compileall, and diff-check. Run only targeted checks needed to resolve a concrete audit risk. Use a clean worktree **outside** the shared repository root for any R2b scan or test; the locked `.claude/worktrees/agent-…` under ROOT has produced phantom constructor sites. The clean-main full-suite baseline has one unrelated deterministic Golden Eval failure and zero R2b failures; do not attribute that Golden Eval result to this integration.

## Return to Ryan

Give a written **PASS or FAIL for `e99856e49e42ad670d16ad0c22e8523afafb8ba1`**, with the specific integration delta checked, commands/evidence used, and any blocking file/line. State whether the predecessor PASS carries to the successor for the bounded S0–S3 safety claim. If the target tip changes, stop and request a new exact-tip review. Return a FAIL to Ryan and the existing #286 Cursor integrator; this handoff authorizes no correction or PR.

Do not audit Copilot `events.jsonl` E0–E4, issue #268 OOM closure, S4 adoption, S5 tail-only I/O, production indexing, watcher/config changes, or live activation here. Sol-High is only a later charter gate for materially conflicting Copilot/Kiro PASS-versus-FAIL verdicts on the same exact revision.

**TL;DR:** [Arc Trapdoor Hunt] Audit the pushed #286 successor `e99856e` for safety and isolation regressions introduced by main integration. Return an exact-tip PASS/FAIL; no corrective or live authority follows from this request.
