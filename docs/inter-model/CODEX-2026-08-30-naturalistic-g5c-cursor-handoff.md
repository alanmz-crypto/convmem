# [Arc Naturalistic ConvMem product-value evaluation] Implementation Handoff — G5C Corrective

**Date:** 2026-08-30
**Author:** Codex architecture/planning lane
**For:** Cursor implementation lane
**Authorization:** Ryan, 2026-08-30 — bounded G5C corrective implementation grant

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` |
| **Accepted design carrier** | `c0890701b01f6a2d88a4e37a67bc06ab9551bac4` |
| **Design payload** | Kiro PASS at `b6a1ccff82ef2456d5b65be122e2e714f84f5ad2`; wording-only corrections at `fde840b` |
| **Required implementation branch** | `fix/2026-08-30-naturalistic-g5c-corrective` |
| **Tip SHA** | Not created; Cursor must start the branch/worktree |
| **Push status** | Not created; push immediately after every commit |
| **PR** | Not opened; Ryan retains merge authority |
| **Ryan GATE** | G5C implementation only is granted. Stop at exact-tip Kiro review; G6/T0 and all live work remain closed. |

## Context brief

**Who:** Ryan granted Cursor one bounded implementation slice after Kiro PASSed
the accepted methodology design. Codex owns this handoff only; Cursor owns code.

**What:** Repair G5's synthetic methodology composition so every T0–T10
boundary proves the artifact guarantees consumed by the next stage, while also
implementing the accepted missingness, denominator, disposition, and paired-
replay mechanics.

**When:** The landed G5 code on `main` can label grouped `T0_T2` successful even
though its nominal frame carries only two of eight required information slots.
The methodology verdict therefore remains C despite the historical G5 merge.

**Why:** A downstream stage or isolated validator must not mask an incomplete
prospective state, and treatment-dependent capture/evaluability must not create
a favorable denominator silently.

**How:** Work only in the named files below, with synthetic fixtures only. Push
the exact implementation tip and stop for fresh independent Kiro review.

## Branch and starting-point contract

Create a new isolated worktree/branch using the repository workflow:

```text
convmem work start fix naturalistic-g5c-corrective --worktree
```

Before the first edit, fast-forward that new branch to the accepted carrier
`c0890701b01f6a2d88a4e37a67bc06ab9551bac4` from
`origin/plan/2026-08-30-naturalistic-g5-corrective-amendment`. If a clean
fast-forward is impossible, stop and report the base conflict; do not rebase or
reconstruct the accepted design silently. Verify the accepted carrier is an
ancestor of the implementation tip before every handoff. Push the
fast-forwarded implementation branch with an explicit refspec before the first
edit so the accepted base is backed up remotely.

```text
branch="fix/2026-08-30-naturalistic-g5c-corrective"
git push -u origin "$branch:refs/heads/$branch"
```

## Strict write allowlist

Cursor may modify only:

- `eval_naturalistic/contracts.py`
- `eval_naturalistic/base.py`
- `eval_naturalistic/enums.py`
- `eval_naturalistic/digest.py`
- `eval_naturalistic/adjudication.py`
- `eval_naturalistic/probe_construction.py`
- `eval_naturalistic/analysis.py`
- `eval_naturalistic/dry_run.py`
- `eval_naturalistic/dry_run_mechanics.py`
- `eval_naturalistic/adjudication_fixtures.py`
- `eval_naturalistic/analysis_fixtures.py`
- `eval_naturalistic/probe_fixtures.py`
- `tests/test_naturalistic_contracts.py`
- `tests/test_naturalistic_adjudication.py`
- `tests/test_naturalistic_probe.py`
- `tests/test_naturalistic_analysis.py`
- `tests/test_naturalistic_dry_run.py`

The grant does **not** include `eval_naturalistic/fixtures.py`,
`eval_naturalistic/contract_validate.py`, package initializers, documentation,
configuration, scripts, runtime integrations, corpus/index code, or any other
test. If the accepted behavior cannot be implemented within this allowlist,
stop and request a revised grant.

## Integration points

- `eval_naturalistic/contracts.py` — durable synthetic methodology records for
  prospective manifest completeness, arm-level capture/evaluability,
  orthogonal state/reason records, and `StageBoundaryLedger`.
- `eval_naturalistic/digest.py` and `base.py` — canonical serialized-byte and
  structural validation primitives. Canonical serialization/hash primitives
  may be shared; stage builders and their success flags are not validation
  authority.
- `eval_naturalistic/enums.py` — fixed state/reason vocabularies required to
  distinguish valid missingness, invalidity, scorer integrity, and reliability.
- `eval_naturalistic/adjudication.py` — sealed, arm/result-blind registry and
  immutable episode-opportunity identity.
- `eval_naturalistic/analysis.py` — complete-pair effect, deterministic bounds,
  process accounting, orthogonal-state precedence, and structured result tuple.
- `eval_naturalistic/dry_run_mechanics.py` — paired sealed-state replay and
  per-boundary synthetic validators.
- `eval_naturalistic/dry_run.py:run_g5_end_to_end` — composition orchestrator;
  grouped statuses become summaries of individual T0–T10 ledger entries.

## Required behavior

### 1. Structural prospective completeness

- Start the corrective synthetic fixture with every required information slot
  explicitly `PENDING`.
- Define the complete prospective manifest content required by the accepted
  architecture, including the original eight information slots plus the
  opportunity-authority rule, fixed failure/reason taxonomy, missing-outcome
  bounds policy, orthogonal-state precedence, paired-replay policy, and scorer
  integrity/reliability policy.
- Validate canonical serialized content, not mutable builder objects,
  `stage_ok`, `.ok`, or a completeness boolean.
- Reject absent, empty, placeholder, inconsistent, falsely marked-complete, or
  non-applicable-without-rule content.
- Re-derive and compare the digest of the exact serialized artifact handed to
  the next stage. A post-freeze byte edit or different handed-off artifact is
  an integrity failure, not ordinary missingness.
- The execution path must refuse to advance without a valid synthetic logged
  freeze digest. Do not create a real T0 freeze or choose live values.

### 2. Immutable opportunity authority

- Reuse the sealed raw-evidence `TargetRegistry` as the sole membership and
  denominator authority; do not create a competing opportunity subsystem.
- Assign one immutable episode-opportunity identity per target-bearing episode.
  Target rows remain secondary inputs to within-episode aggregation.
- Registry construction and validation cannot inspect condition, ConvMem
  capture, retrieval results, trial evidence, evaluability, scores, or outcomes.
- Every downstream record references registry identity/digest and cannot mint,
  delete, substitute, or reclassify membership.

### 3. Separate outcome axes and failure classes

Record separately:

1. natural ConvMem capture diagnostic;
2. C0/C1 trial-evidence capture;
3. C0/C1 score evaluability;
4. protocol/environment/scorer integrity;
5. scorer reliability.

Use a fixed synthetic reason vocabulary. Only valid post-treatment outcome
missingness may enter bounds. Protocol, isolation, replay-environment, lineage,
registry, freeze, or scorer-integrity failures are invalid and must never
receive a latent score or be bounded away. Below-threshold but valid scorer
reliability is blocked, not invalid; an isolated secondary-only disagreement
may be diagnostic.

### 4. Deterministic bounds and structured result

- Preserve the complete registry denominator and report per-arm trial-capture
  and score-evaluability rates/reasons before the effect.
- Compute the complete-pair C1−C0 episode effect only where both valid arm
  scores exist.
- Compute deterministic worst/best-case bounds over the existing normalized
  score support `[0.0, 1.0]` for valid missing episode contributions.
- The synthetic bounds path must degrade as: complete-pair estimate → bounded
  interval → inconclusive interval. A failure-rate tolerance cannot replace the
  bounds or become an estimator cliff.
- Emit a structured synthetic result containing opportunity prevalence,
  complete-pair effect/bounds, and full process/failure accounting. Do not emit
  an authoritative scalar or product disposition.
- Preserve `run_g4_safe_synthetic_example()` and existing G4 fixture semantics;
  this grant is not a retroactive G4 redesign or unrelated refactor.

### 5. Orthogonal disposition precedence

Record protocol validity, information sufficiency, missingness/comparability,
scorer integrity, and scorer reliability separately. Derive the synthetic
non-product disposition/reasons in this precedence:

1. protocol/isolation/lineage/registry/freeze invalidity;
2. environment or scorer-integrity invalidity;
3. insufficient opportunity or information;
4. below-threshold scorer reliability or inconclusive valid-missingness bounds;
5. effect interpretation would be eligible only in a later authorized study.

G5C must remain `methodology_validation_not_product_evidence` and must not emit
positive, null/equivalent, negative, or any other product conclusion.

### 6. Paired replay symmetry

- Model C0/C1 as fresh replays from one sealed synthetic pre-trial state.
- Mechanically compare model/build/settings, prompt, ordinary tools, readable
  roots, budget/stopping policy, mutable state/reset evidence, and external-
  service replay/exclusion evidence.
- The only intended difference is C1 access to the frozen synthetic ConvMem
  surface.
- Reject shared mutable session/cache/database state, non-replayed external
  state, condition-specific repair/retry, changed execution order, or any other
  environment difference before scoring.
- Keep execution-order randomization distinct from scorer-presentation order.

### 7. Individual T0–T10 boundary ledger

Add a synthetic `StageBoundaryLedger` entry for each individual T0 through T10
boundary. Every entry binds:

- stage identity;
- canonical input artifact digest;
- required predicates and their results;
- validator identity/version;
- output artifact digest;
- guarantees exported to the next stage;
- next-stage assumptions;
- failure reason(s).

`T0_T2`, `T3_T5`, `T6_T7`, and `T8_T10` may remain compatibility summaries,
but each summary must be derived from its individual entries. No group-level
success flag may substitute for boundary evidence.

## Required adversarial synthetic controls

Retain every existing required G5 scenario and add at least:

1. incomplete nominal T0_T2 frame from genuine all-`PENDING` slots;
2. empty/placeholder slot falsely marked complete;
3. individual corruption of each T0–T10 stage input;
4. happy-path assertion of every next-stage guarantee, not just return status;
5. serialized bytes changed after freeze;
6. downstream handoff artifact differing from the logged artifact;
7. validator import/boundary proof: no execution, capture, or scoring builder is
   used as prospective completeness authority;
8. registry rule depending on arm, capture, retrieval, or results;
9. asymmetric valid C0/C1 capture/evaluability with deterministic bounds;
10. valid missing outcome and protocol/environment invalidity in the same
    fixture, proving only the former enters bounds and invalidity wins;
11. combined protocol invalidity, sparse information, scorer failure, and
    apparently favorable effect, proving precedence;
12. paired-replay mismatch in roots, shared state/cache/database, external
    response, or frozen execution order;
13. scorer-integrity failure distinct from below-threshold valid reliability;
14. synthetic-only guard proving no natural locator, ConvMem data path, Agent
    runner, live scorer, or G6 authority is imported or resolved.

## Test and verification requirements

Run and report exact commands and results:

```text
python -m pytest -q \
  tests/test_naturalistic_contracts.py \
  tests/test_naturalistic_adjudication.py \
  tests/test_naturalistic_probe.py \
  tests/test_naturalistic_analysis.py \
  tests/test_naturalistic_dry_run.py

ruff check --no-cache \
  eval_naturalistic/contracts.py \
  eval_naturalistic/base.py \
  eval_naturalistic/enums.py \
  eval_naturalistic/digest.py \
  eval_naturalistic/adjudication.py \
  eval_naturalistic/probe_construction.py \
  eval_naturalistic/analysis.py \
  eval_naturalistic/dry_run.py \
  eval_naturalistic/dry_run_mechanics.py \
  eval_naturalistic/adjudication_fixtures.py \
  eval_naturalistic/analysis_fixtures.py \
  eval_naturalistic/probe_fixtures.py \
  tests/test_naturalistic_contracts.py \
  tests/test_naturalistic_adjudication.py \
  tests/test_naturalistic_probe.py \
  tests/test_naturalistic_analysis.py \
  tests/test_naturalistic_dry_run.py

python -m compileall -q eval_naturalistic tests
python -m eval_naturalistic.dry_run
git diff --check
```

Run `python -m pylint` over every changed Python file in the allowlist and
report the exact invocation and score. Do not weaken lint/test configuration or
modify files outside the allowlist to make a check pass.

## Acceptance criteria

- [ ] Only allowlisted files changed.
- [ ] Accepted design carrier `c089070` is an ancestor of the implementation tip.
- [ ] Nominal `run_g5_end_to_end()` cannot report success from an incomplete or
      placeholder prospective frame.
- [ ] Individual T0–T10 ledger entries prove every boundary guarantee; grouped
      statuses are derived summaries only.
- [ ] Sealed registry identity remains the sole episode-opportunity authority.
- [ ] Natural capture, per-arm evidence capture, and per-arm evaluability remain
      separate and fully accounted.
- [ ] Deterministic bounds include only valid missing outcomes and preserve the
      fixed episode denominator.
- [ ] Invalidity/reliability/reason precedence is deterministic and tested.
- [ ] Paired replay has exactly one intended treatment difference and fails
      closed on every tested asymmetry/carryover.
- [ ] Every accepted adversarial scenario is named, deterministic, and
      synthetic-only.
- [ ] Existing G1–G5 focused tests remain green; the G4 `0.3` fixture remains
      descriptive and blocked from product interpretation.
- [ ] No product disposition, live parameter value, G6/T0 authority, corpus
      access, Agent A/B, or live scorer path is added.
- [ ] Branch is committed and pushed after every commit.
- [ ] Cursor supplies an exact changed-file diff, command-by-command evidence,
      branch name, full tip SHA, and push status.
- [ ] Cursor stops for fresh independent Kiro review at that exact tip; no merge.

## Explicit exclusions

- No G6/T0 or live-study activity.
- No live parameter selection or freeze.
- No natural evidence, corpus/index access, Agent A/B run, or scoring.
- No product interpretation or disposition.
- No target-directed capture/index work.
- No retroactive G4 claim and no unrelated G1–G4 refactor.
- No edits outside the strict allowlist.
- No PR merge, main push, or authority to continue after implementation.

## Related files

| Purpose | Path |
|---|---|
| Accepted architecture | [`../plans/ARCHITECTURE-naturalistic-product-value.md`](../plans/ARCHITECTURE-naturalistic-product-value.md) |
| Accepted execution contract | [`../plans/EXECUTION-naturalistic-product-value.md`](../plans/EXECUTION-naturalistic-product-value.md) |
| Current arc state | [`../plans/STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md) |
| Kiro design-review scope | [`CODEX-2026-08-30-naturalistic-g5-corrective-kiro-review-handoff.md`](CODEX-2026-08-30-naturalistic-g5-corrective-kiro-review-handoff.md) |
| Historical landed G5 handoff | [`CURSOR-2026-08-30-naturalistic-product-value-g5-handoff.md`](CURSOR-2026-08-30-naturalistic-product-value-g5-handoff.md) |

## Cursor departure checklist

- [ ] Commit and push the implementation branch with explicit refspec.
- [ ] Confirm the worktree is clean and upstream equals the local tip.
- [ ] Report `git diff --stat origin/main...HEAD` and the exact changed-file list.
- [ ] Report `git log origin/main..HEAD --oneline` so the full carrier and
      implementation history is visible without reconstruction.
- [ ] Report every focused test/lint command and result.
- [ ] Index the Cursor session transcript under Track A.
- [ ] Update no planning/status file; return evidence in the implementation
      handoff/chat because documentation is outside the write allowlist.
- [ ] Stop for fresh exact-tip Kiro review. Ryan alone merges or grants later work.

**TL;DR:** [Arc Naturalistic ConvMem product-value evaluation] Implement only
the accepted synthetic G5C corrective within the strict evaluator/test
allowlist, starting from `c089070`. Prove structural completeness, fixed
registry authority, valid-only missingness bounds, deterministic precedence,
paired replay symmetry, and individual T0–T10 boundary accounting; then push
and stop for fresh Kiro review. G6/live/product authority remains closed.
