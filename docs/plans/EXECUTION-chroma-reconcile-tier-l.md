# Execution Plan — Chroma Reconcile Tier L (T7)

## Planning Status

- **Phase:** Plan drafted; **execution not authorized**
- **Characters:** Cursor (plan + implement after lock); Ryan (Restic backup + reconcile lock)
- **Lane:** Cursor — corpus mutation; not JudgeBench judge-upgrade branch
- **Authority:** P0-B inventory complete. Tier **L** (646 orphans). Ryan **"go"** on 2026-08-07 authorized PR + this plan — **not** live rebuild execution.
- **Evidence SSoT:** `/tmp/chroma-orphan-inventory-20260808T000029Z.json`
- **Parent arc:** [EXECUTION-chroma-orphan-vector-repair.md](EXECUTION-chroma-orphan-vector-repair.md) (P0-A merged via PR pending)
- **Branch (plan):** `plan/2026-08-07-2026-08-07-chroma-orphan-vector-repair` or follow-on `plan/2026-08-07-chroma-reconcile-tier-l`

### Do not touch

- `~/.local/share/convmem/worktrees/fix-2026-08-07-judge-bench-judge-upgrades`
- JudgeBench judge-upgrade source, tests, fixtures, or baselines on that branch

---

## Inventory summary (P0-B, done)

| Metric | Value |
|--------|-------|
| METADATA ID count | 16,696 |
| Distinct HNSW `document=None` IDs (probe union) | 646 |
| Orphans (HNSW − METADATA) | **646** |
| METADATA − query anomalies | 3 (`debug-nopatch` + 2 hashes) |
| Reconcile tier | **L** (>500) |
| P0-A guard deployed | Yes (branch tip `6588896`; rerank crash stopped) |

**Tier L recommendation (from P0 plan):** full `knowledge_units` collection rebuild — not targeted evict.

---

## Problem

HNSW vector index contains ~646 embedding IDs with no METADATA segment row. P0-A prevents crashes but orphans still consume HNSW slots and can appear in query results as skipped rows — retrieval contamination remains.

---

## Goal

Restore HNSW ↔ METADATA parity for `knowledge_units` so:

1. Post-rebuild inventory reports **tier S** (≤50 orphans) or **0**
2. `cal_bad_unknown` and diverse probes return no `document=None` hits
3. `knowledge_units.jsonl` export remains authoritative; Chroma is rebuildable projection

---

## Preconditions (Ryan lock gates)

| Gate | Requirement |
|------|-------------|
| **G1** | P0-A PR merged to `main` |
| **G2** | Restic `convmem-chroma` snapshot current (`restic-ensure-chroma-snapshot.sh --check-only`) |
| **G3** | Ryan explicit **"go rebuild"** — separate from P0 PR merge |
| **G4** | No concurrent watch/index on production corpus during rebuild window |

---

## Proposed approach (tier L default)

### Phase R1 — Pre-flight (read-only)

1. Re-run `scripts/chroma_orphan_inventory.py` → fresh `/tmp/chroma-orphan-inventory-<ts>.json`
2. Confirm tier still L; capture counts for before/after diff
3. `convmem doctor` — all critical checks pass
4. Verify `knowledge_units.jsonl` row count vs METADATA count (doctor `index_drift` if available)

### Phase R2 — Backup

1. Restic snapshot (`convmem-chroma` tag) — mandatory per RECOVER.md live-write policy
2. Optional: copy `~/.local/share/convmem/chroma/` to dated backup path under `/tmp` or Restic only

### Phase R3 — Rebuild `knowledge_units` collection

**Preferred:** rebuild Chroma projection from `knowledge_units.jsonl` export (ledger-first — see `docs/audit-ledger-first/LEDGER-FAILURE-MATRIX.md`).

Candidate steps (repo-aware agent must verify exact CLI before execution):

```bash
# VERIFY exact commands against codebase before running — placeholders
convmem doctor
bash ~/Projects/convmem/scripts/restic-ensure-chroma-snapshot.sh

# Stop watch if active
# Delete or reset knowledge_units collection only (NOT conversation_summaries unless drift found)
# Re-project from knowledge_units.jsonl + processed.json policy

convmem doctor   # index_drift should clear
python scripts/chroma_orphan_inventory.py --output /tmp/post-rebuild-inventory.json
```

**Open question for implementer:** Does convmem expose `delete collection` + `reindex from export`, or is full `convmem index` (processed.json wipe) required? Document chosen path with exact commands in R3 execution handoff.

### Phase R4 — Post-verify

| Check | Pass criterion |
|-------|----------------|
| Inventory | `orphans_hnsw_minus_metadata_count` ≤ 50 (tier S) or 0 |
| Unit tests | `pytest tests/test_chroma_flatten.py -q` |
| Calibration | `eval-synthesis.py --judge --golden /tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl` — 100% |
| Doctor | No new index_drift failures |

R4 verification is executed as Flash slices V1–V6. See [EXECUTION-post-rebuild-verify-flash-slices.md](EXECUTION-post-rebuild-verify-flash-slices.md) (DeepSeek V4 Flash / Crush lane) for verbatim commands, `/tmp` evidence capture, and the GREEN / YELLOW / RED verdict rules.

### Phase R5 — METADATA-without-vector anomalies (3 IDs)

Separate from bulk orphan set. Investigate `debug-nopatch` and two hash IDs before or after rebuild — may be test artifacts or stale METADATA without vectors. Do not block R3 if they are known debug rows; document disposition.

---

## Out of scope

- `conversation_summaries` rebuild (unless doctor shows drift there too)
- JudgeBench judge-model changes
- Full `processed.json` wipe + corpus-wide reindex **unless** R3 proves export-only rebuild insufficient
- Automatic execution without G1–G4

---

## Task order

| ID | Work | Owner | Blocked on |
|----|------|-------|------------|
| T7-1 | File this plan | Cursor | — |
| T7-2 | Verify rebuild CLI path in codebase | Cursor | T7-1 |
| T7-3 | Ryan: merge P0 PR | Ryan | — |
| T7-4 | Ryan: **"go rebuild"** lock | Ryan | G1–G2 |
| T7-5 | R1–R4 execution | Cursor | T7-4 |
| T7-6 | Post-rebuild inventory + handoff | Cursor | T7-5 |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Rebuild duration (16k+ units) | Run in maintenance window; no watch |
| `processed.json` / export mismatch | Doctor index_drift before/after; export is SSoT |
| Orphans return after rebuild | Root cause (stale HNSW writes during ingest) needs separate ingest-path audit if post-verify fails |
| Summaries collection unaffected but divergent | R1 checks both collections |

---

## Stop / escalation

- If post-rebuild inventory still tier L → **stop**; do not loop rebuild blindly — escalate to ingest-path audit
- If export row count ≠ expected METADATA count → **stop** before delete
- Any `BLOCKED` from complete-data restore classification → follow RECOVER.md, no live replace

---

## Sign-off

- **Ryan:** merge P0 PR; then separate **"go rebuild"** for T7-5
- **Cursor:** R3 exact commands after T7-2 codebase verification
