# Codex-to-Codex coordination — append-cursor ownership

**Arc:** Codex (coordination with Trapdoor Hunt issue #286)

**Date:** 2026-09-18

**Author:** Codex

**For:** Codex Sol and Ryan

**Authorization:** Ryan asked for a handoff to avoid confusion between agents working in this area. This handoff makes no Execute or ownership decision.

## Resume state

- The Arc Codex Copilot `events.jsonl` extension remains a **planning-only** proposal on `plan/2026-09-17-generalize-append-cursor`. Kiro PASSed the architecture and execution plan at `9e2d0ef` with two carry-forward conditions. The current planning branch includes later status/routing updates; verify its pushed tip before acting.
- Trapdoor Hunt issue #286 already has an **unmerged** S0–S3 shared-registry implementation. Its reviewed original tip is `506afc1` (Copilot and Kiro PASS). The successor integration branch `feat/2026-09-17-issue-286-main-integration` is pushed at `e99856e`, with code at `5f142e2` rebased onto `origin/main` `18f63db`. It is `READY_FOR_RECHECK`: targeted Copilot audit and Kiro recheck of the integration delta are next. There is no PR. Consult that branch's `docs/inter-model/CURSOR-2026-09-17-issue-286-main-integration-handoff.md` and current routing before assigning work.
- The #286 implementation already changes `incremental_jsonl.py` and adds `incremental_jsonl_formats.py`, including Kiro, Codex history, and Codex rollout entries. Its Codex route is restricted to fresh isolated sources. The Arc Codex proposal excludes rolling production `history.jsonl` and conditionally proposes Copilot only after E0 writer proof. These are different scopes; neither authorizes production history routing.

## Coordination recommendation for Ryan

1. Name the #286 Cursor implementation lane the **single shared-coordinator owner through its current integration, targeted reviews, and disposition**. This names a proposed owner; this document does not make Ryan's decision for him.
2. Keep Arc Codex E1–E4 coordinator and adapter implementation pending until #286's exact-tip review and branch disposition establish the base to extend. After that, Codex Sol can reconcile the Copilot Execute packet with the actual resulting base, and Cursor can implement only after Ryan's grant. Do not start a second concurrent `incremental_jsonl.py` edit.
3. If Ryan wants independent progress before #286 lands, an **E0-only** grant is the narrow choice: Cursor gathers controlled Copilot writer evidence in named temporary resources and returns an eligibility finding. The grant must explicitly state whether provider-backed CLI actions are permitted and bound any cost; the planning packet itself authorizes none. E0 grants no routing, coordinator implementation, bootstrap, live source, canary, or activation. E0 failure returns `NO_COPILOT_ROUTE`; no substitute format is implied.

## What Codex Sol should carry

- Treat the owner and E0 choice above as **recommendations awaiting Ryan**, not as an authorization or review verdict.
- Keep Kiro's Condition A in any later Execute: E3 must explicitly exercise `workspace.yaml` session-id changes, `session.start` versus YAML precedence, and state whether digest or effective-field changes trigger rebuild.
- Refresh exact remote tips and review state before changing the plan. Do not infer that the original #286 Copilot/Kiro PASS covers the successor integration tip, or that the Arc Codex planning PASS covers implementation.
- Keep Arc Codex P2, issue #268 OOM measurement, existing-source adoption, live canary, and activation in their separate gates.

## Next handoff

**Ryan:** decide the shared-code owner and whether E0 alone may start.

**Copilot audit and Kiro:** targeted rechecks of the pushed #286 integration tip.

**Codex Sol:** carry the planning boundary and reconcile the Copilot packet after the shared base is settled.

**Cursor:** act only within the relevant Ryan Execute grant.

**TL;DR:** [Arc Codex] #286 has already implemented the shared registry on an unmerged integration branch. Recommend one #286 owner through review/disposition; allow only a separately granted Copilot E0 evidence trace in parallel. No ownership, Execute, PR, or live grant is made here.
