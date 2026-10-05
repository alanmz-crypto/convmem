# Assignment brief — can an agent own Gate 2 to done? (for Ryan)

**From:** Kiro (review lane)
**To:** Ryan (assignment decision)
**Date:** 2026-10-05
**Purpose:** Help you decide whether to assign an agent to take **Gate 2** (OpenClaw watch-scope
manifest reconciliation) all the way to done — and if so, scope exactly what that agent owns, what
authority they need, and what "done" means. This is a *staffing* brief, not the reconciliation
handoff itself (that is `KIRO-2026-10-05-gate2-manifest-reconcile-handoff.md`).

---

## The one-paragraph picture

The OpenClaw Watch Coverage **tripwire deploy** is held by three gates. Gate 1 (Switchboard arc
safe) is **cleared**. Gate 3 (your deploy grant) is **withheld** behind Gate 2. **Gate 2 is the
only live blocker, and it has no active owner.** Gate 2 is: the live watcher's scope manifest pins
a reviewed-plan SHA that does not exist in the deploy target's history, so the manifest must be
reconciled before the deploy can be coherent. That reconciliation is a judgment call owned by Arc
OpenClaw Watch Coverage — which currently has nobody on it. You are deciding whether to put an
agent there.

## What the assigned agent would own (full scope of "all the Gate 2 work")

1. **Decide the reconciliation path** for `config/repository-knowledge/openclaw-watch-scope-v1.json`,
   whose `reviewed_plan_sha = 19dea97…` is NOT an ancestor of the deploy target. Two candidate paths
   (agent may propose a third):
   - **Path A — merge the reviewed plan into main.** Bring `19dea97` ("fix watch routing and Gate W
     boundary", on the unmerged `*openclaw-watch-coverage*` branches) into main so the existing pin
     resolves. Requires reviewing/merging that plan branch.
   - **Path B — re-pin to a reviewed ancestor.** Change `reviewed_plan_sha` to a SHA that IS an
     ancestor of the deploy target AND is a genuinely reviewed plan for the current coverage. A bare
     re-pin without real review behind it defeats the gate.
2. **Produce the change** (branch, manifest edit or plan merge, tests/validation that the scope +
   Git-clean checks still pass per the arc brief's design) — Execute lane work, not review lane.
3. **Prove it:** show the manifest's `reviewed_plan_sha` resolves into the deploy target and the
   repository-knowledge coverage validates (scope limits, exclusions, no dirty/unlisted bytes).
4. **Hand to Ryan** for merge + the Gate 3 deploy grant. The agent does NOT self-merge or deploy.

## Skills / lane the candidate needs

- Execute-capable (writes code/config, runs validation) — this is implementation, so **not** Kiro
  (review-required) and **not** the Switchboard agent (disclaimed ownership; different arc).
- Must be able to make a **reviewed-plan judgment** (which SHA is the correct reviewed baseline),
  not just a mechanical git edit — Path B is unsafe if done blindly.
- Comfortable in the OpenClaw Watch Coverage arc's safety model (hash-pinned scope manifest,
  fail-closed validation, no-LLM repository chunker). Per the HITL charter this is implementation →
  typically **Cursor** (Execute), optionally with design input, and Ryan merges.

## Authority boundaries (what the agent may NOT do)

- May NOT advance `.worktrees/runtime-main`, restart watch, or deploy — those are Gate 3 / Ryan.
- May NOT grant itself the deploy or merge to main — Ryan owns merges.
- May NOT bless or re-scope the non-Switchboard code in the deploy range (cpu_tripwire.py,
  chroma guard, doctor, deepseek audit) — that is separate review, not Gate 2.
- Must keep the watcher **inactive + disabled** (DeepSeek burn mitigation) — Gate 2 work is static
  (git/manifest), it does not require a running watcher.

## Definition of done (so you can tell when the agent is finished)

- `git merge-base --is-ancestor <manifest reviewed_plan_sha> <deploy target>` returns **YES**.
- The reviewed plan behind that SHA is genuinely reviewed (not a bare re-pin).
- Repository-knowledge validation passes against the deploy target.
- A PR is open for Ryan with the manifest reconciled; Gate 2 marked PASS in LATEST.
- Gate 3 (Ryan grant) and the deploy itself remain untouched — explicitly out of scope.

## Current facts (verified 2026-10-05, re-check at pickup)

- Watcher: **inactive + disabled** (intentional, burn mitigation).
- `.worktrees/runtime-main` HEAD: `a92a74e` (clean).
- Manifest `reviewed_plan_sha`: `19dea97368408ee0b179c05c942306f6d8f1a2e8` — **NOT** an ancestor of
  `origin/main`; lives only on the four unmerged `*openclaw-watch-coverage*` branches
  (`plan/`, `feat/`, `fix/`, `docs/` 2026-09-21).
- **Deploy target moved today:** `origin/main` tip is now `0a250b1` ("Correct the Switchboard
  unresolved-ID grammar before retry (#363)"), one commit past `ff5ce7b`. `ff5ce7b` is still an
  ancestor of `0a250b1`.
  - **Gate 1 caveat:** the Switchboard agent cleared DEPLOY-SAFE **at `ff5ce7b`** and said #363 was
    plan-only and not part of `ff5ce7b`. If the deploy now targets `0a250b1`, Gate 1's clearance
    should be re-confirmed for the new tip (expected trivial — #363 is the same plan-only arc work —
    but it must be stated, not assumed). The Gate 2 agent does not own this; flag it to Ryan.

## Related docs

- Gate 2 reconciliation handoff (the actual task spec): `KIRO-2026-10-05-gate2-manifest-reconcile-handoff.md`
- Gate 1 verdict + ownership boundary: `KIRO-2026-10-05-switchboard-deploy-safety-query-handoff.md`
- Routing: `LATEST.md` top bullets
- Arc brief: `docs/plans/STATUS-openclaw-watch-coverage.md`

---

**TL;DR:** Gate 2 (watch-scope manifest reconciliation) is the tripwire deploy's only live blocker
and has no owner. An assignable agent would: pick a reconciliation path (merge reviewed plan
`19dea97` into main, or re-pin to a reviewed ancestor of the deploy target), produce + validate the
change, and hand a PR to you — **without** deploying, restarting watch, or self-merging. Needs an
Execute-capable agent with reviewed-plan judgment (charter default: Cursor), not Kiro and not the
Switchboard agent. Note the deploy target moved to `0a250b1` (#363) today, so Gate 1's `ff5ce7b`
clearance needs a quick re-confirm for the new tip.
