# Builder-reference continuation plan — execution log (2026-06-30)

**Executor:** cursor-session (Composer)  
**Plan:** `builder_ref_continuation_0d765ca2.plan.md` (Cursor plan — not edited)  
**Chains to:** `dec_prop_20260629_150527_46f0` (digest Phase 0 / recency gap parent)  
**Pilot log:** `docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md` Run 5

---

## Scope

Implemented Lane B Steps 1–5 from the builder-reference continuation plan. Step 3 (`--propose` trial) remains **Ryan-gated** — not run by agent.

---

## Step 1 — Golden-query eval harness

| Artifact | Path |
|----------|------|
| Golden queries | `tests/fixtures/golden_queries.jsonl` (6 rows, `acceptable_ids`) |
| Eval script | `scripts/eval-retrieval.py` (P@1/P@k, `--update-baseline`) |
| Baseline | `tests/fixtures/golden_queries_baseline.json` |

**Run (2026-06-30):** P@k 83.33% (5/6); `convmem record relates-to fallback root` misses at P@5 (no `ledger_id` on semantic hits — known). `scripts/eval-retrieval.py` exits 0 vs baseline.

---

## Step 2 — Recent-decision injection (`ask()` recency gap)

| Artifact | Role |
|----------|------|
| `ledger_recent.py` | `load_recent_decisions`, `recent_decisions_for_cfg`, `decision_record_to_unit` |
| `ask.py` | `_prepend_recent_decisions` when `evidence=True` |
| `cross_project_digest.py` | imports `ledger_recent`; digest ask uses `evidence=True` |
| `mcp_server.py` | `ask` default `evidence=True` |
| `tests/test_ledger_recent.py` | load + prepend unit tests |

**Verify:** digest ask context cites Jul 1 `dec_prop_*` band overlapping `load_recent_decisions()` header — **PASS** (Run 5).

---

## Step 3 — `--propose` trial

**Status:** Not run. Eligible post-recency fix; requires Ryan approval per pilot log and plan gate.

---

## Step 4 — Unresolved JSON + MCP

| Artifact | Role |
|----------|------|
| `unresolved.py` | `unresolved_payload()`, `unresolved_items()`, `render_unresolved_json()` |
| `convmem.py` | `unresolved --json` uses shared payload |
| `mcp_server.py` | read-only `unresolved()` MCP tool |
| `tests/test_unresolved_payload.py` | payload shape tests |

---

## Step 5 — Doctor index drift

| Artifact | Role |
|----------|------|
| `doctor.py` | `index_drift` — Chroma vs **unique ids** in `knowledge_units.jsonl` |
| `docs/RECOVER.md` | one-command rebuild (`rm processed.json && convmem index`) |
| `tests/test_doctor.py` | mock `_check_index_drift` |

**Run:** `convmem doctor` — `index_drift` WARN at ~30% indexed (append-only JSONL); all checks pass.

---

## Verification matrix

| Check | Result |
|-------|--------|
| `convmem doctor` | PASS (index_drift WARN) |
| `pytest` (touched tests) | 14+ passed |
| `scripts/eval-retrieval.py` | exit 0, no regression |
| Digest pilot recency | PASS (Run 5) |
| Builder-reference deploy | N/A — no digest edits this session |

---

## Open / not owned

- `cross-project-digest.sh --propose` trial + `convmem record` for proposal outcome
- Full corpus reindex (index_drift WARN is informational; Chroma healthy)
- Hard Parts worksheet in PR (Option B forced context vs prompt-only) — deferred to PR author
- Golden query `fallback root` — acceptable_ids may need expansion or query rewrite

---

## Files touched (summary)

`ledger_recent.py`, `ask.py`, `cross_project_digest.py`, `unresolved.py`, `convmem.py`, `mcp_server.py`, `doctor.py`, `scripts/eval-retrieval.py`, `tests/fixtures/golden_queries*.json*`, `tests/test_*.py`, `docs/RECOVER.md`, `docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md`
