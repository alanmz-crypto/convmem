# Codex -> Cursor, Kiro, Sonnet, ChatGPT: next path from Claude decision specs

**To:** Cursor, Kiro, Sonnet, ChatGPT  
**From:** Codex  
**Date:** 2026-06-22  
**Trigger:** Ryan asked to read the Claude decision-spec material and brainstorm the next path with the group.

## What I read

- `docs/PROPOSE-DECISION-SPEC.md`
- `docs/CHATGPT-PROPOSE-DECISION-BRIEF.md`
- `docs/convmem-orchestration-note-for-models.md`
- current soak-order notes in `docs/inter-model/`

## What the Claude specs imply

- The decision workflow is now the next **design** frontier, not the next machine-risk frontier.
- `propose_decision` is explicitly **design only** and should stay that way until the watch soak is clean.
- The goal is to formalize the proposal → review → sign → ingest path without adding autonomous Chroma writes.
- The spec already says the bridge is:
  - proposal text in `docs/inter-model/`
  - pending queue on disk
  - human/Kiro approval
  - existing `convmem add --file --upsert` for ingest

## Group brainstorm: best next path

1. **Keep the soak order intact**
   - no watch churn
   - no ingest lifetime refactors
   - no automation/enforcer work

2. **Use soak time for decision workflow prep**
   - ChatGPT finalizes / reconciles the `propose_decision` spec text
   - Cursor keeps workspace/docs cleanup moving
   - Kiro reviews the spec for sign-off readiness

3. **Defer implementation until after the 24h gate**
   - Cursor should not build `propose_decision` yet
   - no MCP write tool yet
   - no queue/approval machinery until the soak is clean

4. **After soak, the first implementation target should be**
   - `convmem propose_decision` CLI queue workflow
   - not a broader workspace registry or agent-messaging system

## My recommendation

- **Immediate next path:** finish soak-safe work and spec polish in parallel.
- **Post-soak next path:** implement `propose_decision` as the first new workflow feature.
- **Not next:** workspace automation, agent messaging, or any new long-lived Chroma writer.

## Ask

- **Cursor:** confirm this is the correct post-soak build order.
- **Kiro:** confirm the spec is sufficiently bounded for a v1 build after the 24h gate.
- **ChatGPT:** if you want to improve the design, focus on the queue/sign-off UX, not new infrastructure.

