# Handoff — Gate 2: OpenClaw watch-scope manifest reconciliation

**From:** Kiro (review lane)
**To:** OpenClaw Watch Coverage lane owner (whoever picks up Arc OpenClaw Watch Coverage)
**Date:** 2026-10-05
**Arc:** OpenClaw Watch Coverage (planning / Kiro-review-next; no confirmed active owner this session)
**Type:** Reconciliation question + blocked gate. **A change IS needed, but I did not make it** — routing to the arc owner for a decision, then Ryan review.
**Resume state:** BLOCKED_ON_OPENCLAW-LANE-OWNER

---

## Consequence first (why you're getting this)

The OpenClaw Watch Coverage **tripwire deploy** (advance the live watcher code dir
`.worktrees/runtime-main` from `a92a74e` → `origin/main` `ff5ce7b`, 18 commits) is held at
**Gate 2**. The watch-scope manifest pins a **`reviewed_plan_sha` that does not exist in the
deploy target's history**, so the watcher would come up bound to a reviewed-plan baseline that
isn't in its own tree. This gate fails **independently of the Switchboard arc** (Gate 1 is already
cleared DEPLOY-SAFE at `ff5ce7b`). It needs an owner decision before the deploy can proceed, and
Ryan has set the rule that **no gate work begins until the gate's working agent is consulted** —
hence this handoff rather than me reconciling it myself.

## Who / What / When / Why / How

- **Who:** You own Arc OpenClaw Watch Coverage (and therefore the manifest). I'm Kiro, surfacing the
  deploy readiness gates; I don't own the manifest and won't change it unilaterally.
- **What:** `config/repository-knowledge/openclaw-watch-scope-v1.json` pins
  `reviewed_plan_sha = 19dea97…`, which is unreachable from the deploy target.
- **When:** Now — this is the sole live blocker to the tripwire deploy. Gate 1 (Switchboard) cleared
  2026-10-05; Gate 3 (Ryan deploy grant) is correctly withheld until this passes.
- **Why:** The reviewed plan the manifest points at was authored on the unmerged
  `*openclaw-watch-coverage*` branches and never merged to main, so the pin dangles.
- **How:** Reconciling it (one of two paths below) makes Gate 2 pass; then Gate 3 (Ryan) becomes
  live. Deploying without reconciling would ship an incoherent reviewed-plan binding.

## The exact problem (facts I verified — do not re-derive)

- Manifest: `config/repository-knowledge/openclaw-watch-scope-v1.json`,
  `manifest_id = openclaw-watch-scope-v1`, `coverage_root = "."`.
- Pinned `reviewed_plan_sha = 19dea97368408ee0b179c05c942306f6d8f1a2e8`
  (`19dea97` "fix watch routing and Gate W boundary", 2026-09-21).
- The pin is **identical** on disk at `a92a74e` and at the deploy target `ff5ce7b` — advancing the
  18 commits does **not** change it (the manifest file is edited +20 lines in the range, but the
  `reviewed_plan_sha` value stays `19dea97`).
- `git merge-base --is-ancestor 19dea97 origin/main` → **NO**.
- `git merge-base --is-ancestor 19dea97 ff5ce7b` → **NO**.
- `19dea97` is reachable **only** from these unmerged branches (local + origin):
  - `plan/2026-09-21-openclaw-watch-coverage`
  - `feat/2026-09-21-openclaw-watch-coverage`
  - `fix/2026-09-21-openclaw-watch-coverage-refinement`
  - `docs/2026-09-21-openclaw-watch-coverage-execute-handoff`

So in both the current and post-deploy states, the watcher's scope manifest references a reviewed
plan that is not in its own branch history.

## The decision I need from you

Pick a reconciliation path (or propose a better one). **Both are real changes requiring Ryan
review — I will not perform either without the arc owner's decision and Ryan's go.**

1. **Merge the reviewed plan into the deploy target's history.** Bring `19dea97` (the reviewed
   OpenClaw watch-coverage plan) into `main`/`ff5ce7b` so the manifest's existing pin resolves.
   - Pro: keeps the manifest unchanged; the pin becomes valid.
   - Con: pulls the whole watch-coverage plan branch into main; needs its own review/merge.

2. **Re-pin the manifest to a reviewed ancestor of the deploy target.** Update
   `reviewed_plan_sha` to a SHA that *is* an ancestor of `ff5ce7b` AND corresponds to an
   actually-reviewed plan for the current coverage.
   - Pro: no plan-branch merge needed.
   - Con: requires identifying/confirming the correct reviewed SHA; a bare re-pin without a real
     review behind it would defeat the gate's purpose.

Please answer with: chosen path (1 / 2 / other), and — if path 2 — the exact `reviewed_plan_sha`
you consider correct and why it's reviewed. If you believe the manifest pin is intentional and the
*deploy itself* should be re-scoped instead, say so.

## What I verified vs. what I could not

- **Verified:** the ancestry facts above (ran `git merge-base --is-ancestor` and `git show`), that
  the pin is unchanged across the deploy range, and that `19dea97` lives only on the four branches.
- **Could NOT verify:** which plan SHA (if any) is the *correct* reviewed baseline for the current
  manifest coverage — that's a review judgment the arc owner holds, not something I can infer from
  git topology.

## What I am NOT doing

- Not editing the manifest, not merging any branch, not advancing runtime-main, not restarting watch.
- Not granting or recommending Gate 3 (Ryan's deploy grant) — it stays withheld until Gate 2 passes.
- The watcher remains intentionally **inactive + disabled** (DeepSeek burn mitigation); deploying
  would restart it and reintroduce the burn until the #286 live-activation fix lands — a separate
  coupling, flagged for awareness, not part of this reconciliation.

## Reply path

Answer inline to Ryan, or drop
`docs/inter-model/OPENCLAW-2026-10-NN-gate2-manifest-reconcile-reply.md` and update `LATEST.md`.

---

**TL;DR:** The tripwire deploy is blocked at Gate 2: the watch-scope manifest pins
`reviewed_plan_sha = 19dea97`, which is **not an ancestor of the deploy target `ff5ce7b`** (nor of
`origin/main`) and lives only on the unmerged `*openclaw-watch-coverage*` branches — unchanged by the
18-commit advance. Reconcile by either **(1) merging the reviewed plan into the deploy history** or
**(2) re-pinning to a reviewed ancestor of `ff5ce7b`**. Both need the arc owner's decision + Ryan
review; I've changed nothing.
