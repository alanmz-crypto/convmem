# Codex-to-Codex coordination — append-cursor ownership

**Arc:** Codex (coordination with Trapdoor Hunt issue #286)

**Date:** 2026-09-18

**Author:** Codex

**For:** Codex Sol and Ryan

**Authorization:** Ryan asked for a handoff to avoid confusion, then selected the Codex lane that authored it as coordination owner on 2026-09-18. This assigns coordination only; Ryan has not assigned the shared-code writer or granted Execute.

## Resume state

- The Arc Codex Copilot `events.jsonl` extension remains a **planning-only** proposal on `plan/2026-09-17-generalize-append-cursor`. Kiro PASSed the architecture and execution plan at `9e2d0ef` with two carry-forward conditions. The current planning branch includes later status/routing updates; verify its pushed tip before acting.
- Trapdoor Hunt issue #286 already has an **unmerged** S0–S3 shared-registry implementation. Its reviewed original tip is `506afc1` (Copilot and Kiro PASS). The successor integration branch `feat/2026-09-17-issue-286-main-integration` is pushed at `e99856e`, with code at `5f142e2` rebased onto `origin/main` `18f63db`. It is `READY_FOR_RECHECK`: targeted Copilot audit and Kiro recheck of the integration delta are next. There is no PR. Consult that branch's `docs/inter-model/CURSOR-2026-09-17-issue-286-main-integration-handoff.md` and current routing before assigning work.
- The #286 implementation already changes `incremental_jsonl.py` and adds `incremental_jsonl_formats.py`, including Kiro, Codex history, and Codex rollout entries. Its Codex route is restricted to fresh isolated sources. The Arc Codex proposal excludes rolling production `history.jsonl` and conditionally proposes Copilot only after E0 writer proof. These are different scopes; neither authorizes production history routing.

## Coordination owner

Ryan selected the **Codex Sol-medium lane that authored this handoff** to coordinate the overlap. That lane tracks exact branch and review state, maintains this planning boundary, and returns code-writer and Execute choices to Ryan. It does not take over Cursor implementation or invoke Sol-High. No qualifying Copilot/Kiro PASS-versus-FAIL conflict has been identified.

## Remaining recommendation for Ryan

1. Name the existing #286 Cursor integrator the **single shared-code writer through its current integration, targeted reviews, and disposition**. This is a recommendation awaiting Ryan's code-writer decision; the Codex coordination assignment above does not settle it.
2. Keep Arc Codex E1–E4 coordinator and adapter implementation pending until #286's exact-tip review and branch disposition establish the base to extend. After that, the coordinating Codex lane can reconcile the Copilot Execute packet with the actual resulting base, and Cursor can implement only after Ryan's grant. Do not start a second concurrent `incremental_jsonl.py` edit.
3. If Ryan wants independent progress before #286 lands, an **E0-only** grant is the narrow choice: Cursor gathers controlled Copilot writer evidence in named temporary resources and returns an eligibility finding. The grant must explicitly state whether provider-backed CLI actions are permitted and bound any cost; the planning packet itself authorizes none. E0 grants no routing, coordinator implementation, bootstrap, live source, canary, or activation. E0 failure returns `NO_COPILOT_ROUTE`; no substitute format is implied.

## What the other Codex Sol should carry

- Treat the shared-code writer and E0 choice above as **recommendations awaiting Ryan**, not as an authorization or review verdict. The authoring Codex lane owns coordination.
- Keep Kiro's Condition A in any later Execute: E3 must explicitly exercise `workspace.yaml` session-id changes, `session.start` versus YAML precedence, and state whether digest or effective-field changes trigger rebuild.
- Refresh exact remote tips and review state before changing the plan. Do not infer that the original #286 Copilot/Kiro PASS covers the successor integration tip, or that the Arc Codex planning PASS covers implementation.
- Keep Arc Codex P2, issue #268 OOM measurement, existing-source adoption, live canary, and activation in their separate gates.

## Next handoff

**Ryan:** decide the shared-code writer and whether E0 alone may start.

**Copilot audit and Kiro:** targeted rechecks of the pushed #286 integration tip.

**Codex Sol-medium (authoring lane):** coordinate the overlap and reconcile the Copilot packet after the shared base is settled.

**Other Codex Sol:** no assignment on this lane; remain available only if a separately authorized task or qualifying review-conflict gate arises.

**Cursor:** act only within the relevant Ryan Execute grant.

**TL;DR:** [Arc Codex] Ryan selected the authoring Codex Sol-medium lane to coordinate. The #286 Cursor integrator remains the recommended sole shared-code writer, pending Ryan's decision. E0, implementation, PR, and live work remain ungranted.
