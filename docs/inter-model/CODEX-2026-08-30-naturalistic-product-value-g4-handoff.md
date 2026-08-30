# [Arc Naturalistic ConvMem product-value evaluation] G4 implementation handoff

**Date:** 2026-08-30
**Author:** Codex implementation and PR Steward lanes
**For:** Ryan merge disposition
**Authorization:** Ryan, 2026-08-30 (direct G4 implementation-lane assignment and handoff request)

---

## Resume state

| Field | Value |
|---|---|
| **State** | `PR_CI_PENDING_RYAN` |
| **Branch** | `feat/2026-08-30-naturalistic-product-value-g4` |
| **Review target** | `fa7d68b4b272a9802b0983c708800d6953ec45f8` |
| **Parent** | `91cda5c56d5f9dd86c0afda1c2a6fe1d353f575b` (frozen G3 implementation) |
| **Superseded G4 freeze** | `0e191c3197c7c950bdcbb7e1aaef0abe1bdc4e76` |
| **Push status** | Review target pushed to `origin`; later integration, documentation, and G1–G3 lint-gate cleanup commits preserve the reviewed G4 bytes |
| **PR** | [Combined G1–G4 delivery PR #255](https://github.com/alanmz-crypto/convmem/pull/255) is open against `main` |
| **Ryan GATE** | Ryan owns merge disposition after PR CI; no G5 or live-study authority |
| **Track A ingest** | `/home/lauer/.codex/sessions/2026/08/30/rollout-2026-08-30T02-03-24-01a0517a-e776-7d41-b11a-c38d8c977954.jsonl` (nudge attempted; active file changed during ingest and watch should retry after debounce) |

The implementation bytes reviewed remain exactly `fa7d68b`; do not substitute
a later carrier commit as the reviewed implementation SHA.

---

## Product goal and lane boundary

The parent arc asks whether ConvMem creates measurable product value during
ordinary work using prospective, sealed, symmetric C0/C1 evaluation rather than
retrospective anecdotes. G4 implements only the pre-live analysis/statistical
machinery: bounded episode scores, two-part co-primary aggregation,
sparse/scorer reliability records, and information-gate parameter slots.

**Why this review exists:** the original G4 implementation at `0e191c3` passed
its happy-path tests but silently accepted malformed and structurally ambiguous
inputs. Codex corrected those G4 contract defects at `fa7d68b` before independent
review.

## Exact review scope

Review the implementation delta:

```bash
git diff 91cda5c56d5f9dd86c0afda1c2a6fe1d353f575b..fa7d68b4b272a9802b0983c708800d6953ec45f8 -- \
  eval_naturalistic/__init__.py \
  eval_naturalistic/analysis.py \
  eval_naturalistic/analysis_fixtures.py \
  tests/test_naturalistic_analysis.py
```

The corrective commit `fa7d68b` specifically:

1. rejects non-finite, boolean, duplicate, orphaned, and invalid score inputs;
2. prevents duplicate episode/condition rows from overwriting or double-weighting results;
3. separates target-bearing opportunity from conditional evaluability and reports opportunity density;
4. keeps zero-target and target-present-but-not-evaluable episodes visible without invented treatment effects;
5. requires an explicit synthetic agreement tolerance and distinct scorer identities;
6. fails closed on missing scorer pairs, malformed gates, duplicate parameter slots, and post-result parameter mutation;
7. preserves the G4 ceiling: information-gate machinery cannot emit a product conclusion.

## Governing contracts

- [`ARCHITECTURE-naturalistic-product-value.md`](../plans/ARCHITECTURE-naturalistic-product-value.md), especially §§14–16 and §21.
- [`EXECUTION-naturalistic-product-value.md`](../plans/EXECUTION-naturalistic-product-value.md), especially G4 and T8–T10.
- G4 grant: synthetic analysis machinery only; no real scoring, product conclusion, or live numerical choices.

## What is explicitly out of scope

- G5 end-to-end dry-run or T0–T10 fixture campaign.
- Prospective episode collection, Agent A/B execution, live ConvMem use, or corpus mutation.
- Treatment assignment/randomization, trial runner, study controller, or environment qualification.
- Selection of meaningful-advantage, equivalence, precision, sparse, or scorer-reliability values.
- PR creation, merge, G6 freeze, or any live-study authorization.
- Repairing inherited G1–G3 lint/cycle debt or the unrelated full-suite Click failure at the exact G4 review SHA.

## Verification already run

At exact implementation SHA `fa7d68b`:

```text
python -m pytest -q \
  tests/test_naturalistic_contracts.py \
  tests/test_naturalistic_adjudication.py \
  tests/test_naturalistic_probe.py \
  tests/test_naturalistic_analysis.py

98 passed, 8 subtests passed
```

```text
python -m pylint \
  eval_naturalistic/analysis.py \
  eval_naturalistic/analysis_fixtures.py \
  tests/test_naturalistic_analysis.py

10.00/10
```

`compileall` and `git diff --check` also passed.

At PR tip after the mechanical G1–G3 cleanup, the same focused suite remains
green and the exact repository Pylint regression gate passes with no new or
increased findings against the PR base. The three G4 files reviewed by Kiro
remain byte-identical to `fa7d68b`.

## Integration state and remaining caveats

These are visible integration issues, not claimed G4 PASSes:

1. PR Steward cleanup removed the new G1–G3 Pylint findings and broke the real
   `eval_naturalistic.adjudication` ↔ `eval_naturalistic.contract_validate`
   import cycle. This was outside the exact-SHA G4 review but inside the
   combined PR's CI-delivery scope; it does not change the reviewed G4 bytes.
2. The original repository-wide pytest run was stopped at 11% after isolating its first
   failure: `tests/test_add_severity.py::AddSeverityTests::test_invalid_severity_rejected`
   received empty Click runner output. The complete naturalistic G1–G4 suite is
   green; PR #255 owns the current full-suite result.
3. The arc has architecture and execution plans but no required
   `docs/plans/STATUS-naturalistic-product-value.md`. Creating that arc brief is
   planning/governance work and was not folded into the bounded G4 corrective.

## Independent review outcome

Kiro issued **PASS** bound to exact implementation SHA
`fa7d68b4b272a9802b0983c708800d6953ec45f8` and independently reproduced the
focused verification. Kiro confirmed all six review questions: fail-closed
input handling; complete opportunity/evaluability accounting; one paired
episode contribution regardless of target count; honest pre-live scorer and
information slots; no reachable product conclusion; and no G5 mechanics.

The review also confirmed that the later carrier changed documentation only and
that the working-tree implementation files were byte-identical to `fa7d68b`.
The PASS does not authorize G5, merge, G6, or live-study work.

## Independent review questions

Kiro answered the following questions with `PASS` at exact SHA `fa7d68b`:

1. Do malformed, duplicate, orphaned, sparse, and non-evaluable inputs fail closed without becoming null or ordinary-confidence evidence?
2. Does co-primary A retain every prospective episode while distinguishing target opportunity from conditional evaluability?
3. Does co-primary B give each evaluable episode at most one paired contribution regardless of target count?
4. Are scorer agreement and information-gate slots honest pre-live records rather than hidden live parameter choices?
5. Can any path at this SHA emit a positive, negative, or null/equivalent product conclusion before later authorization?
6. Did the corrective remain entirely within G4 and avoid implementing G5 mechanics?

The exact-SHA PASS is now in Ryan/PR Steward disposition. It does not authorize
G5, merge, G6, or a live study.

## Leaving / picking up checklist

**Author (leaving):**

- [x] G4 implementation committed and pushed.
- [x] Focused verification recorded above.
- [x] This handoff and `LATEST.md` pointer prepared on the same branch.
- [ ] Arc STATUS update — no arc brief exists; procedural gap recorded above.

**Reviewer (completed):**

- [x] Verified branch ancestry and exact implementation SHA `fa7d68b`.
- [x] Read the architecture §§14–16 and execution G4/T8–T10 contracts.
- [x] Independently reproduced focused verification.
- [x] Returned exact-SHA `PASS` without crossing into G5.

## Handoff summary

**Who:** Codex corrected the bounded G4 implementation and is stewarding PR delivery; Kiro independently reviewed it; Ryan owns merge disposition.
**What:** Fail-closed analysis/statistical machinery at `fa7d68b`.
**When:** 2026-08-30, after the original `0e191c3` freeze was found to accept invalid inputs.
**Why:** Prevent malformed or ambiguous evidence from producing trustworthy-looking co-primary results.
**How:** Strict score/input validation, explicit opportunity/evaluability accounting, scorer independence, immutable parameter slots, and adversarial synthetic tests.

**TL;DR:** [Arc Naturalistic ConvMem product-value evaluation] Kiro PASSed exact
G4 SHA `fa7d68b`; the combined G1–G4 package is in PR Steward delivery, inherited
integration caveats remain explicit, and G5/live work is unauthorized.
