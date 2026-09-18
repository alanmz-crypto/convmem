# Codex-to-Codex coordination — append-cursor ownership

**Arc:** Codex (coordination with Trapdoor Hunt issue #286)

**Date:** 2026-09-18

**Author:** Codex

**For:** Codex Sol, Ryan, and the existing #286 Cursor integrator

**Authorization:** Ryan selected the authoring Codex lane as coordination owner, then said, “Use your best judgement for this decision, and I agree.” This handoff records the resulting shared-code writer choice. No Copilot E0, implementation, PR, or live Execute is granted.

## Resume state

- The Arc Codex Copilot `events.jsonl` extension remains a **planning-only** proposal on `plan/2026-09-17-generalize-append-cursor`. Kiro PASSed the architecture and execution plan at `9e2d0ef` with two carry-forward conditions. The current planning branch includes later status/routing updates; verify its pushed tip before acting.
- Trapdoor Hunt issue #286 already has an **unmerged** S0–S3 shared-registry implementation. Its reviewed original tip is `506afc1` (Copilot and Kiro PASS). The successor integration branch `feat/2026-09-17-issue-286-main-integration` is pushed at `e99856e`, with code at `5f142e2` rebased onto `origin/main` `18f63db`. It is `READY_FOR_RECHECK`: targeted Copilot audit and Kiro recheck of the integration delta are next. There is no PR. Consult that branch's `docs/inter-model/CURSOR-2026-09-17-issue-286-main-integration-handoff.md` and current routing before assigning work.
- The #286 implementation already changes `incremental_jsonl.py` and adds `incremental_jsonl_formats.py`, including Kiro, Codex history, and Codex rollout entries. Its Codex route is restricted to fresh isolated sources. The Arc Codex proposal excludes rolling production `history.jsonl` and conditionally proposes Copilot only after E0 writer proof. These are different scopes; neither authorizes production history routing.

## Coordination owner

Ryan selected the **Codex Sol-medium lane that authored this handoff** to coordinate the overlap. That lane tracks exact branch and review state, maintains this planning boundary, and returns later Execute choices to Ryan. It does not take over Cursor implementation or invoke Sol-High. No qualifying Copilot/Kiro PASS-versus-FAIL conflict has been identified.

## Shared-code decision and remaining gate

1. **Assigned writer:** the existing #286 Cursor integrator is the sole writer of shared `incremental_jsonl.py` and its format registry through the current integration, targeted rechecks, and Ryan's branch disposition. The coordination lane does not edit that code. A later Copilot implementation is a separate assignment against the resulting base, with no concurrent shared-code writer.
2. **Sequence:** targeted Copilot and Kiro rechecks of the exact #286 successor tip come next. Keep Arc Codex E1–E4 coordinator and adapter implementation pending until review and disposition establish the base to extend. Then the coordinating Codex lane reconciles the Copilot Execute packet with that base; Cursor acts only under a later Ryan grant.
3. **E0 scope decision:** defer a Copilot E0 Execute grant for now. The controlled writer trace may need provider-backed CLI actions, and no exact permitted action/cost bound has been named. After the #286 review and branch disposition, Ryan can choose an E0-only grant with named temporary resources, provider-action permission and cap, and the `NO_COPILOT_ROUTE` stop rule. No substitute format is implied on E0 failure.

## What the other Codex Sol should carry

- Treat the #286 writer assignment above as the coordination decision Ryan delegated to this lane. E0 is deferred and ungranted. The authoring Codex lane owns coordination; the existing #286 Cursor integrator owns shared-code edits through disposition.
- Keep Kiro's Condition A in any later Execute: E3 must explicitly exercise `workspace.yaml` session-id changes, `session.start` versus YAML precedence, and state whether digest or effective-field changes trigger rebuild.
- Refresh exact remote tips and review state before changing the plan. Do not infer that the original #286 Copilot/Kiro PASS covers the successor integration tip, or that the Arc Codex planning PASS covers implementation.
- Keep Arc Codex P2, issue #268 OOM measurement, existing-source adoption, live canary, and activation in their separate gates.

## Next handoff

**Ryan:** decide #286 PR/merge disposition after exact-tip reviews; later decide whether to grant E0 alone with bounded actions and cost.

**Copilot audit and Kiro:** targeted rechecks of the pushed #286 integration tip.

**Codex Sol-medium (authoring lane):** coordinate the overlap and reconcile the Copilot packet after the shared base is settled.

**Other Codex Sol:** no assignment on this lane; remain available only if a separately authorized task or qualifying review-conflict gate arises.

**Existing #286 Cursor integrator:** sole shared-code writer through integration review and disposition; no new Execute scope is implied.

**TL;DR:** [Arc Codex] Ryan delegated the writer choice; the existing #286 Cursor integrator is the sole shared-code writer through branch disposition. The authoring Codex lane coordinates. Copilot E0 and all later implementation/live gates remain ungranted.
