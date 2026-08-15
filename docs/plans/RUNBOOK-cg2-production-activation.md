# Operator runbook — CG-2 production activation (pre-soak)

**Scope:** Execute implementation on branch `feat/2026-08-15-cg2-production-activation`.
This runbook does **not** authorize production owner activation, gateway soak, or GC.

## Required grants (Ryan only)

| Step | Grant | What it unlocks |
|------|--------|-----------------|
| Execute | **DONE** — Kiro PASS; Ryan grant at execution plan `6a808f1` | T1–T5 implementation on feature branch |
| Legacy-only gateway soak | Separate exact operation grant | Production config pointing all owners `LEGACY` through serving repository |
| First generational owner | Named owner, SHA, rollback generation, activation grant | Fence + pointer publication for one owner |
| Automatic GC / compaction | Independent evidence + sub-grant | Physical deletion of inactive generations |

Silence on squash-merge = squash OK.

## Evidence artifacts (after Execute merge)

| Artifact | Path |
|----------|------|
| Architecture (locked) | `docs/plans/ARCHITECTURE-cg2-production-activation.md` @ `e680ce8` |
| Execution plan | `docs/plans/EXECUTION-cg2-production-activation.md` @ `6a808f1` |
| VERIFY (mechanical) | `docs/plans/VERIFY-cg2-production-activation.md` |
| Formal model map | `docs/plans/formal/cg2/README.md` |
| Property → test map | `cg2_property_map.py` |
| Rehearsal bundle | `cg2_rehearsal.py` (`collect_execute_evidence`) |

## Preflight

```bash
cd ~/Projects/convmem
convmem doctor
convmem brief --stdout-only
git fetch origin && git status
```

Require: `logical_projection` PASS, `source_reconciliation` fresh or WARN only,
no unpushed commits on the implementation branch before PR.

## Pause conditions (do not proceed to soak/canary)

- Any `logical_projection` FAIL or authority failure in doctor
- `source_reconciliation` stale beyond `max_reconciliation_staleness` (300s default)
- Mixed-mode proof gate FAIL (`authorized_cardinality` or `authority_safety`)
- Unexplained eval/gateway divergence during granted soak
- Missing embedding identity or ambiguous owner/alias state

## Rollback posture (first canary — when separately granted)

1. Record active `generation_id` and `previous_generation_id` from qualified pointer.
2. Republish retained previous generation via documented recovery path
   (`recover_active_pointer` — exact pointer bytes only).
3. Do **not** delete physical rows during rollback; GC remains disabled.
4. Re-run `convmem doctor` and VERIFY V6 checks.

## Mechanical verification (isolated — no live corpus)

```bash
python -m pytest tests/test_cg2_rehearsal.py tests/test_serving_index_repository.py \
  tests/test_mixed_mode_proof.py tests/test_logical_accounting.py \
  tests/test_source_reconciler.py -q
```

Full suite before PR:

```bash
python -m pytest -q
```

## What Execute deliberately did **not** do

- No production configuration change
- No legacy fence or production pointer publication
- No activation manifest
- No automatic inactive-generation deletion or Chroma queue surgery
