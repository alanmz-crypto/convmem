# [Arc Naturalistic ConvMem product-value evaluation] Kiro Re-Review Handoff — G5C Corrective Close

**Date:** 2026-08-31

**Author:** Cursor implementation lane

**For:** Kiro review lane (non-implementing; exact-tip re-review only)

**Authorization:** Ryan-granted G5C arc; follows Kiro `CORRECTIVE REQUIRED` at
`a77b50f` and [`KIRO-2026-08-31-naturalistic-g5c-corrective-handoff.md`](KIRO-2026-08-31-naturalistic-g5c-corrective-handoff.md).
Cursor applied the surgical fix; this packet requests **same-seed exact-tip
re-review**. **No merge, no G6 grant, no live study authority.**

---

## Resume state

| Field | Value |
|---|---|
| **State** | `READY_FOR_KIRO_REREVIEW` |
| **Prior review** | `CORRECTIVE REQUIRED` at `a77b50f7721862b119fc045f2eec24f40df74416` |
| **Corrective commit** | `a64b566a78daa0286a832cdbcdacca24c6239e2d` |
| **Accepted design carrier** | `c0890701b01f6a2d88a4e37a67bc06ab9551bac4` (ancestor of tip — confirmed) |
| **Implementation branch** | `fix/2026-08-30-naturalistic-g5c-corrective` |
| **Exact re-review revision** | `a64b566a78daa0286a832cdbcdacca24c6239e2d` |
| **Push status** | `pushed to origin` |
| **PR** | Not opened — Ryan retains merge authority after Kiro PASS |
| **Ryan GATE** | Kiro exact-tip PASS on `a64b566` → Ryan may open/merge PR; G6 remains closed (ChatGPT review + explicit grant) |
| **Classification** | `methodology_validation_not_product_evidence` |

## Context brief

**Who:** Cursor closed the single defect Kiro identified; Kiro owns independent
re-review at the corrective tip. Codex/Ryan own merge grant.

**What:** One-line import fix plus three targeted regression tests so the T0
structural validator **fails closed** on malformed decoded structure instead of
raising `NameError`.

**When:** First review at `a77b50f` found undefined `StructuralContractError` in
`contracts.py` (F821/E0602). Corrective landed at `a64b566` on top of review
handoff `17b1ca6`.

**Why:** A `NameError` on the structural-invalid path bypassed the design's
fail-closed T0 boundary; the fix must be verified closed, not assumed from the
diff size.

**How:** Re-run verification at exact `a64b566`, confirm the four
`StructuralContractError` sites resolve, confirm regression tests exercise the
**actual** boundary (decoded structural invalidity, not raw-byte decode in this
layer), confirm no disposition/scenario/authority/seed drift. Return `PASS`,
`FAIL`, or `CORRECTIVE REQUIRED`.

---

## Exact re-review scope

Review **only** commit `a64b566a78daa0286a832cdbcdacca24c6239e2d` (diff from
`17b1ca6` parent — **two files only**):

| File | Change |
|---|---|
| `eval_naturalistic/contracts.py` | Add `StructuralContractError` to top `base` import block |
| `tests/test_naturalistic_contracts.py` | Three regression tests in `ProspectiveManifestG5CTests` |

**Do not re-audit** the full G5C surface at `a77b50f` unless the corrective
diff introduces new behavior beyond closing the identified defect. Parent
implementation remains `a77b50f`; carrier `c089070` unchanged.

---

## Defect closure checklist (Kiro's corrective packet)

Confirm each item at `a64b566`:

1. **Import:** `StructuralContractError` imported from `eval_naturalistic.base`
   in `contracts.py` top import block (matches `digest.py` convention).
2. **Sites resolved:** Lines using `StructuralContractError` in
   `StageBoundaryPredicateResultV1.from_dict`, `StageBoundaryLedgerEntryV1.from_dict`,
   `OutcomeAxisRecordV1.from_dict`, and `except StructuralContractError` in
   `validate_prospective_manifest_structural` — no F821/E0602 on that symbol.
3. **Fail-closed path:** `validate_prospective_manifest_structural(body)` with
   decoded body where `header` is not a dict returns `NaturalisticValidation`
   with `ok=False` and non-empty `errors` — **does not raise**.
4. **Typed guard:** `StageBoundaryPredicateResultV1.from_dict({'predicate_name':
   'x', 'passed': 'notbool'})` raises `StructuralContractError` (not `NameError`).
5. **Boundary honesty:** Test uses structurally invalid **decoded** content
   (full policy fields present, bad `header` type) — not a bare `KeyError` from
   missing keys. Raw-byte decode responsibility explicitly documented as
   upstream (`test_raw_serialization_decode_not_contracts_layer`).
6. **No scope creep:** Diff does not touch disposition, ledger shapes, scenario
   IDs, seeds, paired-replay, bounds, precedence, or authority flags.

---

## Verification commands (re-run at exact tip)

```bash
git fetch origin fix/2026-08-30-naturalistic-g5c-corrective
git checkout a64b566a78daa0286a832cdbcdacca24c6239e2d

python -m pytest -q \
  tests/test_naturalistic_contracts.py \
  tests/test_naturalistic_adjudication.py \
  tests/test_naturalistic_probe.py \
  tests/test_naturalistic_analysis.py \
  tests/test_naturalistic_dry_run.py

ruff check --no-cache eval_naturalistic/contracts.py tests/test_naturalistic_contracts.py
python -m pylint eval_naturalistic/contracts.py | grep -E "StructuralContractError|E0602|rated at"
python -m compileall -q eval_naturalistic tests
python -m eval_naturalistic.dry_run
git diff --check
```

### Cursor-reported results at `a64b566` (2026-08-31)

| Check | Result |
|---|---|
| Focused pytest | **119 passed**, 8 subtests (+3 vs pre-corrective 116) |
| `eval_naturalistic.dry_run` | exit 0; **34** scenarios; `all_required_fail_closed_demonstrated=true`; `product_disposition_emitted=false`; `g6_authority_assumed=false` |
| `compileall` | OK |
| `git diff --check` | clean |
| Pylint `contracts.py` | **9.73/10**; no `E0602` on `StructuralContractError` |
| Ruff (2 changed files) | `StructuralContractError` F821 gone; remaining findings pre-existing style (`RUF012` etc. on unchanged patterns) |

### Manual repro (should match tests)

```python
from eval_naturalistic.contracts import (
    validate_prospective_manifest_structural,
    StageBoundaryPredicateResultV1,
)
from eval_naturalistic.base import StructuralContractError

body = {
    "header": "not-a-dict",
    "study_id": "study-synthetic-001",
    "frame_artifact_id": "frame-001",
    "frame_digest": "d" + "0" * 63,
    "information_slots": [],
    "opportunity_authority_rule": "policy-opportunity-authority-v1",
    "failure_reason_taxonomy": ["reason-protocol-invalid"],
    "missing_outcome_bounds_policy": "policy-missing-outcome-bounds-v1",
    "orthogonal_state_precedence": ["protocol_invalid"],
    "paired_replay_policy": "policy-paired-replay-v1",
    "scorer_integrity_policy": "policy-scorer-integrity-v1",
    "scorer_reliability_policy": "policy-scorer-reliability-v1",
}
check = validate_prospective_manifest_structural(body)
assert not check.ok and check.errors  # fail-closed, no raise

try:
    StageBoundaryPredicateResultV1.from_dict({"predicate_name": "x", "passed": "notbool"})
except StructuralContractError:
    pass
else:
    raise AssertionError("expected StructuralContractError")
```

---

## Required Kiro re-review questions

Return `PASS`, `FAIL`, or `CORRECTIVE REQUIRED` at exact `a64b566` and answer:

1. Is the `StructuralContractError` import present and are all four use sites
   free of F821/E0602 on that symbol?
2. Does `validate_prospective_manifest_structural` fail closed (return validation
   errors) on structurally invalid decoded content without raising?
3. Does the non-boolean `passed` guard raise `StructuralContractError` as intended?
4. Do the new tests exercise the claimed boundary (not a misleading KeyError-only
   fixture or invented raw-byte decode duty in `contracts.py`)?
5. Is the diff confined to the two-file allowlist with no disposition, scenario
   count, seed, ledger shape, or authority-flag drift?
6. Does `run_g4_safe_synthetic_example()` still return `conditional_effect=0.3`
   and `disposition=blocked_non_estimable`?

If `PASS`: G5C corrective arc is review-complete at methodology layer; Ryan may
merge the branch (squash OK). **G6 remains Ryan-gated.**

If `FAIL` or `CORRECTIVE REQUIRED`: return bounded file-scoped fixes only.

---

## What Kiro must NOT do

- No code, test, or config edits
- No merge, PR open, or `main` push
- No G6/T0 grant or product conclusion from synthetic fixtures
- No widening re-review into unrelated G5C mechanics unless corrective diff
  regresses them

---

## Related files

| Purpose | Path |
|---|---|
| Kiro corrective handoff (defect spec) | [`KIRO-2026-08-31-naturalistic-g5c-corrective-handoff.md`](KIRO-2026-08-31-naturalistic-g5c-corrective-handoff.md) |
| First Kiro review handoff (`a77b50f`) | [`CURSOR-2026-08-31-naturalistic-g5c-kiro-review-handoff.md`](CURSOR-2026-08-31-naturalistic-g5c-kiro-review-handoff.md) |
| Original G5C implementation grant | [`CODEX-2026-08-30-naturalistic-g5c-cursor-handoff.md`](CODEX-2026-08-30-naturalistic-g5c-cursor-handoff.md) |
| Arc brief | [`../plans/STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md) |

---

## Picking up (Kiro)

1. Read this file and [`KIRO-2026-08-31-naturalistic-g5c-corrective-handoff.md`](KIRO-2026-08-31-naturalistic-g5c-corrective-handoff.md).
2. `git checkout a64b566a78daa0286a832cdbcdacca24c6239e2d`
3. Re-run verification commands; do not trust chat claims alone.
4. Prefer **same reviewer seed** for continuity (Kiro corrective handoff § Re-review contract).
5. Return verdict + six answers; Ryan owns merge.

**TL;DR:** [Arc Naturalistic] Re-review exact tip `a64b566` — one import + three
tests closing the T0 `NameError` defect from `a77b50f`. Confirm fail-closed
behavior and no drift; return PASS for Ryan merge. G6 stays closed.
