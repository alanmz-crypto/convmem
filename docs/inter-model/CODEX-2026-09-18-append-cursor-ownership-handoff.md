# Codex-to-Codex coordination — append-cursor ownership

**Arc:** Codex (coordination with Trapdoor Hunt issue #286)

**Date:** 2026-09-18

**Author:** Codex

**For:** Codex Sol and Ryan

**Authorization:** Ryan selected the authoring Codex lane as coordination owner, then said, “Use your best judgement for this decision, and I agree.” This handoff records the shared-code base and prior writer choice. No Copilot E0, implementation, PR, or live Execute is granted.

## Resume state

- The Arc Codex Copilot `events.jsonl` proposal is **STOPPED: `NO_COPILOT_ROUTE`** under the current contract by Ryan's 2026-09-18 decision. Kiro PASSed its planning documents at `9e2d0ef` and post-merge correction at `53e7b42`, but the later local trace did not pass E0. No implementation or hosted Execute was granted.
- Trapdoor Hunt issue #286's S0–S3 shared-registry implementation was squash-merged to `main` in [PR #307](https://github.com/alanmz-crypto/convmem/pull/307) as `d657767`. Kiro and Copilot PASSed exact reviewed head `19d34a5`, and all six CI checks passed. The merged registry/scanner and fresh isolated Codex routes are now the base for the Copilot proposal; plan reconciliation and targeted Kiro recheck are complete.
- The #286 implementation on `main` changes `incremental_jsonl.py` and adds `incremental_jsonl_formats.py` plus `adapters/jsonl_prefix.py`, including Kiro, Codex history, and Codex rollout entries. Its Codex route is restricted to fresh isolated sources. The Arc Codex proposal excludes rolling production `history.jsonl` and conditionally proposes Copilot only after E0 writer proof. These are different scopes; neither authorizes production history routing.

## Coordination owner

Ryan selected the **Codex Sol-medium lane that authored this handoff** to coordinate the overlap. That work is complete. It did not take over Cursor implementation or invoke Sol-High. No qualifying Copilot/Kiro PASS-versus-FAIL conflict arose.

## Shared-code decision and remaining gate

1. **Completed writer assignment:** the existing #286 Cursor integrator was the sole writer of shared `incremental_jsonl.py` and its format registry through integration, review, and Ryan's merge. The coordination lane did not edit that code. A later Copilot implementation needs a separate Ryan writer assignment against merged `main`, with no concurrent shared-code writer.
2. **Sequence closed:** #286 merged as `d657767`; Codex reconciled the Copilot packet and Kiro PASSed `53e7b42`. Ryan granted one preliminary offline local writer trace, specified in the [Cursor handoff](CODEX-2026-09-18-copilot-e0-local-trace-handoff.md), then stopped the Copilot proposal after its E0 result.
3. **E0 result and stop:** Prior bytes remained exact prefixes, but each action used a new inode and the final action triggered an unexpected `read_agent` tool call. The merged coordinator regards inode change as `source_replaced_or_rotated`, preventing incremental reuse under the current contract. Kiro confirmed the decisive inode finding. Its separate claim that changed `workspace.yaml` digests independently refuse cross-run reuse was unsupported by checkpoint/continuity code; the digest check is within one run. Ryan chose `NO_COPILOT_ROUTE`. No hosted proof, E1–E4, or substitute format is authorized.

## What the other Codex Sol should carry

- Treat the #286 writer assignment and Copilot E0 trace as completed history. The current Copilot route is closed; a future attempt requires a new Ryan scope and writer decision.
- Keep Kiro's Condition A in any later Execute: E3 must explicitly exercise `workspace.yaml` session-id changes, `session.start` versus YAML precedence, and state whether digest or effective-field changes trigger rebuild.
- Refresh `origin/main` before changing the plan. Do not infer that the Arc Codex planning PASS at `9e2d0ef` covers the post-merge revision or any implementation.
- Keep Arc Codex P2, issue #268 OOM measurement, existing-source adoption, live canary, and activation in their separate gates.

## Next handoff

**Ryan:** no pending Copilot decision. A future reopening needs a new scope decision based on measured value.

**Kiro:** targeted plan and trace rechecks complete; correct the separate sidecar-refusal assertion only if a revised E0 design is pursued.

**Codex Sol-medium (authoring lane):** record Ryan's stop decision, then close this coordination lane.

**Other Codex Sol:** no assignment on this lane; remain available only if a separately authorized task or qualifying review-conflict gate arises.

**Existing #286 Cursor integrator:** completed the shared-code integration; no new Execute scope is implied.

**TL;DR:** [Arc Codex] Issue #286's shared code remains on `main`; Ryan stopped the Copilot extension as `NO_COPILOT_ROUTE` after the local trace found inode replacement on every action. No further Copilot work is authorized by this packet.
