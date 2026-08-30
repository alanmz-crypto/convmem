# [Arc Naturalistic ConvMem product-value evaluation] G5 synthetic dry-run handoff

**Date:** 2026-08-30
**Author:** Cursor (G5 implementer)
**For:** Kiro independent G5 review
**Authorization:** Ryan, 2026-08-30 (explicit G5 execution grant; synthetic end-to-end dry-run only)

---

## Resume state

| Field | Value |
|---|---|
| **State** | `READY_FOR_PR` |
| **Branch** | `feat/2026-08-30-naturalistic-g5-dry-run` |
| **Worktree** | `~/.local/share/convmem/worktrees/feat-2026-08-30-naturalistic-g5-dry-run` |
| **Parent SHA** | `a1128b92d2b02aa77a96524ba353ca0da025ce01` (`origin/main` at grant time) |
| **Implementation SHA** | `23b2495927a9891070c7c294e45bdb641eaab352` |
| **Branch tip SHA** | `e249fa3901f6f7de23041be344136b0bdd97c20c` (docs stamp only) |
| **Push status** | pushed to `origin` after freeze |
| **PR** | [PR #259](https://github.com/alanmz-crypto/convmem/pull/259) |
| **Ryan GATE** | After Kiro exact-SHA PASS, Ryan owns whether to merge G5. **No G6 grant is contained here.** |
| **Classification** | `methodology_validation_not_product_evidence` |

---

## What to review

G5 exercises the landed G1–G4 evaluation machinery as a **synthetic end-to-end dry-run**. It tests whether the pipeline behaves correctly across T0–T10 gates.

G5 does **not** test whether ConvMem provides product value. A favorable synthetic C1−C0 effect of `0.3` is a descriptive fixture result only.

**Why this exists:** Ryan authorized G5 so the methodology substrate can be proven fail-closed before any prospective study freeze.

## Exact review scope

Review the implementation delta from parent `a1128b92d2b02aa77a96524ba353ca0da025ce01` to the frozen tip:

```bash
git diff a1128b92d2b02aa77a96524ba353ca0da025ce01..HEAD -- \
  eval_naturalistic/__init__.py \
  eval_naturalistic/dry_run.py \
  eval_naturalistic/dry_run_mechanics.py \
  tests/test_naturalistic_dry_run.py \
  docs/plans/STATUS-naturalistic-product-value.md \
  docs/inter-model/LATEST.md \
  docs/inter-model/STATUS.md \
  docs/inter-model/CURSOR-2026-08-30-naturalistic-product-value-g5-handoff.md
```

G1–G4 implementation files are reused, not rewritten. Confirm the G4 safe synthetic example still yields:

```text
aggregation_ok: True
conditional_effect: 0.3
paired_episodes: 2
disposition: blocked_non_estimable
all_slots_frozen: False
```

## Governing contracts

- [`ARCHITECTURE-naturalistic-product-value.md`](../plans/ARCHITECTURE-naturalistic-product-value.md)
- [`EXECUTION-naturalistic-product-value.md`](../plans/EXECUTION-naturalistic-product-value.md), especially G5 and the §16 adversarial set
- [`STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md)

## What is explicitly out of scope

- Natural episode collection, Agent A/B campaigns, C0/C1 prospective study execution
- ConvMem corpus access or mutation; ordinary user work as study material
- Selection or freeze of live study thresholds / G6 parameters
- Empirical claims about ConvMem; T10 product disposition
- Merge, force-push, production deployment
- A live study controller or trial runner (T5–T7 checks here are synthetic mechanical packages only)

## Synthetic scenarios exercised

1. **`g4_safe_synthetic_example`** — existing G4 paired fixture (`G4_SYNTHETIC_FIXTURE_SEED = 20260830`); effect `0.3`; blocked.
2. **`g5_end_to_end_happy_path`** — T0–T10 chain with two target-bearing episodes plus one zero-target episode; same `0.3` paired effect; zero remains in the opportunity denominator; scorer gate unfrozen; disposition `blocked_non_estimable`.
3. **EXECUTION §16 adversarial named controls** plus malformed/duplicate/orphan:
   capture-dependent exclusion retained; unsealed edit rejected; answer and source leakage rejected; adjudicator/probe-author collision rejected; C0/C1 tool asymmetry rejected; reused Agent-B context rejected; target-directed reindex rejected; missing zero-target roster fails; target-rich episodes contribute one score; post-result threshold fill rejected; controller-as-agent rejected; low scorer reliability does not pass a live threshold; all-zero window is descriptive not null; duplicate/orphan/malformed inputs fail closed; pending information-gate slots block terminal empirical disposition.

No new experimental/prospective-study seed was introduced. The checked-in G4 fixture seed is reused.

## Verification already run

```bash
python -m pytest -q \
  tests/test_naturalistic_contracts.py \
  tests/test_naturalistic_adjudication.py \
  tests/test_naturalistic_probe.py \
  tests/test_naturalistic_analysis.py \
  tests/test_naturalistic_dry_run.py
```

```text
109 passed, 8 subtests passed
```

```bash
python -m pylint \
  eval_naturalistic/__init__.py \
  eval_naturalistic/dry_run.py \
  eval_naturalistic/dry_run_mechanics.py \
  tests/test_naturalistic_dry_run.py
```

```text
10.00/10
```

Also: `python -m eval_naturalistic.dry_run` (JSON verification record, exit 0),
`python -m compileall -q eval_naturalistic tests/test_naturalistic_dry_run.py`,
and `git diff --check`.

## Independent review questions

Answer each with `PASS` or `FAIL` at the exact candidate SHA:

1. Is every G5 input synthetic, with no naturalistic episode, corpus access, or ordinary-work study material?
2. Does a favorable synthetic C1−C0 effect of `0.3` remain descriptive and terminate as `blocked_non_estimable` with `all_slots_frozen: False`?
3. Do zero-target episodes remain in the opportunity denominator, and do target-rich episodes contribute only one within-episode score?
4. Are the required fail-closed controls demonstrated (malformed, duplicate, orphaned, unsealed edit, leakage, role collision, asymmetry, reused context, reindex, missing zero, post-result threshold change, controller-as-agent, low reliability, pending slots)?
5. Does scorer reliability pass a live threshold, or does G5 correctly refuse that pass unless a threshold was separately authorized and frozen?
6. Can G5 emit a positive, negative, or null/equivalent product conclusion, or assume G6 authority?
7. Are the new T5–T7 checks synthetic mechanical packages only, and not a live Agent A/B runner or study controller?

## Independent review outcome

Kiro issued **PASS** bound to exact implementation SHA `23b2495927a9891070c7c294e45bdb641eaab352` on 2026-08-30.
All seven review questions passed. Verification independently reproduced:
109 passed + 8 subtests; Pylint 10.00/10; `python -m eval_naturalistic.dry_run`
exit 0 (20/20 scenarios demonstrated).

A PASS does not authorize G6 or a product conclusion. Ryan owns merge.

## Leaving / picking up checklist

**Author (leaving):**

- [x] G5 dry-run implemented on an isolated worktree/branch from `origin/main`.
- [x] Focused verification recorded above.
- [x] This handoff, `LATEST.md`, and arc STATUS updated.
- [x] Exact tip SHA stamped after freeze commit and pushed.

**Reviewer (Kiro):**

- [x] Verify parent SHA `a1128b92d2b02aa77a96524ba353ca0da025ce01` and exact candidate tip.
- [x] Read architecture/execution G5 and STATUS.
- [x] Independently reproduce focused pytest and pylint.
- [x] Return exact-SHA `PASS` without crossing into G6.

## Handoff summary

**Who:** Cursor implemented G5; Kiro independently reviews; Ryan owns merge and any later G6 grant.
**What:** Synthetic T0–T10 dry-run of G1–G4 evaluation machinery.
**When:** 2026-08-30, after Ryan's explicit G5 grant.
**Why:** Prove the evaluation pipeline fail-closes before any prospective study.
**How:** Hermetic fixtures, G4 seed reuse, named adversarial controls, and an explicit methodology-validation classification.

**TL;DR:** [Arc Naturalistic ConvMem product-value evaluation] G5 is Kiro-PASS at
exact SHA `23b2495927a9891070c7c294e45bdb641eaab352` and ready for Ryan merge. Methodology validation, not product
evidence. G6 is not authorized.
