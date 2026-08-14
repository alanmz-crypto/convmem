# Handoff: Models must announce forward (next stage, next lane, show the work)

**Date:** 2026-08-13 (revised same day)  
**Author:** Kiro (design review)  
**For:** New Kiro session (open-PR triage + agent stage-awareness map)  
**Authorization:** Ryan, 2026-08-13 (verbal: models should say what stage is next, who does it, and the easiest way to see the work)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `docs/2026-08-13-arc-classification-verify-gap` |
| **Push status** | pushed to origin |
| **PR** | not opened |
| **Ryan GATE** | New Kiro session absorbs this into broader PR triage + stage-awareness design |

---

## The problem

Models finish work, push it to GitHub, and stop with "await HITL." Ryan doesn't know the work is unverified until he manually traces every open PR's state. Meanwhile another model *should* be picking it up for the next phase — but nobody told it to.

**Root cause:** Models announce upward (to Ryan) instead of forward (to the next lane). There's no norm that says "when you finish, name who's next and show them your work in the easiest way possible."

**How this was discovered:** The worktree cleanup had three rounds of plan review but zero post-implementation verification. The VERIFY system exists and works — but it only fires when another model is told to run it. Nobody was told.

---

## The fix (behavioral norm)

Every model, when finishing its current phase, must end with a **forward announcement**:

```
I finished: [phase — e.g. "implementation", "plan", "verification"]
Next step:  [what needs to happen — e.g. "verify this", "review the plan", "merge"]
Next lane:  [who — e.g. "Kiro", "Cursor", "Ryan"]
See my work: [the single easiest way to evaluate what I did]
```

### "See my work" must be the lowest-effort path

Not a branch name and SHA. The one thing the next model (or Ryan) opens to understand what happened:

| Situation | Good | Bad |
|---|---|---|
| Implementation done | PR diff URL: `github.com/.../pull/175/files` | "branch feat/2026-08-13-foo at abc123" |
| Plan ready | One file: `docs/plans/ARCHITECTURE-foo.md` | "see the last 3 commits on the branch" |
| Bug fix | `git diff origin/main -- src/broken.py` | "check the worktree" |
| Verification done | VERIFY doc with PASS/FAIL table | "I ran the tests, they passed" |

---

## What this replaces

This handoff originally proposed a protocol rewrite (arc-classification gate, doctor checks, intake fields). That was overengineered. The actual gap is two missing behaviors:

1. Models don't announce forward — they stop and point up at Ryan.
2. When they do reference their work, they don't include the easiest viewing path.

The existing VERIFY system, EXECUTE-TASK phase, and planning protocol are all fine. They just don't fire because no one chains them forward.

---

## Relationship to the new Kiro session

Ryan is starting a new Kiro session to:
1. Triage all open PRs — which ones are stuck between stages
2. Map which agent needs to finish what
3. Give agents a stage-awareness capability

This handoff is **input** to that session:
- The forward-announcement norm is the ongoing behavioral fix
- The new session produces the one-time catch-up routing table
- Together they mean: stuck work gets unstuck now, and future work doesn't get stuck

---

## What NOT to build

- No PLANNING-PROTOCOL.md rewrite
- No doctor check for arc classification
- No new file format or template beyond the four-line block
- No automation that routes between agents — just clear announcements
- No change to the VERIFY system itself (it works when someone invokes it)

---

## Acceptance criteria

- [ ] Models end every phase with forward announcement (next step + next lane + easiest view)
- [ ] "See my work" is always one link/command/path — not a scavenger hunt
- [ ] Open PRs currently stuck between stages get unstuck by the catch-up triage
- [ ] Ryan is not the default router for every agent-to-agent transition
- [ ] Trivial work scales down naturally (one sentence is fine for small things)

---

## Related files

| What | Path |
|------|------|
| Team Charter (lane assignments) | `docs/inter-model/TEAM-CHARTER-2026-07-06.md` |
| LATEST.md (stuck-work evidence) | `docs/inter-model/LATEST.md` |
| Planning Protocol (workflow, unchanged) | `docs/PLANNING-PROTOCOL.md` |
| Verify Planning (fires when invoked) | `docs/planning/VERIFY-PLANNING.md` |
| Execute Task (where forward-announce fits) | `docs/planning/EXECUTE-TASK.md` |

<!-- Original diagnosis: worktree cleanup had 3 plan reviews, 0 verification.
     Root cause simplified: models don't announce forward. Fix: say what's next,
     who does it, and show the easiest path to see the work. -->
