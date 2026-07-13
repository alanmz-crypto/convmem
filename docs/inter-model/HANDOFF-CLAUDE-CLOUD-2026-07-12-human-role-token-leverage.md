# Handoff: Low-effort human role with high token leverage

**Date:** 2026-07-12  
**From:** Ryan + Codex  
**To:** Claude Cloud  
**Purpose:** Advise Ryan how to contribute to convmem's multi-model workflow in a way that materially reduces token use without turning Ryan into a technical reviewer or adding substantial ongoing work. **No code edits or ledger writes.**

## The question

Ryan asked: *"In this project convmem what role could I step into that would save the most on tokens without adding a lot of work to my plate?"*

An initial answer proposed **decision triage / approval**: agents surface options, Ryan selects a direction, and the approved result is recorded so future sessions do not re-debate it. Ryan correctly challenged the premise:

> The models are being used because of vast knowledge, so I wouldn't think that is a minor bit of work for me.

The revised hypothesis is **brief owner / scope-locker**, rather than technical decision-maker. Ryan supplies only information the models cannot reliably infer: outcome priority, non-goals, definition of "done enough," and when to stop exploring. The models retain research, architecture, implementation, audit, and technical trade-off analysis.

Example:

> Optimize for reliability over elegance. No architecture rewrite. Give me one recommended path, implement it, and interrupt me only for irreversible choices.

## What we need from Claude

Give practical advice, not a restatement of the charter.

1. Is **brief owner / scope-locker** genuinely the best low-effort, high-token-leverage human role here? If not, name a better role.
2. Separate the human inputs that require no technical expertise from those that would covertly make Ryan a domain reviewer.
3. Propose a tiny operating cadence: the smallest repeatable input Ryan can give at task start and the narrow conditions that should interrupt him later.
4. Identify likely failure modes: over-constraining agents, vague instructions, premature stopping, or an excessive approval queue.
5. Recommend one simple template Ryan can paste at task start, and one escalation template agents should use when a real human decision is necessary.
6. Say where this fits or conflicts with the current HITL charter, especially the distinction between session ingest and durable ledger conclusions.

## Constraints

- Single user, single workstation, local-first corpus.
- Agents remain responsible for discovery, independent audit, design/sign-off, and implementation according to the lane charter.
- Ryan owns prioritization and durable conclusions; agents must not manufacture authority through a handoff.
- Do not assume Ryan has deep expertise in every technical domain agents investigate.
- Optimize for fewer wasted/repeated model turns, not merely fewer user messages.
- Do not propose a new orchestrator or code changes unless essential to the recommendation.

## Expected response

Return Markdown only:

1. **Recommendation** — one role and why it has the best effort-to-token-savings ratio.
2. **Two-minute operating loop** — start-of-task input, allowed autonomous behavior, and exact interruption conditions.
3. **Templates** — task brief and escalation request.
4. **Boundary** — what Ryan should explicitly *not* take on.
5. **Charter fit** — any small wording/protocol adjustment worth considering (advice only).

## Read order

1. This handoff
2. `context/TEAM-CHARTER-2026-07-06.md`
3. `context/AGENT-ROLES.md`
4. `context/MODEL-WORKFLOW.md`
5. `context/agent-protocol.md`

## Claude prompt

> Read `HANDOFF.md` first, then the context files. We want the smallest human role that reduces model-token waste without requiring Ryan to become a technical decision-maker. A prior suggestion—decision triage—was challenged because models are used precisely for deep knowledge. Assess the stronger alternative: Ryan as brief owner/scope-locker who supplies priorities, non-goals, a definition of done, and a stop rule while agents do the technical work. Recommend a more effective role if warranted. Return the requested operating loop and templates in Markdown only; no code changes or ledger writes.
