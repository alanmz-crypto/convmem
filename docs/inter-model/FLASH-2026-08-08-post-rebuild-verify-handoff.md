# Post-rebuild verify handoff — DeepSeek V4 Flash (V1–V6)

**Who:** DeepSeek V4 Flash, Tier 1, Crush lane (verified gates only; no corpus mutation)
**When:** 2026-08-09
**Parent:** [EXECUTION-chroma-reconcile-tier-l.md](../plans/EXECUTION-chroma-reconcile-tier-l.md) Phase R4 (T7)
**Brief:** [EXECUTION-post-rebuild-verify-flash-slices.md](../plans/EXECUTION-post-rebuild-verify-flash-slices.md)
**Verdict:** **GREEN**

## Verdict summary

All four R4 check rows are GREEN. The Chroma rebuild left the corpus clean: zero
orphans, zero tier-L risk, all unit and methodology tests pass, calibration
completes at 100% with no crash, and doctor shows no new critical failures or
index drift.

| Check                 | Slice | Result | Verdict |
| --------------------- | ----- | ------ | ------- |
| Inventory             | V2    | `orphans_hnsw_minus_metadata_count=0`, tier **S**, probe `none_ids` empty | **GREEN** |
| `test_chroma_flatten` | V3    | 4 passed, exit 0 | **GREEN** |
| Calibration           | V5    | completes, exit 0, 100% pass, judge negative control PASS | **GREEN** (no crash) |
| Doctor                | V4    | exit 0; index_drift 100% coverage / 0 active-only; no new critical | **GREEN** |

## /tmp evidence

| Artifact | Path |
| --- | --- |
| Orphan inventory JSON (V2) | `/tmp/chroma-orphan-inventory-20260809T022634Z.json` (15 MB) |
| Calibration log (V5) | `/tmp/post-rebuild-calibration-20260808T212706Z.log` |
| V1 doctor log | `/tmp/v1-doctor.txt` |
| V4 doctor log | `/tmp/v4-doctor.txt` |
| V3 pytest log | `/tmp/v3-flatten.txt` |

## Slice-by-slice detail

### V1 — Preflight (GREEN)
- `convmem doctor` exit 0 (2 non-fatal warnings: `embed_collection_identity` legacy
  metadata; `standing_register` DUE for `eval-judgebench.py` — JudgeBench, not R4)
- `convmem brief --stdout-only` exit 0: corpus **18,398 units / 2,388 summaries**
- `convmem unresolved` exit 0: **0 open**
- Branch: `fix/2026-08-09-judgebench-arch-lock-chroma-rebuild` (not `main`)

### V2 — Orphan inventory (GREEN)
- `python scripts/chroma_orphan_inventory.py --output /tmp/chroma-orphan-inventory-<UTCts>.json`
- `orphans_hnsw_minus_metadata_count`: **0**
- `reconcile_tier_recommendation`: **S**
- `distinct_none_ids_from_probes`: **0**; probe `none_ids` all empty
- `metadata_id_count`: 18,398; `metadata_minus_query_enumerated_count`: 0

### V3 — Flatten unit tests (GREEN)
- `pytest tests/test_chroma_flatten.py -q` → **4 passed in 0.35s**, exit 0

### V4 — Doctor drift (GREEN)
- `convmem doctor` exit 0
- index_drift: Chroma 18,398 active; JSONL 31,190 historical (18,398 overlap =
  **100% active coverage**; 0 active-only)
- No new critical failures. Same 2 non-fatal warnings as V1.

### V5 — Calibration (GREEN after one flag correction)
- Brief's exact command `eval-synthesis.py --judge --golden <file>` exits **2**:
  the current harness requires `--legacy` with `--judge` (legacy 1-5 judge path
  guard, `scripts/eval-synthesis.py:148`). This is a harness-argument requirement,
  **not** an ask/rerank crash.
- Corrected invocation used for evidence:
  `python scripts/eval-synthesis.py --judge --legacy --golden /tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl`
- **exit 0**; Golden answers: 5; **Pass rate 100.00%**; Abstain control **True**
- Judge mean **5.0** [NON-INDEPENDENT, informational — harness caveat]
- Judge negative control **PASS** (score=1, expected <3)
- All 5 rows PASS; no missing includes; all citations valid
- No regression vs baseline (model context changed — `--update-baseline` is a
  Cursor/Ryan decision, see next steps)

### J1 — Judge upgrades branch verify (optional, GREEN where runnable)
- `pytest tests/test_eval_methodology.py -q` on this branch → **9 passed in 0.06s**
- `tests/test_eval_judge.py` not present on this branch (absent-harness guard in
  the brief; not a failure). J1's dedicated run happens on
  `fix/2026-08-08-2026-08-09-judge-bench-upgrades` where the judge-upgrade fixtures
  live.

## Notes for Cursor / Ryan

1. **V5 `--legacy` in brief:** Fixed on `main` (#161) in `EXECUTION-post-rebuild-verify-flash-slices.md`.
2. **Baseline unchanged.** `eval-synthesis.py` reports "No regression vs baseline"
   and notes the model context changed (Ollama 0.30.11 → 0.32.3). Whether to
   `--update-baseline` is Cursor's rebaseline decision per the brief (YELLOW
   pathway — not triggered, but the option is open). No orphan absence caveat:
   orphans were 0, so the <100%-no-crash YELLOW path does not apply.
3. **Standing checks DUE** surfaced by doctor may reference removed `eval-judgebench.py` CLI
   or JudgeBench wiring — T2–T5 is on `main` (#155); remaining work is G3 gold lock
   ([`STATUS-judgebench.md`](../plans/STATUS-judgebench.md)), not R4 scope.

## Delegate-down wall — not attempted by Flash

Per the brief OFF-LIMITS table:
- Live corpus mutation (`~/.local/share/convmem/chroma`, `processed.json`) — Ryan only
- T3–T5 JudgeBench implementation — **merged #155** (historical wall at verify time)
- `eval_judge.py` / judge-prompt edits — Cursor if tests fail
- `convmem index` full corpus / `convmem refine` bulk — Ryan-gated
- `convmem-watch` / `monitor.timer` restart — Ryan authorizes first
- `convmem record`, merge to `main`, open PR — Ryan

## What GREEN unlocked (historical — see current state below)

At verify time (2026-08-09), GREEN unblocked JudgeBench execute and legacy-cal confidence work. **As of #155 and #161 on `main`:**

- JudgeBench T2–T5 code is **merged** — next gate is **Ryan G3** (gold) per [`STATUS-judgebench.md`](../plans/STATUS-judgebench.md).
- Judge prompt/confidence upgrade is on `main` (#153) — no open judge-upgrades branch required.
- Optional: Cursor/Ryan decide `--update-baseline` for Ollama 0.30.11 → 0.32.3 on the legacy 5-row calibration fixture.
- Standing checks `eval-provenance-wiring` and `eval-negative-control-coverage` remain **DUE** (JudgeBench lane).

---

## Close-out (2026-08-09 — Flash close-out executor)

**Who/What:** Crush lane (Tier 1) close-out slices C1–C5. No gates re-run — R4 evidence above stands.

| Slice | Action | Result |
|-------|--------|--------|
| C1 | Resume wip branch + rebase onto `origin/main` | Clean rebase |
| C2 | Fix V5 command in [EXECUTION-post-rebuild-verify-flash-slices.md](../plans/EXECUTION-post-rebuild-verify-flash-slices.md) | `--legacy` present |
| C3 | R4 cross-link + GREEN note in [EXECUTION-chroma-reconcile-tier-l.md](../plans/EXECUTION-chroma-reconcile-tier-l.md) | Done |
| C4 | [STATUS-chroma-reconcile-tier-l.md](../plans/STATUS-chroma-reconcile-tier-l.md) | Done |
| C5 | Close-out + Active STATUS entries in AGENTS.md / agent-protocol | Done |

**Landed on `main`:** squash-merge **#161** (`docs: land post-rebuild verify handoff and Chroma reconcile STATUS`). The wip branch is redundant with `main` for file content; use `main` + STATUS file for orientation.
