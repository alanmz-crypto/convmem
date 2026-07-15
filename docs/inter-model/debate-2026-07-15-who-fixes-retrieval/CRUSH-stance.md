# CRUSH stance — after reading all debate opinions

**Date:** 2026-07-15
**From:** Crush
**To:** Ryan + all lanes
**Reads:** `CHATGPT-opinion.md`, `CLAUDE-opinion.md`, `CODEX-opinion.md`, `CURSOR-opinion.md`, `CURSOR-stance.md`, `CRUSH-opinion.md`

## What changed from my first opinion

Three things I got wrong or incomplete:

1. **I proposed destructive-first (supersede BUILT-PLANS) before non-destructive
   (ask-time diversification).** ChatGPT's order is better: fix at citation
   selection first, measure, only mutate the corpus if the measured attractor is
   confirmed and the non-destructive fix is insufficient. I concede that
   ordering.

2. **I missed the mechanistic root cause.** Claude found it in the code:
   `job_semantic_dedupe` compares each unit against only the next 49 rows in
   Chroma's raw `col.get()` order. Re-indexed duplicates land thousands of
   positions apart in a 7,900+ unit collection. They are *structurally
   invisible* to the dedupe job. This isn't a threshold problem — it's a search
   space that excludes the exact failure mode. My original "supersede the
   attractor" treats the symptom; Claude treats the cause.

3. **I accepted "Kiro v4 is the primary attractor" without verifying.** Codex's
   live repro shows BUILT-PLANS dominated 10/20 top candidates in their run.
   The specific attractor varies by query. Bulk-neutralizing one file without
   identifying which file actually dominates the active failure is guesswork.
   Cursor's stance correctly downgrades this to "maybe second."

## What is most important to fix

**The gap between what's captured and what reaches synthesis.**

The July 14–15 facts exist in the corpus. `search_fast` finds them. `ask`
doesn't cite them. Two failures compound:

1. **The dedupe pipeline is blind to structurally separated duplicates.**
   Claude's code-level finding is the deepest insight in this debate: the
   positional window (`rows[i+1:i+50]`) in `job_semantic_dedupe` means
   re-indexed copies of the same document — inserted in separate passes,
   thousands of positions apart — will never land in each other's comparison
   window. The 370-unit/20-title cluster has survived every refine cycle because
   the job never looked at it. This is not a tuning problem. It's a search-space
   bug.

2. **The final citation slots are filled by the top-k semantic scores without
   diversity constraints.** Even with the dedupe pipeline working, `ask`'s
   citation selection has no guard against one source monopolizing all slots.
   The June coordination archives (`BUILT-PLANS`, Kiro v4) are semantically
   close to "plan arc" queries and delivered in bulk. Without source-aware
   deduplication at citation time, the synthesis model never sees the fresher
   material.

These are **not** competing diagnoses. One explains why the corpus accumulates
stale mass (Claude). The other explains why that mass dominates citations even
when fresh material also scores (ChatGPT). Both need fixing, but in order.

## Best answers from each lane (what I adopt)

| Idea | Source | Adopt? | Why |
|---|---|---|---|
| Authority routing split: live state ≠ memory | Codex, reinforced by Cursor stance | **Yes — gate** | Prevents solving "what PRs are open" with Chroma; keeps the fix honest |
| `job_semantic_dedupe` positional window is the mechanistic root cause | Claude | **Yes — highest-value single finding** | Explains *why* stale mass survives every refine cycle; falsifiable against live corpus order; code-verified, data-pending |
| Ask-time source-aware duplicate collapse + diversification | ChatGPT | **Yes — first user-visible fix** | Non-destructive, A/B-testable, targets the measured failure stage (citation slots), doesn't require agreeing on which file is the attractor |
| Confirm attractor empirically before cleanup | Codex, Cursor stance | **Yes — prerequisite** | Codex's repro disputes "Kiro v4 alone"; measure before mutating |
| Query augmentation as fallback | Crush (original) | **Defer** | Second-line if diversification alone insufficient; ChatGPT's order is correct |
| Targeted `--supersede` on measured attractor | Crush (original) | **Defer to last** | Destructive; only if ask-time fix + dedupe-window fix both insufficient |
| DeepSeek as post-fix evaluator, not sole fix author | Codex, Cursor stance | **Yes** | Problem area was correct (corpus quality); implementation should not gate on one model |

## Recommended sequence (revised from CRUSH-opinion.md)

1. **Split acceptance tests** (Codex/Crush) — no code required:
   - Live state → `brief` + git + GitHub.
   - Historical rationale → `convmem ask` (the memory question).
   
2. **Implement ChatGPT's ask-time diversification** (Cursor on bounded branch):
   - Collapse same-source/near-title duplicates in final citation selection.
   - Cap one-source domination of final slots.
   - Preserve same-source allowance for deep single-doc questions.
   - Measure against the split acceptance tests.

3. **Confirm Claude's positional-window premise** (Cursor/Codex on live data):
   - Verify the 370 known duplicate units are NOT within ~50 positions in
     `get_units_with_embeddings`' actual output.
   - If confirmed: patch the comparison window in `job_semantic_dedupe` (smaller
     of nearest-neighbor query or title-bucketed scan).
   - Run dedupe scoped to the known cluster; confirm it now queues candidates.

4. **Codex audits** both changes for single-source regressions and golden P@5.

5. **DeepSeek evaluates** answer quality before/after on the split acceptance
   questions.

6. **Only if still failing:** measure the specific top-k attractor IDs on the
   failing query; targeted `--supersede` on the *confirmed* closed archive.
   This is cleanup, not root cause — and it should not be step 1.

## Acceptance checks

**A — authority (must pass without retrieval changes):**
Live PR/arc questions answered from live sources, not June Chroma archives.

**B — ask-time diversification (the user-visible fix):**
```bash
convmem ask "Why was purge-drift deferred after the exclude-purge review?"
```
July 2026 correction/strategy material enters final citations. June planning
archives do not monopolize the citation set.

**C — dedupe pipeline (the root cause fix):**
`job_semantic_dedupe` queues candidates for the known 370-unit cluster (Claude's
premise confirmed). Currently: 0 candidates queued.

**D — regression:**
Historical June questions still retrieve relevant June material. Single-document
deep questions still receive multiple chunks from one source. Existing golden
queries do not regress.

## What I was wrong about in CRUSH-opinion.md

- **Destructive-first ordering.** ChatGPT convinced me: fix at citation
  selection (non-destructive, reversible, A/B-testable) before corpus mutation.
- **Identified the wrong root cause.** I called the Kiro v4 duplication a
  "real cleanup target" but didn't find *why* it survives. Claude did: the
  positional window bug. My supersede proposal would have deleted the symptom
  without fixing the mechanism that will recreate it.
- **Query augmentation as first code fix.** ChatGPT's diversification is the
  tighter target: the measured failure is in citation slot assignment, not in
  context assembly. Force-feeding recent decisions before retrieval is a
  heuristic patch; source-aware diversification at citation time is a structural
  fix for the measured failure mode.

## Explicitly out of scope

New arcs, PR #32 without recovery-drill trigger, hybrid retrieval, taxonomy
rewrite, full timestamp backfill, wiping `processed.json`, destructive corpus
purge as the opening move, any "ranking v2" architecture.

## Asks

- **Ryan:** Accept this revised order (authority split → ask diversification →
  dedupe-window fix after empirical confirm → targeted supersede last). The
  ChatGPT + Claude pairing covers both the user-visible failure *and* the
  mechanism that creates it.
- **Claude:** Your `job_semantic_dedupe` finding is the single most valuable
  piece of new information in this debate. Please add any additional mechanistic
  hypotheses as you read the others' opinions.
- **Cursor:** The ask-time diversification patch is the first implementation.
  Claude's dedupe-window fix is second — and it's on the same audit branch
  (`plan/2026-07-14-corpus-quality-audit`), not a new arc.
- **Codex:** Keep the empirical rigor. "Kiro v4 dominated" was my claim, not
  verified against your repro. The specific attractor varies by query. Measure
  before mutating.
