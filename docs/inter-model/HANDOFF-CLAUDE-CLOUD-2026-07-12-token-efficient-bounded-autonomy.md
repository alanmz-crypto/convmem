# Handoff: Token-efficient bounded-autonomy architecture review

**Date:** 2026-07-12
**From:** Ryan + Codex
**To:** Claude Cloud
**Purpose:** Review the completed architecture for a Cursor-first bounded-autonomy pilot in convmem. Determine whether it cuts coordination tokens to the safe practical floor without weakening expert reasoning, verification, lane boundaries, or non-Git operational safety. **No code edits, runtime changes, merges, or ledger writes.**

## Decision under review

The architecture proposes a prompt-policy overlay, not a new service or command:

- Ryan normally supplies one required sentence: the observable outcome.
- Cursor executes three routine tasks in the real `~/Projects/convmem` repository.
- Cursor researches silently, chooses one path, implements, verifies, commits, pushes, and Track A-indexes without routine approval interruptions.
- A fresh Cursor session must retrieve prior pilot context through convmem without Ryan pasting it.
- Codex reviews the accumulated evidence once after the three-task streak, rather than shadowing every task.
- A non-mutating Cloudflare/DNS probe tests exact authorization semantics.
- WordPress is a separate later probation because convmem success cannot validate backup-before-DB-mutation behavior.
- Promotion is staged: manual pilot, opt-in canonical mode, three-task soak, then routine-convmem default.

## Read order

1. `ARCHITECTURE-token-efficient-bounded-autonomy.md`
2. `context/TEAM-CHARTER-2026-07-06.md`
3. `context/AGENT-ROLES.md`
4. `context/agent-protocol.md`
5. `context/MODEL-WORKFLOW.md`
6. Builder references only where needed:
   - `builder-reference/ousterhout-builder-digest.md`
   - `builder-reference/hard-parts-builder-digest.md`
   - `builder-reference/evolutionary-architectures-builder-digest.md`
   - `builder-reference/zeller-builder-digest.md`

## Questions for Claude

1. Does the precedence model correctly prevent bounded autonomy from overriding system permissions, lane `must not` rules, domain safety, and exact external authorization?
2. Is the proposed lower bound—one brief, surface-required short updates, and one concise final report—actually the lowest safe coordination overhead?
3. Which remaining instructions or measurements consume tokens without protecting a demonstrated failure mode?
4. Does making Cursor the sole execution surface for the three convmem tasks isolate the policy variable appropriately?
5. Is one Codex promotion review sufficient, or does the charter require more independent review for routine pilot tasks?
6. Does the fresh-Cursor Track A retrieval test prove useful coordination, or merely prove that indexing occurred?
7. Are the three-task PASS/reset rules strong enough? Identify any false-PASS path.
8. Is separating WordPress probation correct, and is any non-Git risk still incorrectly treated as reversible?
9. Should any part of Stage 2 be shortened further before entering the always-loaded protocol, so the standing-token cost does not erase the savings?
10. Recommend the three best first convmem task shapes for this pilot. Do not invent work merely to exercise the policy.

## Expected output

Return Markdown only:

1. **Verdict:** accept, accept with changes, or redesign.
2. **Token-floor audit:** protected, compressible, and still-wasteful token use.
3. **Safety/authority audit:** confirmed boundaries and false-PASS risks.
4. **Cursor coordination audit:** whether the loop is sufficient without new orchestration.
5. **Required changes before pilot:** ordered and minimal.
6. **Recommended pilot task shapes:** three, with selection criteria.
7. **Compact revised contract:** only if it is materially shorter or safer than the proposed one.

## Constraints

- Single user, single workstation, local-first corpus.
- The real convmem repository is the pilot environment; no dev fork or lab runtime.
- Agents never merge or push `main`; Ryan owns merges.
- Ryan alone approves durable conclusions; handoff and Track A are not records.
- WordPress DB mutations always require a verified backup and remain outside this pilot.
- External changes require exact resource, operation, and intended final value or named one-shot action.
- Do not use unmeasured token-saving percentages.
- Do not propose a tracker, orchestrator, or new logging surface unless the existing architecture cannot produce trustworthy evidence.

## Claude prompt

> Read `ARCHITECTURE-token-efficient-bounded-autonomy.md` first, then the charter and protocol context. Audit whether this Cursor-first convmem pilot cuts coordination tokens to the lowest safe practical bound without cutting expert reasoning, evidence, verification, or authority gates. Look specifically for false-PASS paths, standing-token costs, redundant review, and gaps in cross-session Track A coordination. Recommend only changes that materially improve safety or reduce tokens. Return Markdown only; do not edit code, merge branches, write records, or mutate external systems.
