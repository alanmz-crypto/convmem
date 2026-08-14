# Implementation Handoff: Models must announce next-stage and show their work

**Date:** 2026-08-13  
**Author:** Kiro (design review)  
**For:** Codex (architecture planning) — or the new Kiro session triaging open PRs  
**Authorization:** Ryan, 2026-08-13 (verbal: models should say what stage is next, who does it, and the easiest way to see the work)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `docs/2026-08-13-arc-classification-verify-gap` |
| **Tip SHA** | (this commit) |
| **Push status** | pushed to origin |
| **PR** | not opened |
| **Ryan GATE** | New Kiro session may absorb this into its broader PR triage + agent-stage-awareness design |
| **Track A ingest** | Kiro session — indexed at handoff |

---

## The problem (simple version)

Models finish work, push it to GitHub, and stop with "await HITL." Ryan doesn't know the work is unverified until he manually traces every open PR. Meanwhile another model *should* be picking it up for the next phase (verification, review, merge-readiness) — but nobody told it to.

**Root cause:** Models announce upward (to Ryan) instead of forward (to the next lane). There's no norm that says "when you finish, name who's next and show them your work."

---

## The fix (behavioral norm, not protocol rewrite)

Every model, when finishing its current phase, must end with a **forward announcement**:

```
I finished: [phase name — e.g. "implementation", "architecture plan", "verification"]
Next step: [phase name — e.g. "verify this", "review this plan", "merge"]
Next lane: [who — e.g. "Kiro", "Cursor", "Ryan"]
See my work: [easiest path to evaluate it — a PR URL, a diff command, a specific file]
```

**"See my work" must be the easiest way to see it** — not a branch name and SHA that requires five commands to inspect. Examples:

| Situation | Good "see my work" | Bad |
|---|---|---|
| Implementation done | `https://github.com/.../pull/175/files` | "branch feat/2026-08-13-foo at tip abc123" |
| Plan ready for review | `docs/plans/ARCHITECTURE-foo.md` (one file to read) | "see the last 3 commits" |
| Bug fix pushed | `git diff origin/main..feat/fix-bar -- src/broken.py` | "check the worktree" |
| Verification complete | The VERIFY doc with PASS/FAIL table | "I ran the tests" |

---

## What this replaces

This supersedes the earlier framing in this same handoff (arc-classification gate / doctor check / intake field). That was overengineered. The actual gap is:

1. Models don't announce forward — they stop and wait for Ryan.
2. When they do announce, they don't include the easiest viewing path.

Fixing those two behaviors means:
- Work doesn't silently sit unverified on GitHub.
- The next model can start immediately without spelunking.
- Ryan sees the chain progressing without being the router for every transition.

---

## Relationship to the new Kiro session

Ryan is starting a new Kiro session that will:
1. Triage all open PRs
2. Map which agent needs to finish what
3. Give agents a way to know their own stage

This handoff is **input** to that session. The forward-announcement norm is the ongoing behavioral fix. The new session produces the one-time catch-up (routing table for everything currently stuck).

---

## What NOT to build

- No protocol doc rewrite (PLANNING-PROTOCOL.md, EXECUTE-TASK.md are fine)
- No doctor check for arc classification (the simpler norm covers it)
- No automation that routes between agents (just clear announcements)
- No new file format or template — the four-line block above is the whole thing

---

## Acceptance criteria

- [ ] Models end every phase with forward announcement (next step + next lane + easiest view)
- [ ] "See my work" is always a single link/command/path — not a scavenger hunt
- [ ] Open PRs that are currently stuck get unstuck by the catch-up triage
- [ ] Ryan is not the default router for agent-to-agent transitions
- [ ] Trivial work (single ack, one-line fix) scales down naturally (one sentence is fine)

---

## Related files

| What | Path |
|------|------|
| Planning Protocol (workflow, unchanged) | `docs/PLANNING-PROTOCOL.md` |
| Team Charter (lane assignments) | `docs/inter-model/TEAM-CHARTER-2026-07-06.md` |
| LATEST.md (current stuck-work evidence) | `docs/inter-model/LATEST.md` |
| This session's worktree cleanup review | (session transcript — Track A) |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed and pushed
- [x] `LATEST.md` bullet at top with link and resume state
- [ ] Branch pushed

**New session (picking up):**

- [ ] Read this for the behavioral norm
- [ ] Triage all open PRs for which ones are stuck between stages
- [ ] Produce the routing table (what's next, who does it, where to look)
- [ ] Establish the forward-announcement norm in whatever form fits

<!-- Original diagnosis: worktree cleanup had 3 rounds of plan review, 0 verification.
     Root cause: not missing protocol — models just don't announce forward. -->
