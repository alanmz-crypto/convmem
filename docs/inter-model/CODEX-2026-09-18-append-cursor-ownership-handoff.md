# Codex-to-Codex coordination — append-cursor ownership

**Arc:** Codex (coordination with Trapdoor Hunt issue #286)

**Date:** 2026-09-18

**Author:** Codex

**For:** Codex Sol and Ryan

**Authorization:** Ryan selected the authoring Codex lane as coordination owner, then said, “Use your best judgement for this decision, and I agree.” This handoff records the shared-code base and prior writer choice. No Copilot E0, implementation, PR, or live Execute is granted.

## Resume state

- The Arc Codex Copilot `events.jsonl` extension remains a **planning-only** proposal on `plan/2026-09-17-generalize-append-cursor`. Kiro PASSed the original architecture and execution plan at `9e2d0ef` with two carry-forward conditions, then PASSed the post-merge correction at exact plan tip `53e7b42` against merged code `d657767`. No Execute was granted; verify the pushed tip before acting.
- Trapdoor Hunt issue #286's S0–S3 shared-registry implementation was squash-merged to `main` in [PR #307](https://github.com/alanmz-crypto/convmem/pull/307) as `d657767`. Kiro and Copilot PASSed exact reviewed head `19d34a5`, and all six CI checks passed. The merged registry/scanner and fresh isolated Codex routes are now the base for the Copilot proposal; plan reconciliation and targeted Kiro recheck are complete.
- The #286 implementation on `main` changes `incremental_jsonl.py` and adds `incremental_jsonl_formats.py` plus `adapters/jsonl_prefix.py`, including Kiro, Codex history, and Codex rollout entries. Its Codex route is restricted to fresh isolated sources. The Arc Codex proposal excludes rolling production `history.jsonl` and conditionally proposes Copilot only after E0 writer proof. These are different scopes; neither authorizes production history routing.

## Coordination owner

Ryan selected the **Codex Sol-medium lane that authored this handoff** to coordinate the overlap. That lane reconciles the plan with merged `main` and returns later Execute choices to Ryan. It does not take over Cursor implementation or invoke Sol-High. No qualifying Copilot/Kiro PASS-versus-FAIL conflict has been identified.

## Shared-code decision and remaining gate

1. **Completed writer assignment:** the existing #286 Cursor integrator was the sole writer of shared `incremental_jsonl.py` and its format registry through integration, review, and Ryan's merge. The coordination lane did not edit that code. A later Copilot implementation needs a separate Ryan writer assignment against merged `main`, with no concurrent shared-code writer.
2. **Sequence:** #286 is merged as `d657767`; Codex reconciled the Copilot packet and Kiro PASSed `53e7b42`. Ryan decides whether to grant E0 alone with exact client actions and provider/stop controls. E1–E4 remain pending until E0 evidence/review and a later Ryan writer/grant decision.
3. **E0 scope decision:** defer a Copilot E0 Execute grant for now. Installed CLI 1.0.86 permits a local offline-provider run under a temporary `COPILOT_HOME`; this avoids external model calls but cannot alone prove online writer parity. GitHub-hosted inference has a 30-credit minimum soft session limit that can overshoot on the final response. Ryan can choose an E0-only grant with exact permitted actions, temporary resources, provider/stop bound, and the `NO_COPILOT_ROUTE` stop rule. No substitute format is implied on E0 failure.

## What the other Codex Sol should carry

- Treat the #286 writer assignment above as completed history. E0 is deferred and ungranted. The authoring Codex lane owns plan reconciliation; Ryan owns a later Copilot writer assignment.
- Keep Kiro's Condition A in any later Execute: E3 must explicitly exercise `workspace.yaml` session-id changes, `session.start` versus YAML precedence, and state whether digest or effective-field changes trigger rebuild.
- Refresh `origin/main` before changing the plan. Do not infer that the Arc Codex planning PASS at `9e2d0ef` covers the post-merge revision or any implementation.
- Keep Arc Codex P2, issue #268 OOM measurement, existing-source adoption, live canary, and activation in their separate gates.

## Next handoff

**Ryan:** decide whether to grant E0 alone with bounded actions and explicit provider/stop controls; assign a later Copilot code writer only if E1–E4 are granted.

**Kiro:** targeted post-merge planning recheck complete and PASS at `53e7b42`; later evidence review only if E0 is granted.

**Codex Sol-medium (authoring lane):** return Kiro's PASS and the concrete E0-only choice to Ryan.

**Other Codex Sol:** no assignment on this lane; remain available only if a separately authorized task or qualifying review-conflict gate arises.

**Existing #286 Cursor integrator:** completed the shared-code integration; no new Execute scope is implied.

**TL;DR:** [Arc Codex] Issue #286's shared code is on `main`; Kiro PASSed the reconciled Copilot plan at `53e7b42`. Ryan decides E0 scope and a separate Copilot writer later. No Execute or live gate is granted.
