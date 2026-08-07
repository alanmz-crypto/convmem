# Execution Plan — Chroma Orphan Vector Repair (Revised)

## Planning Status

- **Phase:** Plan revised; P0-A implementation **not yet authorized**
- **Characters:** Cursor (implement + inventory); DeepSeek Flash (plan critique); Ryan (authorization)
- **Lane:** Cursor — not the JudgeBench implementation branch
- **Authority:** Read-only diagnosis complete 2026-08-07. Plan and P0-B (read-only inventory) may proceed. **P0-A code mutation (T2/T3) requires Ryan's explicit confirmation before Cursor writes to `chroma_store.py`.**
- **Evidence SSoT:** `/tmp/claude-chroma-raw-20260807T233007Z.json`
- **Blocker:** JudgeBench T5 calibration (`eval-synthesis.py --judge --golden /tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl`) fails on fixture `cal_bad_unknown`
- **Branch:** `plan/2026-08-07-2026-08-07-chroma-orphan-vector-repair`

### Do not touch

- `~/.local/share/convmem/worktrees/fix-2026-08-07-judge-bench-judge-upgrades`
- JudgeBench judge-upgrade source, tests, fixtures, or baselines on that branch

---

## Evidence / Diagnosis

| Layer | Finding | Status |
|-------|---------|--------|
| Crash | `ValueError: Unsupported input type: NoneType` at `rerank.py:39–40` | Proven, mechanical |
| Leak point | `chroma_store.py:517–531` `_flatten()` preserves `documents[i] is None` | Proven, mechanical |
| Call sites | `_flatten()` invoked at lines 206 (`query_summaries`), 267 (`query_units` superseded path), 276 (`query_units` normal path) | Supplied by repo-aware agent; grep output in appendix below |
| Storage | ≥11 distinct orphan IDs surfaced from 2 of 6 bounded queries; zero ID overlap between `cal_bad_unknown` (7) and `cal_good_transition` (4) | Proven, from raw artifact |
| SQLite | Fresh corpus scan: 16,747 `chroma:document` rows, 0 null, 0 empty — not a persisted-null write bug | Proven |
| Supersede filter | Ineffective on orphans: `metadata=None` → `{}` → `is_superseded()` returns `False` | Proven |
| Row-existence framing | "Absent from METADATA segment" is inference from per-ID lookup returning no keys, not a direct `row_found` flag in the capture schema | Inference-supported, not schema-proven — noted for future capture tooling |

**Radius framing:**

- **Crash radius:** query-dependent — orphans must land in the top-20 rerank window to trigger the exception.
- **Contamination radius:** broader than crash radius — orphans appear in most queries tested; passing fixtures are rank-position lucky, not clean retrieval. Total orphan count is unknown and treated as urgent, not deferred cleanup.

---

## Problem Summary

Chroma's HNSW vector index returns orphan hits (IDs with no corresponding row in the SQLite METADATA segment) as top-N query results. `_flatten()` passes these through with `document=None`, `metadata=None`. The supersede filter in `query_units()` doesn't catch them because it treats `None` metadata as an empty-but-valid dict. Reranking crashes on the first `None` document it tries to pair with the query string. This blocks the JudgeBench T5 calibration gate on `cal_bad_unknown` and, per the contamination-radius finding, is not isolated to that one fixture.

---

## Two Independent Tracks (not sequenced against each other)

### P0-A — Read-side guard (implementation gated on Ryan's authorization)

**Goal:** Stop `None` documents from reaching any `_flatten()` consumer.

**Required behavior:** `ChromaStore._flatten()` must not emit rows whose `document` is `None` into any downstream consumer (rerank, supersede filter, or otherwise). Do not coalesce `None → ""` — an empty string is rankable and would still consume a rerank slot on unrankable content.

**Skip predicate — VERIFY before finalizing:**

- Evidence-backed default: skip when `document is None`, regardless of metadata state. This is the only condition proven necessary and sufficient to prevent the observed crash.
- Before implementing, check `query_summaries()` (the call site distinct from `query_units()`) for any legitimate row shape where `document is None` but `metadata` is present and meaningful. This is the Flash critique's concern and is unresolved in the supplied evidence.
- If no such row shape exists in the summaries path: use `document is None` alone as the skip condition, uniformly.
- If such a row shape does exist: DISCRETION to the repo-aware agent to define a narrower predicate that preserves it, documented as an explicit exception with the evidence that justified it (not assumed in advance).

**T1a finding (2026-08-07, read-only):** `conversation_summaries` METADATA segment has 2,351 rows; **0** rows with absent/null `chroma:document`. `add_summary()` always passes a `document` string. No `document=None`/`metadata=present` row shape observed in summaries. **Finalized predicate for T2: skip when `document is None`.**

**Tests:**

- Unit test: synthetic Chroma response mixing valid rows and `document=None` rows — assert `_flatten()` drops only what the finalized predicate says to drop.
- Regression: `cal_bad_unknown` path through `ask()` → `query_units()` → rerank completes without the `NoneType` crash.

**Done when:** pytest passes; `ask()` on the `cal_bad_unknown` question completes without a rerank crash.

**Does not require:** orphan inventory count, reconcile/reindex, or JudgeBench branch changes.

**Requires before starting:** Ryan's explicit confirmation to mutate `chroma_store.py` (see Stop/Escalation below).

---

### P0-B — Bounded orphan inventory (read-only; no authorization gate beyond existing read access)

**Goal:** Size HNSW-vs-METADATA drift to choose targeted evict vs. partial reindex vs. full rebuild.

**Method (read-only; evidence under `/tmp` only):**

1. METADATA ID set via `chroma_readonly.collection_ids(chroma_dir, UNITS)`.
2. Query-surfaced orphan IDs — union of `none_ids` across all 5 JudgeBench calibration fixtures, the negative-control query, and 3–5 additional diverse probes (inter-model, ledger, WordPress, abstain-style).
3. Must use `open_chroma_for_verify` → `collection.query()` directly — never through `query_units()`/`ask()`/any post-`_flatten()` path, so P0-B data doesn't depend on whether P0-A has been deployed.
4. Include at least one probe with `n_results ≥ collection.count() + slack` to enumerate HNSW entries beyond the usual top-20/top-60 window.
5. Bidirectional diff: query/HNSW ID set minus METADATA IDs (orphans); METADATA IDs minus query-enumerated set (metadata-without-vector, if any — a distinct anomaly worth separately flagging if found).
6. Per-ID SQLite lookup for each diff ID: explicit `row_found: bool` (fixing the schema gap noted above), `chroma:document` presence, `superseded`, `deleted`, and a JSONL cross-reference if historical.
7. Write artifact to `/tmp/chroma-orphan-inventory-<timestamp>.json`.

**Ceiling:** if the union exceeds 500 IDs, report count + sample + source-path families and note whether full vector-segment enumeration is needed as a follow-up rather than completing it inline.

**Done when:** artifact written; summary states total distinct orphans, cross-query overlap, and a reconcile-tier recommendation:

| Tier | Orphan profile | Likely reconcile |
|------|----------------|------------------|
| S | ≤50, one source family (e.g. a single Kiro snapshot purge) | Targeted evict / metadata cleanup |
| M | 50–500, multiple families | Partial reindex or segment compaction |
| L | >500 or widespread | Full `knowledge_units` collection rebuild |

**Does not require:** P0-A to be merged first — fully parallel.

**Does not authorize:** `convmem index` full corpus, `rm processed.json`, any DB mutation, or reconcile execution. Ryan lock required after the tier is known.

---

## Out of Scope (this arc)

- JudgeBench judge-model/prompt upgrades (`fix-2026-08-07-judge-bench-judge-upgrades` branch)
- Reconcile/reindex execution — blocked on P0-B tier result + Ryan lock
- `doctor._check_embed_collection_identity` changes — different failure mode, not this diagnosis
- Modifying `/tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl`

---

## Task Order

| ID | Track | Work | Owner | Done when |
|----|-------|------|-------|-----------|
| T1 | Both | Plan filed + Flash critique | Cursor → DeepSeek | Critique received (done — "APPROVE WITH CHANGES") |
| T1a | P0-A | Check `query_summaries()` for `document=None`/`metadata=present` rows | Cursor | Finding documented; finalizes skip predicate |
| **T-gate** | Gate | **Ryan confirms authorization to mutate `chroma_store.py`** | Ryan | Explicit go-ahead recorded |
| T2 | P0-A | `_flatten()` null-document skip (predicate per T1a) + unit test | Cursor | pytest PASS |
| T3 | P0-A | Integration: `cal_bad_unknown` ask path, no crash | Cursor | Manual or test PASS |
| T4 | P0-B | Read-only inventory pass | Cursor | `/tmp/chroma-orphan-inventory-*.json` written |
| T5 | P0-B | Inventory summary + reconcile tier recommendation | Cursor | Written in handoff |
| T6 | Gate | JudgeBench T5 calibration re-run | Ryan/Cursor | `eval-synthesis.py --judge --golden …` completes |
| T7 | Future | Reconcile/reindex (separate arc) | Ryan lock | After T5 tier is known |

T1a and T4–T5 (P0-B) may run in parallel with each other and are not blocked by the T-gate. T2/T3 are blocked on the T-gate.

**Critique:** [`docs/inter-model/DEEPSEEK-FLASH-2026-08-07-chroma-orphan-plan-critique.md`](../inter-model/DEEPSEEK-FLASH-2026-08-07-chroma-orphan-plan-critique.md) — **APPROVE WITH CHANGES**

---

## Verification

```bash
cd ~/Projects/convmem

# T1a — check before finalizing predicate
grep -n "query_summaries\|_flatten" chroma_store.py
# inspect for document=None + metadata-present row handling / tests

# P0-A (after T-gate)
python -m pytest tests/test_chroma_flatten.py -q
python -c "
from ask import ask
ask('What is the exact production launch date of the fictional Moonbeam integration, according to ConvMem?', top_k=6, evidence=False)
print('OK: no rerank NoneType crash')
"

# P0-B (read-only, no gate)
# run inventory pass; inspect /tmp/chroma-orphan-inventory-*.json

# T6 gate (after P0-A merged)
python scripts/eval-synthesis.py --judge --golden /tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl
```

---

## Done Conditions

- P0-A: pytest passes on the extended `_flatten()` test; `cal_bad_unknown` no longer crashes rerank; T6 calibration run completes end-to-end.
- P0-B: inventory artifact written with explicit `row_found` flags; tier (S/M/L) recommended with supporting counts.

---

## Stop / Escalation Conditions

- **Do not write to `chroma_store.py` (T2) until Ryan has explicitly confirmed authorization in this thread.** The plan being drafted and critiqued is not itself authorization.
- If T1a finds a legitimate `document=None`/`metadata=present` row shape, stop and report before choosing a predicate — this is a case where evidence changes the implementation, not a routine repo-consistent choice.
- If P0-B's orphan union exceeds 500 IDs, stop at the reporting ceiling rather than attempting full vector-segment enumeration inline.
- If P0-B surfaces the inverse anomaly (METADATA rows with no corresponding vector), stop and report separately — that's a different failure mode than this diagnosis covers and may need its own plan.
- Any reconcile/reindex action (T7) requires a separate, explicit Ryan lock after the P0-B tier is known — not implied by P0-A or P0-B completion.

---

## Sign-off / Authorization

- **Mechanical:** Cursor completes T1a, T2–T5; T6 proves T5 calibration unblocked.
- **Ryan:** confirms authorization for T2/T3 (code mutation) before Cursor begins; separately authorizes the reconcile arc (T7) only after the P0-B tier report.
- **DeepSeek Flash:** adversarial critique on T1 (received, "APPROVE WITH CHANGES") — the `query_summaries()` concern is now T1a, not left as an open note.

---

## Appendix — `_flatten()` call-site grep (2026-08-07)

```
$ rg -n "_flatten\(" chroma_store.py
206:        return self._flatten(res)      # query_summaries()
267:            return self._flatten(res)  # query_units(include_superseded=True)
276:        results = self._flatten(res)   # query_units() normal path
517:    def _flatten(res: dict) -> list[dict]:
```

Context (abbreviated):

```python
# line 199–206 — query_summaries
def query_summaries(self, embedding, top_k):
    res = self._collection(SUMMARIES).query(...)
    return self._flatten(res)

# line 255–276 — query_units
def query_units(self, embedding, top_k, *, include_superseded=False):
    ...
    results = self._flatten(res)
```
