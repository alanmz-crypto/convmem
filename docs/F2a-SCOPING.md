# F2a — Store API + dedupe hardening (Builder brief)

**Status:** Ready to scope/implement in parallel with backfill drain  
**Blocked:** Nothing — independent of F2b monitor  
**Depends on:** F1 ✅ signed off

---

## Goals

1. Move embedding access behind public `ChromaStore` API (Kiro flag from F1 review)
2. Reduce duplicate citations in `ask --evidence` (post-rerank `ledger_id` dedupe)
3. Optional: LLM verdict pass on `semantic_dedupe` queue (v1.1 if time)

---

## Task 1 — `get_units_with_embeddings()`

**Why:** `job_semantic_dedupe` calls `store._collection("knowledge_units")` directly — fragile.

**API:**

```python
def get_units_with_embeddings(
    self,
    *,
    include_superseded: bool = False,
) -> list[dict]:
    # Returns [{"id", "metadata", "embedding"}, ...]
    # metadata["id"] bound to chroma id (same as units_metadata)
```

**Acceptance:**

- `semantic_dedupe` uses public method only
- No `_collection` calls outside `chroma_store.py`
- Unit test with mock or temp Chroma

---

## Task 2 — `ask.py` citation dedupe (post-evidence rerank)

**Why:** Twin UUIDs fixed in Chroma; same `ledger_id` can still appear twice in top-k if scores differ slightly.

**Where:** After `apply_evidence_rerank()`, before slice to `top_k`:

```python
# Keep highest rank_score per ledger_id; skip empty ledger_id (legacy)
```

**Acceptance:**

- `ask --evidence` with duplicate ledger hits → one citation per `ledger_id`
- Existing evidence rerank tests unchanged
- New test: two results same `ledger_id` → one citation

---

## Task 3 — Document F1-lite semantic dedupe

**Already in MILESTONE-F.md:** queues on embedding similarity only; no LLM verdict in F1.

**Optional F2a stretch:** For each `dedupe_queue.jsonl` row, optional LLM same-fact? → still **no auto-merge**; append verdict to queue record only.

---

## Out of scope (F2a)

- F2b `monitor.py` (see `F2b-MONITOR-POLICY.md`)
- Full `redistill` chunk replay
- `--approve-dedupe` CLI (manual JSONL review OK for now)
- `--prune` / physical delete

---

## Verification

```bash
python -m unittest discover -s tests
convmem ask "What security issues remain unresolved?" \
  --domain web_stack.security --evidence
# → no duplicate ledger_id in References panel
```

---

## Priority

| P | Task | Effort |
|---|------|--------|
| 1 | Citation dedupe in `ask.py` | Small |
| 2 | `get_units_with_embeddings()` | Small |
| 3 | LLM verdict on dedupe queue | Optional |

---

*For Builder — implement when user says go on F2a.*
