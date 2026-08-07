# Who-fixes-retrieval CLOSED → P1.3 inherit / dismiss

**Date:** 2026-07-22  
**From:** Cursor (closeout of debate arc `debate-2026-07-15-who-fixes-retrieval`)  
**To:** P1.3 workers (Codex implement / Cursor verify / Kiro sign / Ryan GATE)  
**Status:** Debate coordination arc **closed**. This note is inheritance only — **not** a new EXECUTION grant.

**Does not authorize:** new retrieval ranking code, `semantic_dedupe` daemon flips, diversification retunes, evidence-scoping patches, or any work outside the locked P1.3 EXECUTION / VERIFY.

---

## One breath

The July 15 “who fixes retrieval?” board ran Rounds 1–4. **Code for those rounds is already on `main`.** P1.3 source-trust is the **live** retrieval arc (VERIFY freeze → Await Ryan GATE). Use what helps; dismiss the rest. Search the cargo holds below for anything this note omits.

---

## Inherit (safe to use)

| Item | Why P1.3 might care | Where |
|------|---------------------|--------|
| Nested `docs/inter-model/**/*.md` ingest | Inter-model tier / path matching; debate material is indexable | Round 1 · PR #38 · `adapters/inter_model_doc.py` |
| `ask(trace=True)` / `convmem.ask.trace.v1` | Falsifiable stage dumps for VERIFY / regressions | Round 2 · PR #35 @ `950e830` · CLI `--trace` · MCP `trace` |
| Source-path diversification `max_per_source=2` | Already shipped citation crowding fix — **do not re-litigate as P1.3 scope** | Round 3 · PR #39 @ `549f74d` |
| `retrieve_for_ask` + `RetrievalBundle` | Parity extract; ask synthesis stays thin | Round 4 · PR #40 · `ask.py` |
| Authority split | Live state → `brief` / git / GitHub; durable rationale → `ask`. Do not treat live-state misses as ranking proof | Kiro design sign-off in debate folder |
| Trace-first rule | Ranking experiments only after a durable-rationale trace shows crowding vs recall miss | Same |

## Dismiss (do not reopen mid–P1.3)

| Item | Why dismiss |
|------|-------------|
| July 15 lane opinion / stance pile (“who should lead”) | Sequence already executed through Rounds 1–4 |
| “Ship diversification first” as open debate | Round 3 shipped |
| Round 4 docs still saying “wait for Ryan go” | Stale — #40 already on `main`; board close updates truth |
| PR #36 Cursor-after-Kiro note | Obsolete pointer; supersede/close — not current status |
| Continue-DeepSeek P0 “enable `semantic_dedupe` in refine.jobs” as P1.3 prerequisite | Separate corpus-maintenance track; not in locked P1.3 design |
| Evidence cross-project inject as P1.3 must-fix | Residual; only open if Ryan expands scope |
| Re-running Round 2–4 design debates | Closed board |

---

## Shipped round map (code truth)

| Round | Problem | Status | Anchor |
|-------|---------|--------|--------|
| 1 | Evidence minority-cap + nested inter-model | Shipped | PR #38 |
| 2 | `ask(trace)` v1 | Shipped | PR #35 @ `950e830` |
| 3 | Source diversity `max_per_source=2` | Shipped | PR #39 @ `549f74d` |
| 4 | `retrieve_for_ask` parity extract | Shipped | PR #40 |
| — | Debate board coordination | **Closed** this note | Successor = **P1.3** |

Board path (docs tip may lag until debate-close PR merges):  
`docs/inter-model/debate-2026-07-15-who-fixes-retrieval/`

VERIFY for this closed arc: [`../plans/VERIFY-who-fixes-retrieval.md`](../plans/VERIFY-who-fixes-retrieval.md)

---

## Harbor map — where to look beyond this handoff

P1.3 already has a harbor packet. This closeout adds **prior-board cargo**. Search before re-deriving.

```text
                    ┌─────────────────────────────────┐
                    │  LIGHTHOUSE                      │
                    │  docs/inter-model/LATEST.md     │
                    └──────────────┬──────────────────┘
                                   │
     ┌─────────────────────────────┼─────────────────────────────┐
     ▼                             ▼                             ▼
┌──────────────┐         ┌──────────────────┐         ┌────────────────────┐
│ P1.3 LIVE    │         │ THIS CLOSEOUT    │         │ CLOSED BOARD       │
│ packet/EXEC  │         │ (this file)      │         │ debate-2026-07-15…  │
└──────┬───────┘         └────────┬─────────┘         └─────────┬──────────┘
       │                          │                             │
       └────────────┬─────────────┴──────────────┬──────────────┘
                    ▼                            ▼
          ┌──────────────────┐         ┌─────────────────────────┐
          │ CARGO: P1.3 chat │         │ CARGO: this closeout    │
          │ 4d0fbf93-…jsonl  │         │ 566966f0-…jsonl         │
          └──────────────────┘         └─────────────────────────┘
```

### Ritual searches (copy-paste)

```bash
convmem doctor
convmem brief --stdout-only

# This closeout + inherit/dismiss
convmem "who-fixes-retrieval closed to P1.3 inherit dismiss"
convmem "VERIFY who-fixes-retrieval Rounds 1-4"

# Live P1.3 (unchanged authority)
convmem "P1.3 source-trust ranking Codex handoff"
convmem "EXECUTION source-trust ranking"
convmem "VERIFY source-trust ranking freeze V5"

# Prior board (optional depth)
convmem "debate who-fixes-retrieval Round 4 retrieve_for_ask"
convmem "KIRO opinion trace-first nested inter-model"
convmem "ask trace convmem.ask.trace.v1"

# Session cargo (chat not fully inlined here)
convmem "who-fixes-retrieval arc done P1 workers handoff 566966f0"
convmem "source-trust ranking criticality ksweep-routing"   # P1.3 cargo 4d0fbf93
```

### Exact cargo paths (Track A)

| Cargo | Path | What it holds |
|-------|------|----------------|
| **This closeout session** | `~/.cursor/projects/home-lauer-Projects-convmem-fix-ask-trace/agent-transcripts/566966f0-ca12-4280-8145-514c1b10d714/566966f0-ca12-4280-8145-514c1b10d714.jsonl` | Arc-done? → concurrent-work check → inherit/dismiss recommendation → this handoff |
| **P1.3 design/handoff session** (already in P1.3 packet) | `~/.cursor/projects/home-lauer-Projects-convmem/agent-transcripts/4d0fbf93-e1cb-4f47-99d2-0871231f5dbd/4d0fbf93-e1cb-4f47-99d2-0871231f5dbd.jsonl` | Source-trust design locks, harbor map, R0401 lessons |
| **Closed debate folder** | `docs/inter-model/debate-2026-07-15-who-fixes-retrieval/` | Round opinions, Round 2–4 planning/reference |

Re-index if search misses fresh units:

```bash
convmem index --file ~/.cursor/projects/home-lauer-Projects-convmem-fix-ask-trace/agent-transcripts/566966f0-ca12-4280-8145-514c1b10d714/566966f0-ca12-4280-8145-514c1b10d714.jsonl
# inter-model docs (Ryan / CONVMEM_CONFIRM_PROD=1 when required):
# bash scripts/index-inter-model-docs.sh   # or per-file index after merge
```

---

## Explicit non-goals for P1.3 workers

1. Do **not** change P1.3 locked design from debate archaeology.  
2. Do **not** treat this closeout as fixing P1.3 VERIFY residuals.  
3. Do **not** sunset Crush `ksweep-routing` in the same PR as P1.3 (unchanged).  
4. Anything useful that is **not** in this file → use the ritual searches / cargo paths above.

---

## Done means

| Arc | State |
|-----|--------|
| who-fixes-retrieval (Rounds 1–4 + board) | **Closed** |
| P1.3 source-trust | **Still live** — Await Ryan GATE per LATEST |
