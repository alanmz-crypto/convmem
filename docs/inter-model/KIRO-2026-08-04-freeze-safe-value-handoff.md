# Kiro → Codex handoff — freeze-safe high-value work (2026-08-04)

**Who:** Kiro (review lane), handing to Codex (architecture/planning).
**What:** Evidence from this session + map of the most valuable freeze-safe work available now.
**When:** 2026-08-04T01:45Z. Corpus frozen (census window ends 2026-08-07).
**Why:** Session produced two pieces of real evidence and one blocked finding. This handoff routes the next productive work.
**How:** Codex reads this, picks the highest-leverage item it can execute within its lane, and starts.

---

## Evidence produced this session

### 1. P1.3 source-trust ranking: POST-SHIP PASS (closes the loop)

PR #78 (`af31c6e`, merged) added source-trust boosts. Verification at PR time was on a frozen snapshot. **This session re-probed on the live corpus (16,115 units):**

| Query class | Rank 1 | Boost | First chat rank |
|---|---|---|---|
| `ksweep-deploy` | `.kiro/steering/ksweep-deploy.md` | +0.15 | 5 (no boost) |
| `#ksweep-deploy convmem steering` | steering snapshot | +0.15 | 6 |
| `convmem ksweep deploy instructions steering` | steering snapshot | +0.15 | 8 |

**Verdict:** The June 30 failure class (stale chat outranking authoritative steering) is definitively resolved on live. Steering P@1 across all variants. **This closes `dec_prop_20260722_013340_dc60`.**

### 2. Doctor FAIL `census_revision_mismatch`: root-caused, non-blocking

- Census armed 2026-07-30 at `76126e0` (origin/main).
- Runtime = `b346221` (branch `docs/2026-08-03-kiro-delegation-instructions`, 5 commits ahead).
- `current_code_revision()` = `git rev-parse HEAD` in repo CWD. Any non-main checkout trips it.
- Census has **15,652 events** — valuable, do not discard.
- Window ends **2026-08-07** naturally.
- **Non-blocking:** only prevents `repair_empty_ledger_documents` (not needed during freeze). Reads, indexing, search, record all continue working.
- **Fix:** wait 3 days, or verify via worktree (`git worktree add /tmp/convmem-doctor-check origin/main && cd /tmp/... && convmem doctor`).

### 3. Embedding eval real-run: blocked on R2b authorization

Both models respond (`nomic-embed-text` 768d, `mxbai-embed-large` 1024d). Shadow configs exist. Harness code-complete on main. **But:** shadow Chroma stores are empty — no corpus package exists. The pipeline (R2b capture → B-Accept → R4/R5 builds → R7 compare) is sequentially gated by Ryan authorization at each step.

---

## What Codex can do now (ranked by evidence value)

### Tier 1 — Produces durable Gate 2 prep evidence

**A. Expand the golden query set (8 → 25–40 queries)**

- The EXECUTION plan explicitly requires a "25–40-query pilot with resolvable real corpus/ledger IDs, Claude label/coverage review, and query/relevance hashes bound into the approved Gate 2 run-manifest."
- Current: only 8 queries in `tests/fixtures/golden_queries.jsonl`.
- **Work:** mine the corpus for representative queries across domains (coding.tooling, web_stack.wordpress, web_stack.security, workflow.git, ai.embedding_eval). For each, identify the correct `acceptable_ids` from ledger/Chroma. Write coverage analysis. Output: expanded JSONL + coverage doc.
- **Why now:** completely read-only. Frozen corpus = stable ground truth. Every query added now is usable for the real comparison later.
- **Blocks:** nothing — this is autonomous.
- **Ledger relate:** `dec_prop_20260705_011902_3adf` (golden eval family).

**B. Standing-check probes: `escalation-threshold-retune`**

- Corpus is now 16,115 units vs baseline 5,708 (2.82× — well past the 2.0 trigger).
- The triage note says: "Query recent escalation rates to assess safety impact before deferring retune."
- **Work:** count synthesis_gate and index_gate failures over rolling 7d/30d windows (from doctor output / `convmem brief`). Determine if the current ≥3/week threshold still makes sense at 2.8× corpus size. Write finding.
- **Why now:** purely read-only data gathering. The actual retune is Ryan-gated config edit.
- **Blocks:** nothing.

### Tier 2 — Reduces queue debt (read-only triage)

**C. Wave 2 retrieval-coherence observations (`obs_67af0873f738`, `obs_a379f07d0878`, `obs_806985bc5697`)**

- These are retrieval-gap observations from the triage note.
- **Work:** query the corpus for each obs, verify whether the gap still exists post source-trust merge, document findings (close or re-affirm each).
- **Why now:** source-trust may have already fixed some of these. Read-only verification.

**D. Recency-boost standing check probe**

- Same 2.82× trigger as escalation-threshold.
- **Work:** measure whether recency=0.1 / 30-day half-life causes staleness problems at current corpus size. Query pairs where the correct answer is recent vs old to measure displacement.
- **Why now:** frozen corpus = controlled measurement.

### Tier 3 — Prepares future authorization (docs only)

**E. Draft the R2b run-manifest + capture plan for Ryan review**

- Schema is implemented (`eval_corpus/r2b_capture_auth.py`). What's missing: the actual manifest JSON file with correct hashes, paths, and an approval sidecar.
- **Work:** draft the manifest body, document what Ryan needs to approve, reference the existing `EXECUTION-2026-07-20-r2b-capture.md` plan.
- **Caution:** This is docs-only. No execution. The draft does NOT constitute authorization.

**F. Challenger model decision: confirm `mxbai-embed-large` vs `qwen3-embedding:8b`**

- R2a configs use `mxbai-embed-large`. A Codex session (July 20) records Ryan selecting `qwen3-embedding:8b` as challenger. No plan doc reflects this. `qwen3-embedding:8b` is **not pulled** on Ollama.
- **Work:** search corpus for the Ryan directive, reconcile with R2a configs, document the authoritative choice.
- **Why now:** prevents building the wrong shadow store when R2b is eventually authorized.

---

## System state snapshot

| Check | State |
|---|---|
| Branch | `docs/2026-08-03-kiro-delegation-instructions` (5 ahead of main) |
| origin/main | `76126e0` — PR #136 |
| Census | armed, window 2026-07-31 → 2026-08-07, 15652 events |
| Doctor | 1 FAIL (census_revision_mismatch — non-blocking), 2 WARN |
| Standing DUE | recency-boost-retune, escalation-threshold-retune |
| Unresolved | 11 (7 now, 4 deferred per triage note) |
| Embed models | nomic-embed-text (768d), mxbai-embed-large (1024d) — both responding |
| Shadow stores | configs only (empty chroma dirs) |
| Golden queries | 8 (target: 25–40) |

---

## Relates-to

- `dec_prop_20260722_013340_dc60` — P1.3 source-trust (now closeable)
- `dec_prop_20260705_011902_3adf` — golden eval family
- `dec_prop_20260623_161428_c311` — fallback root

---

## Ritual entry

```bash
convmem doctor
convmem brief --stdout-only
convmem unresolved
git branch --show-current
```
