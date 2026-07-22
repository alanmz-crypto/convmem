# Architecture: Semantic dedupe / queue hygiene

| Field | Value |
|-------|-------|
| Status | Proposed — Ryan GATE before live mutation |
| Owner | Ryan owns config + approve gates; Cursor plans/implements code; Kiro reviews batches when asked |
| Scope | Corpus-maintenance track for `dedupe_queue.jsonl` backlog + job/config alignment |
| Decision | Pause uncontrolled growth, banded Ryan-gated drain, no auto-merge |

## Problem

After F1 (2026-07-01) the semantic dedupe queue was drained and LATEST recorded
`semantic_dedupe` **out of daemon jobs** until growth warranted re-queueing. Live
reality (2026-07-22) diverged:

| Fact | Value |
|------|-------|
| `~/.local/share/convmem/dedupe_queue.jsonl` | ~1167 lines; **~1157 pending** |
| Status mix | 9 historically approved, 1 `rejected_keep_both`, rest pending |
| Similarity bands (pending) | ~143 at 1.000; ~57 in 0.98–0.999; ~240 in 0.95–0.98; ~717 in 0.92–0.95 |
| Exact title match pairs | ~194 |
| Live `[refine].jobs` | still includes `semantic_dedupe` |
| Refine daemon | **pauses** when queue depth ≥ `queue_max_depth` (200) |
| Ingest path | `ingest_dedupe.persist_ingest_dedupe` **keeps appending** (`source: ingest`) with **no** depth pause |

So the backlog grows from **watch/index**, not from the paused refine job. Leaving
1157 unreviewed pairs is corpus debt; blind `--approve-dedupe all` risks wrong
tombstones. P1.3 soak also showed Kiro **session-snapshot** steering copies
crowding top-N — related noise, not the same as semantic queue drain.

This arc is the parked who-fixes / P1.3 follow-up: a **separate corpus brief**,
not ranking work.

## Decision

Run a three-phase hygiene arc:

1. **Stop the bleed (ops + small code)** — Align live refine jobs with F1 policy
   (drop `semantic_dedupe` from daemon jobs). Add the same `queue_max_depth`
   pause to **ingest** semantic enqueue so watch cannot unbounded-grow the
   queue while a backlog exists.
2. **Banded review (Ryan-gated)** — Classify pending rows; drain high-confidence
   bands first (identical titles @ ~1.0, then ≥0.98) with sample review — never
   silent full `all` on first pass.
3. **Optional Phase D (separate or later)** — Snapshot-path steering crowding
   (exclude or supersede `.kiro/sessions/**/snapshots/**/.kiro/steering/`
   duplicates favoring GitClones paths). Out of Phase A–C unless Ryan expands
   scope.

No auto-merge. `--approve-dedupe` remains the only apply path. Undo snapshots
under `refine_undo/semantic_dedupe/` stay required.

## Required rules

**Rule 1 — No bulk tombstone without sample.** Before any `--approve-dedupe all`
or large line-range apply, Ryan (or named reviewer) must see a band summary and
a sample of ≥10 rows from that band. First apply batches are small (≤50) unless
Ryan explicitly widens.

**Rule 2 — Config and corpus mutation are Ryan-owned.** Agents may edit repo
`config.example.toml` and code; they must **not** silently rewrite
`~/.config/convmem/config.toml` or run `--approve-dedupe` unless Ryan asked in
the same turn.

**Rule 3 — Ranking stays frozen.** No `source_trust`, postfilter, diversification,
or rerank changes in this arc.

## Non-goals

- Auto-merge or LLM-only merge without queue status change
- Evidence-inject / ask evidence-budget work
- Full corpus reindex, forget, or R2a/R2b
- Changing `dedupe_similarity` threshold without a measured false-positive note
- Closing staging2 header unresolveds

## Residual risk

- High-similarity pairs can still be distinct facts (false merge).
- Pausing ingest enqueue hides new candidates until depth drops — accepted while
  draining; document when to re-enable.
- Snapshot steering noise may remain until Phase D.

## Acceptance

- Live refine jobs match documented policy (no idle `semantic_dedupe` while
  backlog ≥ `queue_max_depth`, or Ryan records an explicit exception).
- Ingest semantic append respects `queue_max_depth` (or equivalent pause flag).
- Pending count materially reduced via reviewed applies; remaining backlog has
  a written band plan.
- VERIFY plan filled; no ranking golden updates.
- LATEST / standing register reflect arc state.
