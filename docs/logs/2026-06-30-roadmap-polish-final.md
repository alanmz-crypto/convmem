# Roadmap polish — execute-ready plan (2026-06-30)

**Author:** composer-2.5-fast (Cursor)  
**Trigger:** Ryan asked to polish planning after P0–P1b + global protocol closed; incorporate Claude review.  
**Chains to:** `dec_prop_20260623_215943_5abe` (planner arc)

---

## Where convmem is

**Mode:** operate-and-document — not foundation-build.

| Layer | Status |
|-------|--------|
| P0–P1b | Closed (watch, doctor, F2a, unresolved, golden 10/10) |
| Global protocol + soak | Closed per `docs/inter-model/LATEST.md` |
| Corpus | ~2,915 units |
| Chroma write path | Fixed in working tree — `ChromaStore` always `PersistentClient` (SegmentAPI upsert failed on live HNSW with "Index seems to be corrupted or unsupported") |
| Next default build | None — land git + graduate `ROADMAP.md` |

---

## Plan evolution (this session)

1. **Brainstorm** → lauer-only roadmap (watch, doctor, F2a, P1a/b, gated P2).
2. **Gap audit** — protocol closed; ROADMAP-DRAFT stale; uncommitted ~745-line tree.
3. **Chroma bug** — `record --approve-last` approved to JSONL but index failed; root cause SegmentAPI vs PersistentClient on non-empty HNSW.
4. **Polish v1** — operate-and-document; P1c streaming; two-commit landing suggested.
5. **Claude review v1** — split Chroma commit; Restic gate; live-HNSW regression test; hard `_debug_log` gate; pinned thresholds (>20 inventory, delete stale decisions jsonl, P1c ≥3/week).
6. **Claude review v2** — Restic **snapshot-if-stale before gates** (not just before commit); gate order cheapest-first; rerank moved to manual spot-check (not hard trigger).

**Execute-ready plan:** Cursor plan `convmem_roadmap_final` (2026-06-30).

---

## Execute sequence (not done yet)

```
0. Restic: current? If stale → snapshot chroma now; block if Restic fails
1. Gates (cheapest-first):
   rg '_debug_log' chroma_store.py → zero
   live-HNSW regression test (non-empty corpus upsert)
   unittest + doctor
   live record --approve-last or add --upsert
2. Commit 1: chroma_store.py + test only
3. Commit 2: protocol, adapters, docs, ROADMAP.md, README
4. Hygiene: inventory >20 → index; delete unsigned examples/decisions-session-2026-06-18.jsonl
```

**Optional (gated):**

- P1c streaming Phase 1 — ≥3 `synthesis_failed` / calendar week of `ask`
- P2 MCP tools — new FAIL row in `VERIFICATION-MATRIX.md` only
- P2-stream — after P1c + client pre-flight

---

## Still open (plan only)

| Item | Notes |
|------|-------|
| Land git (2 commits) | Chroma fix + sprawl separated |
| `ROADMAP-DRAFT.md` → `ROADMAP.md` | Test count from `brief --with-tests` at publish |
| Live-HNSW regression test | Not in suite yet — add before Commit 1 |
| `_debug_log` in chroma_store.py | Strip before Commit 1 |
| P1c / P2 / P2-stream | Gates not fired |

---

## Record block

Ryan runs:

```bash
convmem record \
  --relates-to dec_prop_20260623_215943_5abe \
  --summary "convmem planner: execute-ready operate-and-document roadmap — Restic gate, two-commit Chroma landing, pinned optional gates" \
  --rationale "After P0–P1b and global protocol closed (~2915 units, golden 10/10). Polished roadmap for lauer: operate-and-document not foundation-build. Chroma fix identified: SegmentAPI upsert failed on live HNSW (record --approve-last index error); working tree uses PersistentClient-only. Execute sequence: Restic current or snapshot-if-stale BEFORE gates; gates cheapest-first (no _debug_log, live-HNSW regression test, unittest+doctor, live upsert); Commit 1 chroma+test only, Commit 2 protocol/docs/ROADMAP/README; hygiene >20 pending inventory, delete unsigned examples/decisions-session-2026-06-18.jsonl; rerank manual spot-check only. P1c if ≥3 synthesis_failed/week; P2 on new VERIFICATION-MATRIX FAIL only. Log: docs/logs/2026-06-30-roadmap-polish-final.md. Not executed: commits, ROADMAP graduation, regression test." \
  --author composer-2.5-fast

convmem record --approve-last
```
