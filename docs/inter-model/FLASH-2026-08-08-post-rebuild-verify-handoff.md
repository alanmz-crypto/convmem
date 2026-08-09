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

1. **V5 `--legacy` correction is a brief fix.** The `EXECUTION-post-rebuild-verify-flash-slices.md`
   V5 command should become
   `python scripts/eval-synthesis.py --judge --legacy --golden /tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl`.
   FLASH did not edit the brief (OFF-LIMITS: tracked-file edits are the V6 handoff
   only); this is a Cursor-or-Ryan change.
2. **Baseline unchanged.** `eval-synthesis.py` reports "No regression vs baseline"
   and notes the model context changed (Ollama 0.30.11 → 0.32.3). Whether to
   `--update-baseline` is Cursor's rebaseline decision per the brief (YELLOW
   pathway — not triggered, but the option is open). No orphan absence caveat:
   orphans were 0, so the <100%-no-crash YELLOW path does not apply.
3. **Standing checks DUE** surfaced by doctor reference `eval-judgebench.py`
   provenance/negative-control wiring. That is JudgeBench T3/T4-adjacent work
   (Cursor lane), out of R4 scope — surfaced for completeness.

## Delegate-down wall — not attempted by Flash

Per the brief OFF-LIMITS table:
- Live corpus mutation (`~/.local/share/convmem/chroma`, `processed.json`) — Ryan only
- T3–T5 JudgeBench implementation (`eval_provenance`, runner, legacy shim) — Cursor
- `eval_judge.py` / judge-prompt edits — Cursor if tests fail
- `convmem index` full corpus / `convmem refine` bulk — Ryan-gated
- `convmem-watch` / `monitor.timer` restart — Ryan authorizes first
- `convmem record`, merge to `main`, open PR — Ryan

## What GREEN unlocks

- Cursor may proceed JudgeBench T3–T5 on `main` (`eval_provenance.py`, runner,
  legacy shim) per [EXECUTION-judgebench.md](../plans/EXECUTION-judgebench.md)
  and [VERIFY-judgebench.md](../plans/VERIFY-judgebench.md) CHK-004..008.
- Judge upgrades PR (`fix/2026-08-08-2026-08-09-judge-bench-upgrades`): review the
  `eval_judge.py` diff and draft PR title/body once J1 is green on that branch.
- Optional: Cursor decides `--update-baseline` to fold the Ollama 0.32.3 context
  into the calibration baseline.

---

## Close-out (added 2026-08-09 by Flash close-out executor)

**Who/What:** Crush lane (Tier 1) running close-out slices C1–C5 from [paste_1.txt close-out plan](../../paste_1.txt). No gates were re-run — R4 evidence above stands.

| Slice | Action | Result |
|-------|--------|--------|
| C1 | Resume wip branch + rebase onto `origin/main` | Clean rebase; 4 commits ahead |
| C2 | Fix V5 command in [EXECUTION-post-rebuild-verify-flash-slices.md](../plans/EXECUTION-post-rebuild-verify-flash-slices.md) | **Already correct on branch** — commit `a89c933` had `--legacy` already applied; no new edit needed |
| C3 | Add R4 cross-link + GREEN note to [EXECUTION-chroma-reconcile-tier-l.md](../plans/EXECUTION-chroma-reconcile-tier-l.md) | Done — line 106 |
| C4 | Write [STATUS-chroma-reconcile-tier-l.md](../plans/STATUS-chroma-reconcile-tier-l.md) from the JudgeBench template | Done — new file, 10 sections |
| C5 | This close-out section + AGENTS.md / `config/agent-protocol.md` Active STATUS entries | Done |

**Branch:** `wip/2026-08-08-2026-08-08-post-rebuild-verify`
**Commits ahead of `origin/main`:** see `git log origin/main..HEAD --oneline` in the PR body below.
**Push status:** pushed to `origin/wip/2026-08-08-2026-08-08-post-rebuild-verify` after each commit.

### PR offer to Ryan (do not auto-create)

**Title:** `docs: land post-rebuild verify handoff and Chroma reconcile STATUS`

**Body (squash-merge):**

> Ryan gets GREEN R4 evidence on `main`, the corrected V5 `--legacy` command in the Flash brief, and a STATUS arc brief so the next model orients without re-reading the T7 thread.
>
> **What:** closes out the Chroma Reconcile Tier L arc (T7 R4, post-rebuild verify).
> **Who:** Crush lane (Tier 1 close-out), under plan delegated in `paste_1.txt`.
> **When:** 2026-08-09.
> **Why:** the wip branch held the GREEN handoff unmerged; the parent arc lacked a STATUS file so the next model had no single-doc orientation.
> **How:** adds `STATUS-chroma-reconcile-tier-l.md` (JudgeBench template), appends R4 GREEN cross-link to the parent plan, lists the new STATUS in `AGENTS.md` + `config/agent-protocol.md`. No code, no gates re-run.
>
> **Merge reading:**
> - [`docs/plans/STATUS-chroma-reconcile-tier-l.md`](../plans/STATUS-chroma-reconcile-tier-l.md)
> - [`docs/inter-model/FLASH-2026-08-08-post-rebuild-verify-handoff.md`](FLASH-2026-08-08-post-rebuild-verify-handoff.md) (this file)
> - [`docs/plans/EXECUTION-chroma-reconcile-tier-l.md`](../plans/EXECUTION-chroma-reconcile-tier-l.md) (R4 section)
>
> **TL;DR:** lands the GREEN verify evidence + arc STATUS on `main` so the Chroma Reconcile Tier L arc can be marked closed.
