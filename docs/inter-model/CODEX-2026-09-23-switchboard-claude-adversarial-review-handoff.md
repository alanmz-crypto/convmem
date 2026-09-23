# Adversarial Review Handoff — ConvMem Switchboard Transition Readiness

**Arc:** ConvMem Switchboard

**Date:** 2026-09-23  
**Author:** Codex architecture lane  
**For:** Claude adversarial-review lane  
**Authorization:** Ryan requested a handoff to assess whether transition preparation can begin now and whether additional safe preparation is possible.

## Resume state

| Field | Value |
|---|---|
| **State** | `READY_FOR_REVIEW` |
| **Branch** | `docs/2026-09-23-switchboard-naming-lock` |
| **Tip SHA** | See the commit containing this handoff |
| **Push status** | Must be pushed after commit |
| **PR** | Not opened |
| **Ryan GATE** | No runtime/configuration/credential change is authorized by this review request |

## Review question

Determine whether ConvMem and OpenClaw can begin a smooth transition-preparation phase now, before the Switchboard is live, and identify additional preparation that would materially reduce transition risk.

The review must answer two separate questions:

1. **Can we safely do the proposed preparation now?**
2. **What additional preparation is missing that can be done without prematurely activating, configuring, or qualifying the real integration?**

## Current facts to treat as inputs

- The Switchboard design chooses a version-adapted, read-only OpenClaw-to-ConvMem connector.
- ConvMem remains the durable authority; OpenClaw must not receive `record`, `approve`, or other durable-write capability.
- Bound project/site/domain scope is a hard ceiling; caller arguments may narrow but never widen it.
- `related()` must authorize the complete traversed result before rendering.
- `ask()` remains gated until synthesized-result handling is independently proven safe.
- The installed local OpenClaw is `2026.3.2`; capability probing found no `openclaw mcp` command and no `~/.openclaw/openclaw.json`.
- The latest bounded T0–T5 execution plan was merged in PR `#327`; its semantic parent is `cd9d2698b7423f907b552bc9118a0af523018ca9`, with reviewed overlay tip `d1ca459960e42458b352dfd0e76a7f55db67416b`.
- M7/M8 are synthetic fixture milestones. Passing them does not qualify the real runtime, live data, governed writes, or promotion.
- Gate D (real runtime), Gate W (governed writes), Gate D-V (value evaluation), Gate E (pilot), and promotion are separate later gates.
- Transcript capture remains blocked by the independent poison-transcript/Chroma data-integrity issue.
- The OpenClaw watch-coverage arc is separate: it covers committed repository knowledge, not live OpenClaw profiles, memory, workspaces, or transcripts.

## Proposed preparation to attack

Review the following proposed activities for safety, usefulness, and hidden coupling:

1. Choose and freeze the OpenClaw version/runtime baseline, including rollback version and dependency hashes.
2. Prepare a transition packet covering versions, scope, credentials, network, filesystem, service ownership, rollback, and evidence.
3. Prepare a disposable staging profile/workspace with synthetic data only.
4. Define a small acceptance workload covering scoped retrieval, denial behavior, prompt-injection-shaped memory, timeout/cancellation, child-agent behavior, and restart/rollback.
5. Draft the Gate D packet for authentication, containment, packaging, distribution, permissions, and provider/model behavior.
6. Design the child-agent inheritance observation, without assuming inheritance.
7. Repair/merge the bounded folder-watch work if its failing pytest baseline is resolved.
8. Define operational ownership for upgrade, qualification, scope changes, shutdown, rollback, and promotion.

## Adversarial review requirements

Classify every finding as exactly one of:

- `SAFE_NOW` — can proceed without changing live runtime, live config, credentials, data, authority, or production behavior.
- `REVIEW_REQUIRED` — useful, but needs an explicit architecture/design/review or Ryan decision before execution.
- `LIVE_DATA_OR_PROMOTION_BLOCKER` — cannot proceed until Gate D/W/D-V/E or promotion authority exists.
- `BUILD_BLOCKER` — reveals that the bounded T0–T5 contract is internally incomplete or unsafe.
- `NON_BLOCKING_UNCERTAINTY` — unresolved but does not prevent safe preparation.

Attack at least these failure modes:

- Updating OpenClaw changes the capability surface, dependency closure, auth route, or evidence identity.
- A staging profile accidentally reads real `HOME`, XDG paths, credentials, workspaces, or transcripts.
- The transition packet becomes an unreviewed production configuration or silently chooses Gate D values.
- Acceptance tasks accidentally exercise live channels, external side effects, durable writes, or `ask()`.
- Child-agent experiments infer inheritance from absence of a call rather than proving the runtime boundary.
- Watch coverage admits OpenClaw profiles, memory, databases, generated evidence, or secrets.
- Synthetic M7/M8 success is incorrectly reported as real-runtime or promotion readiness.
- Rollback leaves stale authority, publication, process, credential, or transcript state.
- The proposed preparation creates a second source of truth or bypasses ConvMem’s existing approval/admission boundaries.

## Expected response format

Return a concise written verdict with:

```text
ARC: ConvMem Switchboard
VERDICT: SAFE_TO_PREPARE | PREPARE_WITH_CONSTRAINTS | BLOCKED

SAFE_NOW:
- <item + why>

REVIEW_REQUIRED:
- <item + exact owner/gate>

BLOCKERS:
- <item + evidence + affected gate>

ADDITIONAL_PREPARATION:
- <highest-value missing item>

DO_NOT_DO:
- <specific prohibited action>

NEXT_LANE: Codex | Kiro | Cursor | Ryan
REQUIRED_NEXT_ACTION: <one concrete action>
```

Do not implement code, update OpenClaw, configure MCP, access live ConvMem data, use credentials, start a gateway, enable capture, or grant production permissions as part of this review.

## Reference files

- `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md`
- `docs/plans/EXECUTION-openclaw-convmem-integration.md` on the reviewed plan branch
- `docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md` on the reviewed plan branch
- `docs/plans/STATUS-openclaw-convmem-integration.md`
- `docs/plans/STATUS-openclaw-watch-coverage.md`
- `docs/inter-model/OPENCLAW-CONVMEM-FINAL-PROMPT-SUITE-DRAFT.md`

## Handoff boundary

Claude is reviewing transition readiness, not approving implementation or promotion. Any recommendation that changes runtime/authentication, permissions, mounts, services, network, provider/model, data admission, transcript capture, or production configuration must be returned as a separately owned Kiro/Ryan gate decision.
