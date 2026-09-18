# Ingest cost diagnosis — why DeepSeek spend spiked, and what was actually wrong

**Date:** 2026-09-17
**Author:** Claude (ad-hoc, no arc)
**Status:** Findings record. Actions taken are tracked in the two handoffs linked below.

**Why this file exists:** Track A cannot record a Claude session — no Claude
Code adapter exists, so `convmem index --file <claude transcript>` ingests
nothing. This document carries the reasoning that would otherwise be lost. It is
an `inter_model_doc`, so it is indexed through a working adapter on local
Ollama embeddings at no provider cost.

---

## The question

Why did DeepSeek appear cheaper "last week"? A prior diagnostic attributed it to
a billing-window boundary plus `convmem index` lacking an incremental cursor,
and proposed enabling `[index.incremental_jsonl]` as the lever.

## What the measurements actually showed

The proposed lever was wrong, and two of the supporting figures did not hold.

**1. The incremental route cannot touch either hot file.** It is hard-scoped to
one adapter — `ELIGIBLE_FORMAT = "jsonl_kiro_session"` (`incremental_jsonl.py:42`),
with `:526` raising `IsolationViolation` otherwise. Neither `~/.codex/history.jsonl`
nor the Codex rollout is a Kiro session. Enabling the flag would have changed
nothing about the bill, and it is a Ryan-only gate under Arc Codex besides.

**2. The "612x duplication / 127 unique" figure did not hold.** Of 77,871
exported units from `history.jsonl`, 77,871 had unique ids and 77,804 unique
`title+summary` pairs. Each re-index produces *new, non-identical* summaries, so
dedupe can never collapse them. The cost claim survived; the
duplication-by-identity claim did not. This is the worse version of the problem.

**3. The dominant cost term, measured:**

| Measure | Value |
|---|---|
| Active Chroma units from `~/.codex/history.jsonl` | **44,770 of 79,566 — 56% of the serving corpus** |
| That file | 6.3 MB, **3,281 lines**, prompts-only |
| Paid calls per single touch | 66 chunks x 2 = **132** |
| Codex rollouts already indexed (full sessions) | **462 files, 18,639 units** |
| Provider failures since 2026-09-15 | history.jsonl **1,434** · rollout 81 · cursor 4 |

`history.jsonl` was ~94% of provider traffic, and its content was already
covered by 462 rollout transcripts.

## The trap that nearly caused a regression

Watch observers are recursive (`watch.py:445`). `~/.codex/history.jsonl`'s
**parent** `~/.codex` was the only thing putting all 462 Codex rollouts under
watch — `~/.codex/sessions` was not in `[sources].paths`. Deleting the
`history.jsonl` entry would have silently stopped Codex session indexing
entirely. The entry was **replaced** with `~/.codex/sessions`, which preserves
rollout coverage and narrows the observed root.

## The larger defect, found only by checking spawn distribution

Ranking by corpus share found the cost term but missed the waste term. Spawn
counts told a different story: `history.jsonl` was 95 of 6,352 index spawns,
while nine `docs/inter-model/*.md` files were ~715 spawns *each*.

Cause: `watch_skip_reason` returned `None` as soon as the **path**-keyed hash
differed, short-circuiting before the **content**-hash check eight lines below.
`ingest.py:1219` gates on content hash alone. The two disagreed.

What armed it: all nine files had their current content hash already in
`processed.json`, recorded under a **Copilot session-state audit copy** of the
same repo tree.

```
key 5c4eb9d6  path .../convmem/docs/inter-model/README.md          <- stale
key 1473ba1d  path ~/.copilot/session-state/.../audit-b2735c4a/... <- current content
```

Watch therefore spawned a full systemd scope + interpreter + Chroma import for a
file ingest would immediately skip — ~1,900 wasted spawns/day. A sweep of all
2,045 live processed entries found exactly **9** files in this state, matching
the journal precisely. Any duplicated tree arms it.

### Upstream cause: the repo watches copies of itself

The duplicate content was not incidental. `~/.copilot/session-state` is a watch
root, and **six convmem git worktrees currently live inside it**
(`git worktree list | grep .copilot/session-state`). Copilot audit runs place
full checkouts of the repository into a directory convmem indexes, so
`docs/inter-model/*.md` from those copies are ingested as `inter_model_doc`
records under Copilot paths. That is exactly how `README.md`'s content hash came
to be stored under `audit-b2735c4a`.

This is a standing generator, not a one-off: every audit worktree creates a
fresh set of duplicate-content records. The skip-logic fix makes the duplication
harmless to watch, but the underlying arrangement — an indexed root containing
checkouts of the indexed project — remains and deserves a decision of its own.

These spawns cost no provider calls: `inter_model_doc` ingest uses only local
Ollama embeddings, which is why the markdown storm logged zero provider
failures while burning CPU.

## The 900-second timeouts were not about file size

100% of index-subprocess timeouts in the retained journal window were
`history.jsonl`. The cause was not volume but retry sleep: a dead provider made
each chunk fail twice with 5s then 10s backoff, so ~66 chunks x ~15s exceeded the
900s ceiling before the file could finish. Fixing the retry policy, not the
timeout, is what removes it.

## Two silent failures found while fixing the above

- **`index --file` reported success for work it did not do.** A file no adapter
  recognizes printed `files_processed=0` and exited **0**. This is the mechanism
  behind Track A's silence: `CLAUDE.md` instructs every Claude session to run
  `convmem index --file <its transcript>`, no Claude adapter exists, and every
  such handoff has ingested nothing while reporting success.
- **A 402 has no fallback.** `llm.py:45` selects DeepSeek when the API key is
  *present*; the local fallback is keyed on the key being **absent**, not on the
  call failing. An exhausted balance is therefore a hard error per chunk, not a
  graceful degrade.

## Corrections made to this session's own claims

Recorded because the pattern matters more than the individual errors.

1. **"Problem solved" after the exclusion** — wrong. Ranked by corpus share
   without checking spawn distribution, which is where the larger defect lived.
2. **"No regressions, 188/244 tests pass"** — those were *targeted* sweeps
   allowed to stand in for the full suite. The full suite showed **53 failed /
   2,483 passed** on the branch against **2 / 108** on `main` for the same files.
3. **Two digests reported mislabeled** and captured at a different commit than
   claimed.

The common failure: measuring a convenient subset and generalizing. The
R2b rebind handoff encodes a countermeasure — a full-suite run plus an explicit
`main` baseline, with a note that the baseline was never measured and must be
produced rather than assumed.

## Why the branch is red, and why the author did not fix it

R2b binds an authority-content digest over governed writer / proof / lease /
route-entrypoint modules (`eval_corpus/r2b_v2/coverage/inventory.py:293`), so
editing `ingest.py` or `convmem.py` at all invalidates it. Separately a governed
Chroma ctor site shifted `convmem.py:640` -> `:655` (byte-identical code).

Regeneration is routine maintenance — `d14f8a6`, `ef4a7dd`, `5c103aa`,
`a91bb28`, `8983a6f` all do it. What is not routine is the author of a change
regenerating the digest that attests to it. The harness independently refused
the action as a security-control modification. Both point the same way, so it
was handed off rather than self-attested.

## Verified production outcome

Independent of the test suite:

| Measure | Before | After |
|---|---|---|
| Index spawns | 760 in 15.6 h (~49/hr) | 1 in 5 min |
| Provider failures | ~750/day | 0 |
| Files stuck re-spawning | 9 | 0 |

Positive control: the one spawn after the fix was a genuinely new Codex rollout,
indexed normally — confirming the change does not suppress real work.

## Open decisions (Ryan)

1. Purge the 44,770 `history.jsonl` units, or leave them serving. Real content,
   not literal duplicates.
2. `llm.py` fallback-on-provider-error **vs** the fail-fast shipped here. These
   are alternatives; adopting both is incoherent.
3. Whether Claude transcripts belong in the corpus at all, and separately
   whether `~/.claude/projects` is ever wired to watch.
4. Four dependabot vulnerabilities (2 critical, 2 high) on the default branch.
5. `_SKIP_SCAN_PREFIXES` (`inventory.py:305`) skips `.worktrees/` but not
   `.claude/`, so Claude Code's worktree isolation silently poisons the R2b
   ctor/sink scan with a duplicate repo copy. Confirmed live: 82 of 83 scanned
   sites came from one agent worktree. Needs an owner.

## Related

| What | Path |
|---|---|
| R2b rebind (next step) | `CURSOR-2026-09-17-r2b-inventory-rebind-handoff.md` |
| Claude adapter | `CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` |
| Correctives branch | `fix/2026-09-17-watch-skip-hash-parity` @ `daa0159` |
