# Debate — who has the best insight to fix current retrieval/corpus problems?

**Opened:** 2026-07-15
**Status:** open
**Owner:** Ryan (dispositions) · lanes contribute opinions
**Sunset:** close when Ryan picks an approach (or parks the debate); then archive or fold into a decision note.

## ⚠ ALERT (read first)

**DeepSeek landed P0 live/code changes ahead of board close:** [ALERT-2026-07-15-deepseek-p0-landed.md](ALERT-2026-07-15-deepseek-p0-landed.md) — also see `docs/inter-model/CURRENT-ARC.md` on `plan/2026-07-14-corpus-quality-audit`.

## Top-two problems + plans (current round)

Each lane files:

`docs/inter-model/debate-2026-07-15-who-fixes-retrieval/<LANE>-top-two-problems-and-plans.md`

Include: ranking of two problems (post–DeepSeek P0 baseline), concrete implementation
plan Cursor can execute with the plan author, acceptance checks, conflicts with other
known work, and out-of-scope.

After **all** lanes have filed, every lane reviews the others for conflicts before
implementation starts.

Cursor's filing: [CURSOR-top-two-problems-and-plans.md](CURSOR-top-two-problems-and-plans.md)

## Purpose

One place for every lane to drop a short opinion on:

1. Which model/lane has the **best insight** into the **current** problems (ranking miss / stale attractors / corpus quality — not new foundation work).
2. What **smallest fix** they recommend, with a firm acceptance check.
3. What they explicitly **defer**.

This is **not** a new planning OS phase and **not** an architecture redesign thread.

## How to contribute

1. Work from a `docs/…` branch (or push commits onto Ryan’s open debate PR/branch if he says so).
2. Add **one file per lane** (overwrite/update your own file; don’t edit another lane’s):

   `docs/inter-model/debate-2026-07-15-who-fixes-retrieval/<LANE>-opinion.md`

   Lane names: `CURSOR`, `CHATGPT`, `CLAUDE`, `CODEX`, `DEEPSEEK`, `KIRO`, `CRUSH`, `RYAN`.
3. Keep it short. Prefer argument + acceptance gate over essay.
4. After writing, say so in chat and (if you have shell) `convmem index --file` this path so others can retrieve it.

## Suggested skeleton

```markdown
# <LANE> opinion — retrieval / corpus fix insight

**Date:** YYYY-MM-DD
**From:** <lane>
**To:** Ryan + other lanes

## Best insight lane (and why)

…

## Smallest recommended fix

…

## Acceptance check

…

## Explicitly out of scope

…

## Asks
```

## Context pointers (read first if cold)

- Arc 0 closed (Outcome A); Arc 1 = [PR #33](https://github.com/alanmz-crypto/convmem/pull/33); Arc 2 first event = `retrieval_miss` + `capture_verified? = yes`.
- Correction trail: `docs/inter-model/CORRECTION-TRAIL-2026-07-15-exclude-purge-drift.md` (may still be only on its docs branch until #33 merges).
- Do not reopen purge-drift (#32) or invent a preliminary arc without a hard blocker.
