# Arc Brief — Chroma Reconcile Tier L

> **Every model working on this arc must read this file at session start.**
> After reading, state: "Goal: [one sentence]. My role: [what I'm here to do]. The system currently: [what exists]. Missing: [what doesn't exist yet]."

---

## 1. What This Is For (product goal)

ConvMem's retrieval layer is a two-part store: a Chroma HNSW vector index plus a SQLite METADATA segment. Each indexed unit needs both halves. A bug in the legacy indexing path left 646 IDs present in HNSW but missing from METADATA ("orphans"). Orphans polluted query results with `document=None` rows, crashed the reranker, and blocked the JudgeBench calibration fixture `cal_bad_unknown` — meaning **all retrieval-dependent quality measurement was on contaminated ground**.

**This arc restores HNSW↔METADATA parity.** When complete:

1. Post-rebuild inventory reports **tier S** (≤50 orphans) or **0**
2. `cal_bad_unknown` and diverse probes return no `document=None` hits
3. The corpus is a clean foundation for JudgeBench calibration, `ask.py` judging, and any future eval work

**Done means:** the rebuild is verified GREEN, docs are merged to `main`, and the corpus is treated as trustworthy again for downstream eval arcs.

---

## 2. System Design (how the pieces connect)

```
        knowledge_units.jsonl   (authoritative export, ledger-first)
              │
              │ rebuild projection
              ▼
        ┌─────────────────────────┐
        │   Chroma knowledge_units │
        │   ┌──────────────────┐  │
        │   │ HNSW vector index │  │
        │   │  (id → embedding) │  │
        │   └─────────┬────────┘  │
        │             ▼           │
        │   ┌──────────────────┐  │
        │   │ SQLite METADATA   │  │
        │   │  (id → document,  │  │
        │   │   metadata)       │  │
        │   └─────────┬────────┘  │
        └─────────────┼───────────┘
                      │
                      ▼ query_units / query_summaries
              ┌──────────────┐
              │ _flatten()   │  ← P0-A guard here (drop None rows)
              └──────┬───────┘
                     ▼
               rerank / ask / eval
```

**Key invariants:**
- `knowledge_units.jsonl` is the source of truth; Chroma is a rebuildable projection (`docs/audit-ledger-first/LEDGER-FAILURE-MATRIX.md`).
- P0-A `_flatten()` guard must never emit `document=None` rows; do **not** coalesce `None → ""` (empty strings are rankable and would still consume rerank slots).
- Orphan inventory must bypass `_flatten()` (use `open_chroma_for_verify` → `collection.query()`) so the read path being measured isn't filtered by the guard it's measuring.

---

## 3. What Exists Right Now (file map)

### On `main` (merged, stable)

| File | What it does | State |
|------|-------------|-------|
| `chroma_store.py` — `_flatten()` guard | Drops `document=None` rows before consumers | **Merged (#141)** |
| `tests/test_chroma_flatten.py` | Guard unit tests (4 tests) | Green |
| `scripts/chroma_orphan_inventory.py` | Read-only inventory tool; emits tier recommendation | Complete |
| `scripts/eval-synthesis.py` | Calibration harness; requires `--legacy` with `--judge` (lines 137–141) | Complete |
| `docs/plans/EXECUTION-post-rebuild-verify-flash-slices.md` | Flash V1–V6 slice brief with verbatim commands | On `main` (#161); V5 includes `--legacy` |
| `docs/inter-model/FLASH-2026-08-08-post-rebuild-verify-handoff.md` | R4 GREEN evidence handoff + close-out | On `main` (#161) |
| `docs/plans/STATUS-chroma-reconcile-tier-l.md` | **This file** — arc landscape | On `main` (#161) |

### Planning docs on `main`

| File | Role |
|------|------|
| `docs/plans/EXECUTION-chroma-orphan-vector-repair.md` | Parent arc — P0-A guard + P0-B inventory |
| `docs/plans/EXECUTION-chroma-reconcile-tier-l.md` | This arc's plan — R1–R5 phases |
| `docs/inter-model/DEEPSEEK-FLASH-2026-08-07-chroma-orphan-plan-critique.md` | Plan review |
| `docs/inter-model/CRUSH-2026-08-08-index-complete-judgebench-unblock.md` | Rebuild completion note |

### /tmp evidence (ephemeral — captured in handoff doc)

| Path | Contents |
|------|----------|
| `/tmp/chroma-orphan-inventory-20260808T000029Z.json` | Pre-rebuild: 646 orphans, tier L |
| `/tmp/chroma-orphan-inventory-20260809T022634Z.json` | Post-rebuild: **0 orphans, tier S** |
| `/tmp/post-rebuild-calibration-20260808T212706Z.log` | V5 calibration log (100% pass with `--legacy`) |

---

## 4. Completion State

| # | Milestone | Status | Evidence |
|---|-----------|--------|----------|
| P0-A | `_flatten()` read-side guard | **DONE** — merged #141 | `tests/test_chroma_flatten.py` green |
| P0-B | Tier-L orphan inventory | **DONE** — 646 orphans documented | `/tmp/chroma-orphan-inventory-20260808T000029Z.json` |
| G1 | P0-A merged | **DONE** | #141 |
| G2 | Restic snapshot | **DONE** | pre-rebuild policy |
| G3 | Ryan "go rebuild" | **DONE** | 2026-08-07 |
| R3 | Full re-index | **DONE** | `CRUSH-2026-08-08-index-complete-judgebench-unblock.md` |
| R4 | Post-rebuild verify | **DONE — GREEN** | `FLASH-2026-08-08-post-rebuild-verify-handoff.md` |
| Docs | Handoff + STATUS + brief on `main` | **DONE** | #161 |
| R5 | 3 METADATA-without-vector anomalies (`debug-nopatch` + 2 hashes) | **Optional disposition** | Documented in parent plan |

**Summary: Arc is closed for code and verification. Optional R5 disposition and Ryan-gated ops remain.**

---

## 5. Your Role (read this to know what you're here to do)

**If Ryan sent you here to disposition R5:** The 3 METADATA-without-vector anomalies are documented in `EXECUTION-chroma-reconcile-tier-l.md` Phase R5. They may be test artifacts or stale rows; decide whether to drop, keep, or move to a debug collection. This is not a blocker.

**If Ryan sent you here to verify the GREEN verdict:** Read `FLASH-2026-08-08-post-rebuild-verify-handoff.md`. The four gates (inventory, unit tests, calibration, doctor) all passed. Evidence paths are in the handoff's artifact table. Do not re-run gates unless Ryan asks for a regression check.

**If Ryan sent you here because retrieval looks wrong:** That would be a new arc. This arc's verify was GREEN; new contamination would need a fresh inventory and diagnosis.

**If you don't know why you're here:** Ask Ryan. This arc is closed unless retrieval regresses or you are handling optional R5 / ops items below.

---

## 6. What Remains Before "Live" (sequential)

- [ ] Optional: R5 anomaly disposition (decision only, no code)
- [ ] Optional, deferred: rebaseline `/tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl` after Ollama 0.30.11 → 0.32.3 (Cursor proposes, Ryan locks; tracked as JudgeBench concern, not this arc)
- [ ] Ops: `convmem-watch` monitor restart and `convmem refine` bulk run — Ryan-gated

---

## 7. Hard Stops (models cannot cross)

| Stop | Gate owner | What it blocks |
|------|-----------|----------------|
| Restic snapshot requirement | Ryan + RECOVER.md live-write policy | Any corpus mutation without a current backup |
| "Go rebuild" authorization | Ryan | Phase R3 execution |
| Merge to `main` | Ryan | All PRs — models never merge |
| `convmem record` | Ryan | Ledger writes from this arc |
| Bulk `convmem refine` / `convmem index` (without `--file`) | Ryan | Post-rebuild ops |
| JudgeBench G3/G4 (gold corpus, judge selection) | Ryan | Separate arc — not unblocked by this one |

---

## 8. Relationship to ConvMem (the bigger picture)

```
ConvMem retrieval stack:
├── Ledger / knowledge_units.jsonl   — authoritative source
├── Chroma projection (THIS ARC)     — rebuildable; was contaminated, now clean
│     ├── P0-A guard — defensive (merged)
│     ├── P0-B inventory — diagnostic (done)
│     └── Tier-L rebuild + R4 verify — restorative (done, GREEN)
├── JudgeBench (SEPARATE arc)        — uses this corpus; calibration unblocked
└── Live ask.py reranking            — depends on clean retrieval
```

This arc is *downstream of* the ledger and *upstream of* JudgeBench calibration. A contaminated Chroma silently invalidates every quality signal above it; that's why this had to land first.

---

## 9. Key Design Files (for deep dives)

| Purpose | Path | Read when |
|---------|------|-----------|
| Parent arc (P0-A guard + P0-B inventory) | `docs/plans/EXECUTION-chroma-orphan-vector-repair.md` | You need leak-point evidence or `_flatten()` call-site analysis |
| This arc's plan | `docs/plans/EXECUTION-chroma-reconcile-tier-l.md` | You need phase breakdown, gates, Ryan's lock conditions |
| Flash executor brief | `docs/plans/EXECUTION-post-rebuild-verify-flash-slices.md` | You need the exact V1–V6 commands |
| GREEN evidence handoff | `docs/inter-model/FLASH-2026-08-08-post-rebuild-verify-handoff.md` | You need to see pass/fail per gate |
| Plan critique | `docs/inter-model/DEEPSEEK-FLASH-2026-08-07-chroma-orphan-plan-critique.md` | You need to know why the plan looks the way it does |
| Rebuild completion note | `docs/inter-model/CRUSH-2026-08-08-index-complete-judgebench-unblock.md` | You need post-rebuild corpus stats |

---

## 10. How to Update This Brief (departure protocol)

**When you finish working on this arc, update this file before handoff.** The goal is that the *next* model reads this one document and has the same quality of mental landscape you had — updated to reflect reality after your work.

**Rules — keep this a snapshot, not a log:**

1. **Overwrite, don't append.** Update section 3 (file map) and section 4 (completion state) to reflect current reality. Delete rows for things that no longer exist. Change "on wip branch" to "on `main`" when merged.

2. **Keep section 5 (Your Role) generic.** Rewrite for what the *next* model probably needs to do, not what you just did.

3. **Update section 6 (What Remains) by removing completed items.** The list only shows what's ahead.

4. **Touch the diagram (section 2) only if the design changed.**

5. **One line in the Update Log.** Date, your name, milestone-level change.

6. **Do not add session-specific context.** No "I ran into X"; that belongs in Track A session ingest.

7. **The test: could a model read *only* this file and know what to do?** If not, fix it.

---

## Update Log

| Date | Who | Change |
|------|-----|--------|
| 2026-08-09 | Crush (DeepSeek Flash close-out) | Initial arc brief; R4 GREEN |
| 2026-08-09 | Cursor | Landscape sync: docs on `main` (#161); arc closed except optional R5/ops |
