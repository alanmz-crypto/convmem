# CURSOR — execution plan: evidence budget + nested inter-model ingest

**Date:** 2026-07-15
**From:** Cursor (implementer)
**Status:** Ready to code when Ryan authorizes. This document is the runbook.
**Does not authorize code by itself** — partners signed the architecture; Ryan starts implementation.

## Authority

| Doc | Role |
|---|---|
| [CURSOR-architecture-evidence-and-nested-ingest.md](CURSOR-architecture-evidence-and-nested-ingest.md) | Locked design |
| [CURSOR-conflict-disposition-evidence-nested.md](CURSOR-conflict-disposition-evidence-nested.md) | Phase 1 vs follow-on |
| [CURSOR-partner-signoff-2026-07-15.md](CURSOR-partner-signoff-2026-07-15.md) | R1 / V4 / Kiro sign-off |
| [KIRO-review-cursor-architecture.md](KIRO-review-cursor-architecture.md) | Cap-after-dedupe + approve |

## Branch and commits

```bash
cd ~/Projects/convmem
convmem work start fix ask-evidence-budget
# Branch shape: fix/YYYY-MM-DD-ask-evidence-budget off origin/main
```

Two commits on that branch (push after each with explicit refspec):

1. Phase 1 — evidence budget / store close
2. Phase 2 — nested `docs/inter-model/**` + Kiro snapshot rejection test

Never edit on `main`. No bulk `convmem index`. No live Chroma purge.

---

## Phase 1 — evidence budget (commit 1)

### 1.0 Reproduce (PR body baseline)

```bash
convmem ask "Why was purge-drift deferred after the exclude-purge review?"
convmem ask --evidence "Why was purge-drift deferred after the exclude-purge review?"
```

Record per citation: `source_path`, `domain`, `ledger_id`, `evidence_status`.

### 1.1 Code — `_prepend_recent_decisions` in `ask.py`

Replace behavior at ~167–188. Exact pipeline:

1. Filter raw `recent_records` by explicit `domain` / `site` when supplied
   (`site` exact; `domain` top-level prefix via `domain.split(".")[0]`).
2. Convert with `decision_record_to_unit` (≤ `max_recent` / `RECENT_DECISIONS_LIMIT`).
3. Drop from **recent** any unit whose `ledger_id` already appears in semantic
   (semantic keeps the unit; recent inject is novel-only).
4. Cap: `capped = recent_after_dedupe[: min(max_recent, max(1, total_limit // 3))]`.
5. Return `capped + semantic[: total_limit - len(capped)]` (merged length == `total_limit`).

Wire call site (~324): pass `domain=` / `site=` from `ask()`.

Do **not** change MCP `evidence=True` default.

### 1.2 Code — ChromaStore leak

In evidence block (~312), replace bare `ChromaStore(...)` with:

```python
with ChromaStore(cfg["index"]["chroma_dir"]) as store:
    units = apply_evidence_rerank(...)
```

(`__enter__` / `__exit__` already call `close()` in `chroma_store.py` ~105–118.)

### 1.3 Confirm provenance (no feature work)

`decision_record_to_unit` sets `evidence_status="recent_decision"` (`ledger_recent.py` ~87).
Citation formatting already passes `evidence_status` (`ask.py` ~238). After the cap change,
spot-check that injected units still carry that field (Codex audit surface).

### 1.4 Tests — `tests/test_ledger_recent.py`

- 8 recent + 8 semantic, `total_limit=8` → ≤2 recent, length 8; simulated `[:5]` ≥3 semantic.
- Cap-after-dedupe: overlapping ledger_ids reduce recent *before* cap.
- Small `total_limit` (e.g. 2): `max(1, 0)=1` still allows one recent when records exist.
- Explicit `domain` / `site` filters mismatched records.
- Unscoped path: ≤ minority recent (cross-project allowed this round).
- Store closed via context manager on success and on rerank exception.

### 1.5 Verify and push

```bash
# focused then full suite + whitespace gate
# re-run --evidence query; paste before/after citation table in PR body
git push -u origin "$branch:refs/heads/$branch"
```

Acceptance: final five citations ≥3 semantic when ≥5 semantic candidates (`fetch_k=8` / `top_k=5`).

---

## Phase 2 — nested inter-model ingest (commit 2)

### 2.1 Tests first — `tests/test_inter_model_doc.py`

- Direct `docs/inter-model/*.md` → True + `detect_format == "inter_model_doc"`
- Nested `docs/inter-model/debate-*/FILE.md` → True
- Deep nest → True
- `docs/archive/inter-model/...` → False
- `.kiro/sessions/.../snapshots/.../docs/inter-model/debate/.../*.md` → False
- `other/inter-model/file.md` → False

### 2.2 Code — `adapters/inter_model_doc.py`

After suffix / `archive` / `_EXCLUDE_PATH_TOKENS`, accept when some index `i` has
`parts[i] == "inter-model"` and `parts[i-1] == "docs"`. Keep exclusions **ahead** of
the ancestor walk.

### 2.3 Post-land (Ryan-authorized, not bulk)

```bash
# individual files only, from repo checkout that has debate markdown
convmem index --file docs/inter-model/debate-2026-07-15-who-fixes-retrieval/ALERT-2026-07-15-deepseek-p0-landed.md
# ...other named debate files as needed
convmem "ALERT DeepSeek P0 landed"   # distinctive phrase smoke
```

---

## Out of scope (this series)

| Item | Status |
|---|---|
| Citation `(recent decision)` UX labels | Follow-on |
| Uncapped-when-domain-scoped | Follow-on |
| Domain inference | Rejected / stay explicit |
| `ask(trace=True)` | Phase 3 (R1 + Kiro) |
| MCP `evidence` default flip | Ryan only |
| Bulk index / live purge / rerank flip | Out |

## Partner smoke after Phase 1 lands

- **Kiro:** confirm ≥3/5 semantic on MCP-equivalent `--evidence` path.
- **R1:** confirm slots-only formula remains superseded; store closed; `evidence_status` retained.
