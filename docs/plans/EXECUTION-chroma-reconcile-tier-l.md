# Execution Plan — Chroma Reconcile Tier L (T7)

## Planning Status

- **Phase:** Plan drafted; **execution not authorized**
- **Characters:** Cursor (plan + implement after lock); Ryan (Restic backup + reconcile lock)
- **Lane:** Cursor — corpus mutation; not JudgeBench judge-upgrade branch
- **Authority:** P0-B inventory complete. Tier **L** (646 orphans). Ryan **"go"** on 2026-08-07 authorized PR + this plan — **not** live rebuild execution.
- **Evidence SSoT:** `/tmp/chroma-orphan-inventory-20260808T000029Z.json` (UTC Aug 8; authorization was local Aug 7)
- **Parent arc:** [EXECUTION-chroma-orphan-vector-repair.md](EXECUTION-chroma-orphan-vector-repair.md) (P0-A merged via PR #141, squash commit on main)
- **Branch (plan):** `plan/2026-08-07-chroma-reconcile-tier-l`

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
| P0-A guard deployed | Yes (PR #141 squash-merged to main) |

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
| **G1** | P0-A PR #141 merged to `main` (DONE) |
| **G2** | Restic `convmem-chroma` snapshot current (`restic-ensure-chroma-snapshot.sh --check-only`) |
| **G2b** | Ryan confirms backup snapshot id before rebuild (see T7-2b) |
| **G3** | Ryan explicit **"go rebuild"** — separate from P0 PR merge |
| **G4** | No concurrent watch/index on production corpus during rebuild window; verify daemons stopped (see R3 pre-checks) |

---

## Proposed approach (tier L default)

### Phase R1 — Pre-flight (read-only)

1. Re-run `scripts/chroma_orphan_inventory.py` → fresh `/tmp/chroma-orphan-inventory-<ts>.json`
2. Confirm tier still L; capture counts for before/after diff
3. `convmem doctor` — all critical checks pass
4. Verify `knowledge_units.jsonl` row count vs METADATA count (doctor `index_drift` if available)

### Phase R2 — Backup

**Backup ownership:** Ryan confirms Restic snapshot id before Cursor runs R3 (gate G2b).

1. Restic snapshot (`convmem-chroma` tag) — mandatory per RECOVER.md live-write policy
2. Optional: copy `~/.local/share/convmem/chroma/` to dated backup path under `/tmp` or Restic only

### Phase R3 — Rebuild `knowledge_units` collection

**Preferred:** rebuild Chroma projection from `knowledge_units.jsonl` export (ledger-first — see `docs/audit-ledger-first/LEDGER-FAILURE-MATRIX.md`).

Candidate steps (repo-aware agent must verify exact CLI before execution):

```bash
# VERIFY exact commands against codebase before running — placeholders
convmem doctor
bash ~/Projects/convmem/scripts/restic-ensure-chroma-snapshot.sh

# Pre-R3 daemon check (mandatory for G4):
# Verify watch/refine/monitor daemons are stopped — convmem doctor alone is insufficient
pgrep -f "convmem watch" && echo "FAIL: watch still running" || true
pgrep -f "convmem refine" && echo "FAIL: refine still running" || true
systemctl --user status convmem-watch.service 2>/dev/null || true
# Stop if active:
# systemctl --user stop convmem-watch.service convmem-refine.service convmem-monitor.timer

# Delete or reset knowledge_units collection only (NOT conversation_summaries unless drift found)
# Re-project from knowledge_units.jsonl + processed.json policy

convmem doctor   # index_drift should clear
python scripts/chroma_orphan_inventory.py --output /tmp/post-rebuild-inventory.json
```

**T7-2 deliverable (required before G3):** Document the chosen rebuild path with exact CLI — either (a) delete `knowledge_units` collection + reindex from `knowledge_units.jsonl` export (preferred, ledger-first), or (b) full `convmem index` with `processed.json` wipe if (a) is not supported. T7-4 **go rebuild** must not fire until this is written in the execution handoff.

### Phase R4 — Post-verify

| Check | Pass criterion |
|-------|----------------|
| Inventory | `orphans_hnsw_minus_metadata_count` ≤ 50 (tier S) or 0 |
| Unit tests | `pytest tests/test_chroma_flatten.py -q` |
| Calibration | `eval-synthesis.py --judge --golden /tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl` — 100% completion; **caveat**: judge pipeline is informational/thin (no `return_eval_trace`, title+ledger_id only); R4 pass = no rerank crash + fixtures complete, do NOT treat as production judge quality gate |
| Lane boundary | R4 uses `eval-synthesis.py --judge` from main merged code, NOT excluded JudgeBench judge-upgrade worktree |
| Doctor | No new index_drift failures |
| Daemons restarted | Watch/refine/monitor services resumed post-rebuild |

### Phase R5 — METADATA-without-vector anomalies (3 IDs)

Separate from bulk orphan set. Investigate `debug-nopatch` and two hash IDs before or after rebuild — may be test artifacts or stale METADATA without vectors. Do not block R3 if they are known debug rows; document disposition.

**R5 task-order entry:** Add T7-5b below to ensure these 3 anomalies receive explicit disposition (keep/delete/neutralize) before handoff.

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
| T7-2 | Verify rebuild CLI path in codebase (delete collection + reindex from export vs full index) | Cursor | T7-1 |
| T7-2b | Ryan: confirm Restic backup snapshot id (gate G2b) | Ryan | T7-2 |
| T7-3 | Ryan: merge P0 PR #141 (DONE) | Ryan | — |
| T7-4 | Ryan: **"go rebuild"** lock | Ryan | **T7-2, T7-2b**, G1 |
| T7-5 | R1–R4 execution (including daemon stop/restart) | Cursor | T7-4 |
| T7-5b | R5 disposition for 3 METADATA-without-vector anomalies | Cursor | T7-5 |
| T7-6 | Post-rebuild inventory + handoff | Cursor | T7-5b |

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

- **Ryan:** merge P0 PR #141 (DONE); then separate **"go rebuild"** for T7-5
- **Cursor:** R3 exact commands after T7-2 codebase verification

---

## T7-2 deliverable — rebuild CLI verification (Cursor, 2026-08-08)

**Status:** COMPLETE. **G3 / T7-4 may proceed** after G2b only — not before this section existed.

### Finding: no export-replay CLI (path A does not exist)

Codebase search confirms convmem has **no** `delete collection` + reindex-from-`knowledge_units.jsonl` command. There is no `delete_collection` call anywhere in the repo. `ingest.index()` upserts from source inventory via `processed.json`; it does **not** wipe HNSW orphans or reset a collection.

`knowledge_units.jsonl` is an append-only export used for drift checks (`doctor` `index_drift`) and repair classification — **not** a replay source into Chroma today. See `docs/audit-ledger-first/LEDGER-FAILURE-MATRIX.md` (full replay from ledger is future-state).

### Chosen path for tier L: **path B — full Chroma reset + source rescan**

| Step | Actor | Command / action |
|------|-------|------------------|
| R1 | Cursor | Re-run inventory + `convmem doctor` (baseline counts) |
| G4 verify | Cursor | `systemctl --user is-active convmem-watch.service convmem-refine.service convmem-monitor.timer` — all must be **inactive** before delete; stop with `systemctl --user stop convmem-watch.service convmem-refine.service convmem-monitor.timer` |
| G2 / G2b | Ryan | `bash scripts/restic-ensure-chroma-snapshot.sh` + confirm snapshot id |
| R2 | Ryan/Cursor | Restic `convmem-chroma` snapshot current (mandatory) |
| R3 pre | **Ryan** | Delete live Chroma store: `rm -rf ~/.local/share/convmem/chroma` (**hook-blocked for agents** — Ryan terminal only) |
| R3 | Ryan/Cursor | `rm ~/.local/share/convmem/processed.json` (**hook-blocked for agents**) |
| R3 | Cursor | `convmem inventory` then `convmem index` (full source rescan per `docs/RECOVER.md` § Index drift) |
| R4 | Cursor | `convmem doctor` (index_drift), inventory script, `pytest tests/test_chroma_flatten.py -q`, calibration run (informational gate per R4 caveat) |
| R4 | Cursor | Restart daemons: `systemctl --user start convmem-watch.service convmem-refine.service convmem-monitor.timer` |

**Why not processed.json wipe alone:** incremental `convmem index` without deleting Chroma leaves orphan HNSW vectors in place (646 `document=None` hits are HNSW−METADATA drift, not missing ingest). Collection delete is not exposed; **whole `chroma/` directory removal** is the supported nuclear option per RECOVER.md ("If Chroma itself is corrupt, restore from Restic … before reindexing" — equivalent to empty + reindex).

**Alternative if Restic has pre-drift snapshot:** `scripts/chroma_restore_drill.py` pattern — restore tagged snapshot to run dir is drill-only; for production use Restic restore of `convmem-chroma` tag to live path (Ryan-gated, follow RECOVER.md live-replacement rules).

### G4 verification (concrete)

```bash
# Must print inactive/inactive/inactive before R3 delete
systemctl --user is-active convmem-watch.service convmem-refine.service convmem-monitor.timer
pgrep -af "convmem (watch|refine|monitor)" || true
```

`convmem doctor --v1` includes `convmem-watch`, `convmem-refine`, `convmem-monitor.timer` systemd checks — use as secondary signal, not sole gate.

### R4 judge dependency (item 6)

`eval-synthesis.py --judge` on **merged `main`** post-#141 — not the excluded `fix-2026-08-07-judge-bench-judge-upgrades` worktree. Golden set: `/tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl` (5 fixtures). Pass = completes without rerank crash; not production judge quality.

### Blocks lifted

| Gate | After T7-2 |
|------|------------|
| T7-4 (go rebuild) | Unblocked pending **G2b** + **G4 verified** |
| T7-5 (R1–R4) | Unblocked after T7-4 |

