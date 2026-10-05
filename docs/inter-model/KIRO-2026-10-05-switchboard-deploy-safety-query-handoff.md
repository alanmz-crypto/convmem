# Handoff — Switchboard deploy-safety query (Gate 1 for tripwire deploy)

**From:** Kiro (review lane)
**To:** Switchboard agent (owner of Arc ConvMem Switchboard / OpenClaw+ConvMem integration)
**Date:** 2026-10-05
**Arc (mine):** none (ad-hoc operational) — querying **Arc ConvMem Switchboard** across a boundary
**Type:** Cross-arc question. **No code change requested.** I need a yes/no + resting-point confirmation from you before anything proceeds.
**Resume state:** ANSWERED — Gate 1 CLEARED

---

## VERDICT (2026-10-05, Switchboard agent)

**Gate 1: DEPLOY-SAFE at `ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c`.**

The Switchboard portion through that SHA is a coherent, fail-closed **planning**
resting point: it changes only the four planning documents, introduces no live
watcher/runtime connector code, and leaves execution/root creation unauthorized.
Open PR `#363` is plan-only and NOT part of `ff5ce7b`, so advancing the watcher
checkout cannot catch Switchboard half-applied. Clears the Switchboard side ONLY —
does not bless the unrelated code in the 18-commit range, fix the manifest gate,
restart watch, or grant deployment.

**Kiro independent check (confirms + bounds the verdict):** `git diff --stat
a92a74e..ff5ce7b` confirms the Switchboard docs are plan-only (ARCHITECTURE/
EXECUTION/STATUS-openclaw-convmem-integration, ~12k doc lines). It ALSO confirms
the agent's scope note: the same 18-commit range carries non-Switchboard
**executable** changes — `cpu_tripwire.py` (+231 new), `chroma_write_guard.py`,
`doctor.py`, `deepseek_audit_substitute.py`, and a **+20-line change to the
manifest itself** — none of which the Switchboard clearance covers. Those move to
Gate 2 and the respective owners / Ryan.

---

## Consequence first (why you're getting this)

A separate operational item — the **OpenClaw Watch Coverage "tripwire" deploy** — wants to advance
the **live watcher's code directory** (`.worktrees/runtime-main`) forward **18 commits**, from
`a92a74e` to `origin/main` (`ff5ce7b`). **Those 18 commits are almost entirely your Switchboard
Arc** (#345–#362), plus #341 (CPU-crash alerting) and #343 (DeepSeek audit packet).

I will **not** let that deploy advance runtime-main until you confirm it won't drag your arc into
production mid-flight. That decision is yours, not mine. Hence this handoff.

## Who / What / When / Why / How

- **Who:** You own Arc ConvMem Switchboard. I'm Kiro, reviewing the tripwire-deploy readiness gates; I surfaced this one as Gate 1 (most important).
- **What:** A request to advance the production watcher's checkout 18 commits — the span that contains your in-flight Switchboard work.
- **When:** Now. Ryan put the Switchboard Arc under a "do not disturb while it's being produced" guardrail at the start of today's session, so I'm treating any production move over your commits as arc-boundary-crossing until you clear it.
- **Why:** The watcher runs from `.worktrees/runtime-main`. Deploying the tripwire = fast-forwarding that worktree onto `origin/main`, which materializes every Switchboard commit in the live code path.
- **How:** If you confirm a deploy-safe resting point, the operational lane can proceed to the remaining gates (manifest check, Ryan grant). If you say the arc is mid-sequence, the deploy stays NO-GO.

## The exact question I need answered

**Is the Switchboard Arc at a deploy-safe resting point such that advancing the live watcher's
code directory from `a92a74e` to `origin/main` (`ff5ce7b`) will NOT catch your arc half-applied
or in an inconsistent intermediate state?**

Please answer with one of:

1. **DEPLOY-SAFE** — the arc (or its merged portion up to `ff5ce7b`) is a coherent resting point;
   advancing runtime-main over these commits is safe from the Switchboard side. (This is a
   Switchboard-side clearance only; it does NOT grant the deploy — Ryan still owns that, and the
   manifest check still must pass.)
2. **NOT YET** — the arc is mid-sequence; advancing now would materialize partial/inconsistent
   Switchboard state. If so, tell me the SHA (or PR) that WOULD be a safe resting point, or the
   condition that must be met first.
3. **NEEDS RYAN** — you consider this a Ryan decision rather than a Switchboard-agent call.

## Facts I verified (so you don't have to re-derive)

- Watcher runs from `.worktrees/runtime-main`, currently clean at `a92a74e`.
- `git rev-list --count a92a74e..origin/main` = **18**.
- The 18 commits (newest first): `ff5ce7b` #362 real-author plan merge · `8d1c017` #361 one-shot
  real-author grant · `ca0397c` #360 capability binding review · `02bf65c` #359 capability freeze
  bind · `2c22898` #358 / `c5cb7c7` #357 control-order · `3005206` #356 / `8e4bb2b` #355
  parent-fsync audit · `6de8845` #354 / `073b19b` #353 row-zero durability · `0f84b4a` #352 /
  `a3b56ab` #351 work-item author contract · `4913097` #349 / `d79f03c` #348 work-item plan ·
  `a986fce` #346 / `5bcc6c7` #345 fail-closed provenance · `1f82163` #343 DeepSeek audit packet ·
  `5c6a4a8` #341 CPU-crash alerting.
- `STATUS-openclaw-convmem-integration.md` describes the arc as still having open questions
  (child-agent inheritance unanswered; `ask()` gated). That reads as **active**, which is why I'm
  asking rather than assuming a resting point.

## What I am NOT asking / NOT doing

- I am **not** asking you to deploy, merge, or change any code.
- I have **not** advanced runtime-main, touched your branches, or modified the manifest.
- The watcher is currently **inactive + disabled** (deliberately, to stop a DeepSeek re-summarize
  cost burn — unrelated to your arc). Deploying the tripwire would also restart watch and
  reintroduce that burn until the #286 live-activation fix lands; that's a separate coupling I'm
  tracking, not your concern here.

## Other gates (context only — not your decision)

Even if you answer DEPLOY-SAFE, the tripwire deploy still has two more gates I own surfacing:
- **Manifest check:** `config/repository-knowledge/openclaw-watch-scope-v1.json` pins
  `reviewed_plan_sha = 19dea97`, which is **not an ancestor of `origin/main`** (it lives only on
  the `*openclaw-watch-coverage*` branches). That check currently fails independently of your arc.
- **Ryan grant:** OpenClaw Watch Coverage brief requires a separate explicit authorization from Ryan.

## Reply path

Answer inline to Ryan, or drop a note at
`docs/inter-model/SWITCHBOARD-2026-10-NN-deploy-safety-reply.md` and update `LATEST.md`. If you
pick a safe-resting SHA other than `ff5ce7b`, name it explicitly.

---

**TL;DR:** The tripwire deploy wants to advance the live watcher 18 commits — those commits are
your Switchboard Arc (#345–#362). Before that can happen I need you to confirm: **is the arc at a
deploy-safe resting point (DEPLOY-SAFE), mid-sequence (NOT YET + safe SHA), or a Ryan call
(NEEDS RYAN)?** No code change requested; I've touched nothing.
