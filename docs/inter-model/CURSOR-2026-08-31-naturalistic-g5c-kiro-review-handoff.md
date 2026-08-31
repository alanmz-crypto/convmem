# [Arc Naturalistic ConvMem product-value evaluation] Kiro Review Handoff — G5C Implementation

**Date:** 2026-08-31

**Author:** Cursor implementation lane

**For:** Kiro review lane (non-implementing; exact-tip sign-off only)

**Authorization:** Ryan granted bounded G5C implementation 2026-08-30 via
[`CODEX-2026-08-30-naturalistic-g5c-cursor-handoff.md`](CODEX-2026-08-30-naturalistic-g5c-cursor-handoff.md).
Cursor completed implementation; this packet stops for fresh independent Kiro
review. **No merge, no G6 grant, no live study authority.**

---

## Resume state

| Field | Value |
|---|---|
| **State** | `READY_FOR_KIRO_REVIEW` |
| **Accepted design carrier** | `c0890701b01f6a2d88a4e37a67bc06ab9551bac4` |
| **Implementation branch** | `fix/2026-08-30-naturalistic-g5c-corrective` |
| **Exact review revision** | `a77b50f7721862b119fc045f2eec24f40df74416` |
| **Push status** | `pushed to origin` |
| **PR** | Not opened — Ryan retains merge authority after Kiro PASS |
| **Ryan GATE** | Kiro exact-tip PASS → Ryan may open/merge PR; G6 remains closed until separate ChatGPT review + explicit G6 grant |
| **Classification** | `methodology_validation_not_product_evidence` — not product evidence |

## Context brief

**Who:** Cursor implemented the Ryan-granted G5C corrective on the strict
evaluator/fixture/test allowlist. Codex owns the design carrier; Kiro owns
independent review at the exact implementation tip.

**What:** Repair G5's synthetic methodology composition so every individual
T0–T10 boundary proves artifact guarantees, structural prospective completeness
is validated from serialized bytes, sealed registry remains sole opportunity
authority, valid-only missingness enters deterministic bounds, orthogonal
disposition precedence is deterministic, and paired replay has exactly one
intended treatment difference.

**When:** Landed G5 on `main` (PR #259) could label grouped `T0_T2` successful
with an incomplete prospective frame; methodology verdict remained C. Kiro
PASSed the corrective design at `b6a1ccf` (wording at `fde840b`); Ryan accepted
at `c089070`. Cursor implementation landed at `a77b50f`.

**Why:** Downstream stages and grouped success flags must not mask incomplete
prospective state, denominator drift, invalidity-as-missingness, or replay
asymmetry capable of a false favorable methodology PASS.

**How:** Review only the exact tip and changed allowlist files below. Return one
`PASS`, `FAIL`, or `CORRECTIVE REQUIRED` verdict with bounded corrections.
Do not implement, merge, select live parameters, access natural evidence, or
infer product value from synthetic fixtures.

---

## Exact review scope

Review **only** at commit `a77b50f7721862b119fc045f2eec24f40df74416` on branch
`fix/2026-08-30-naturalistic-g5c-corrective`. Verify `c089070` is an ancestor
of the tip. Do not review chat narrative, unpushed local state, or docs-only
commits except as routing context.

### Changed implementation files (allowlist — 16 files)

| File | G5C role |
|---|---|
| `eval_naturalistic/contracts.py` | `ProspectiveManifestV1`, `StageBoundaryLedger*`, serialized-byte validation, policy completeness |
| `eval_naturalistic/enums.py` | G5C stage/reason/orthogonal-axis vocabularies |
| `eval_naturalistic/base.py` | Validator import-boundary helper |
| `eval_naturalistic/digest.py` | Minor import hygiene |
| `eval_naturalistic/adjudication.py` | `EpisodeOpportunityIdentityV1`, arm-blind registry guard |
| `eval_naturalistic/analysis.py` | Deterministic bounds, orthogonal disposition, structured synthetic result |
| `eval_naturalistic/dry_run_mechanics.py` | `SyntheticPairedReplayStateV1`, `validate_paired_replay_symmetry` |
| `eval_naturalistic/dry_run.py` | T0–T10 ledger orchestration, 14 new adversarial scenarios |
| `eval_naturalistic/probe_construction.py` | Import hygiene only |
| `eval_naturalistic/probe_fixtures.py` | Import hygiene only |
| `eval_naturalistic/analysis_fixtures.py` | Import hygiene only |
| `tests/test_naturalistic_contracts.py` | Manifest/ledger contract tests |
| `tests/test_naturalistic_adjudication.py` | Opportunity-identity tests |
| `tests/test_naturalistic_analysis.py` | Bounds/precedence tests |
| `tests/test_naturalistic_dry_run.py` | Ledger + G5C scenario tests |
| `tests/test_naturalistic_probe.py` | Import hygiene only |

**Out of scope for this review grant:** `eval_naturalistic/fixtures.py`,
`contract_validate.py`, package initializers, docs edits on the branch,
configuration, scripts, corpus/runtime integrations, G6/T0, live parameters,
natural evidence, Agent A/B, live scoring, product disposition.

---

## Load-bearing mechanics to verify

### 1. Structural prospective completeness (T0)

- Synthetic fixture can start with all required information slots explicitly
  `PENDING`; complete manifest requires substantive serialized policy content.
- Validation authority is **canonical serialized bytes**, not `stage_ok`, `.ok`,
  or builder completion flags.
- Reject absent, empty, placeholder, falsely marked-complete, or
  non-applicable-without-rule content.
- Re-derive digest of exact artifact handed downstream; post-freeze byte edit or
  handoff mismatch is integrity failure.
- Execution refuses to advance without valid synthetic logged freeze digest.
- `run_g5_end_to_end()` must **not** succeed from incomplete/placeholder frame.

### 2. Immutable opportunity authority (T2+)

- Sealed `TargetRegistry` is sole membership/denominator authority.
- One immutable `episode_opportunity_id` per target-bearing episode.
- Registry construction cannot inspect condition, capture, retrieval, trial
  evidence, evaluability, scores, or outcomes.

### 3. Separate outcome axes

Record separately: natural ConvMem capture; C0/C1 trial-evidence capture;
C0/C1 score evaluability; protocol/environment/scorer integrity; scorer
reliability. Fixed reason vocabulary. Only valid post-treatment outcome
missingness may enter bounds; protocol/isolation/lineage/registry/freeze/scorer-
integrity failures are invalid and never bounded.

### 4. Deterministic bounds and structured result

- Complete-pair C1−C0 effect only where both valid arm scores exist.
- Deterministic worst/best-case bounds over normalized score support `[0.0, 1.0]`
  for valid missing episode contributions only.
- Degrade: complete-pair estimate → bounded interval → inconclusive interval.
- Emit structured synthetic result (opportunity, effect/bounds, process
  accounting). No authoritative scalar or product disposition.
- `run_g4_safe_synthetic_example()` preserved: `conditional_effect=0.3`,
  `disposition=blocked_non_estimable`.

### 5. Orthogonal disposition precedence

1. protocol/isolation/lineage/registry/freeze invalidity;
2. environment or scorer-integrity invalidity;
3. insufficient opportunity or information;
4. below-threshold scorer reliability or inconclusive valid-missingness bounds;
5. effect interpretation eligible only in later authorized study.

Classification remains `methodology_validation_not_product_evidence`.

### 6. Paired replay symmetry (T6–T7)

- C0/C1 as fresh replays from one sealed synthetic pre-trial state.
- Mechanical comparison of model/build/settings, prompt, tools, readable roots,
  budget/stopping, mutable-state reset, external-service replay/exclusion.
- **Only** intended difference: C1 access to frozen synthetic ConvMem surface.
- Reject shared mutable session/cache/database, non-replayed external state,
  condition-specific repair/retry, changed execution order.

### 7. Individual T0–T10 boundary ledger

- One `StageBoundaryLedger` entry per individual T0 through T10 boundary.
- Each entry binds: stage identity, canonical input digest, predicate results,
  validator identity/version, output digest, guarantees exported, next-stage
  assumptions, failure reason(s).
- Grouped `T0_T2`, `T3_T5`, `T6_T7`, `T8_T10` are **derived summaries only**;
  no group-level success substitutes for boundary evidence.
- Happy path must show **11 individual entries** (`T0`…`T10`).

---

## G5C adversarial scenarios (must be demonstrated)

Retain all pre-G5C required scenarios plus these 14 named G5C controls:

| Scenario ID | What it proves |
|---|---|
| `incomplete_nominal_t0_frame` | All-`PENDING` prospective slots fail before T0_T2 success |
| `false_completeness_placeholder_slot` | Placeholder marked complete rejected by byte validation |
| `stage_corruption_sweep` | Each T0–T10 input corruption fails that stage closed |
| `boundary_composition_proof` | Happy path asserts next-stage guarantees, not return status alone |
| `freeze_tamper_post_seal` | Post-freeze byte edit → digest mismatch / integrity failure |
| `handoff_artifact_mismatch` | Downstream validator receives different artifact than logged |
| `validator_import_boundary` | T0 structural validator does not import execution/capture/scoring builders |
| `registry_arm_dependent_rule` | Registry rule consulting arm/capture/results rejected |
| `asymmetric_valid_missingness_bounds` | Asymmetric C0/C1 capture/evaluability → deterministic bounds, fixed denominator |
| `invalid_vs_boundable_separation` | Valid missing enters bounds; protocol invalidity wins precedence |
| `disposition_precedence_favorable_effect` | Favorable effect cannot override protocol/sparse/scorer failures |
| `paired_replay_mismatch` | Root/shared-state/external/order asymmetry fails before scoring |
| `scorer_integrity_vs_reliability` | Integrity failure distinct from below-threshold valid reliability |
| `synthetic_only_guard` | No natural locator, corpus path, Agent runner, live scorer, or G6 authority |

Dry-run report at tip: **34 scenarios**, `all_required_fail_closed_demonstrated=true`,
`product_disposition_emitted=false`, `g6_authority_assumed=false`.

---

## Verification evidence (Cursor-run at `a77b50f`)

Re-run independently at the exact tip before signing:

```bash
git fetch origin fix/2026-08-30-naturalistic-g5c-corrective
git checkout a77b50f7721862b119fc045f2eec24f40df74416

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

### Cursor-reported results (2026-08-31)

| Check | Result |
|---|---|
| Focused pytest | **116 passed**, 8 subtests |
| `compileall` | **OK** |
| `python -m eval_naturalistic.dry_run` | **exit 0** |
| `git diff --check` | **clean** |
| Pylint (changed core files) | contracts 9.44, dry_run 9.90, analysis 9.94, adjudication/enums/mechanics 10.00 |
| Ruff (allowlist) | **52 findings** — predominantly pre-existing `RUF012` on `_FIELDS` class attributes in `contracts.py` (pattern predates G5C); not introduced as new gate-weakening |

---

## Required Kiro review questions

Return `PASS`, `FAIL`, or `CORRECTIVE REQUIRED` at exact `a77b50f` and answer:

1. Does serialized-byte prospective completeness validation prevent grouped
   `T0_T2` success on an incomplete or placeholder frame?
2. Does the individual T0–T10 `StageBoundaryLedger` prove boundary guarantees,
   with grouped statuses derived only as summaries?
3. Does sealed registry identity remain the sole episode-opportunity authority
   with no arm/capture/result-dependent membership rule?
4. Are natural capture, per-arm trial capture, and per-arm evaluability
   separate and fully accounted before effect interpretation?
5. Do deterministic bounds include only valid missing outcomes on `[0.0, 1.0]`,
   preserve the fixed denominator, and degrade estimate → bounds → inconclusive?
6. Is orthogonal disposition precedence deterministic and tested against a
   favorable synthetic effect?
7. Does paired replay fail closed on every tested asymmetry with C1 ConvMem as
   the sole intended difference?
8. Are all 14 G5C adversarial scenarios named, deterministic, synthetic-only,
   and demonstrated in `run_g5_dry_run()`?
9. Is G4's descriptive `0.3` fixture preserved without product interpretation?
10. Does the diff stay within the granted allowlist with no G6/live/product
    authority added?

If `CORRECTIVE REQUIRED`, list bounded file-scoped fixes only — no scope
expansion beyond the Cursor grant allowlist.

---

## Acceptance criteria (reviewer checklist)

- [ ] Exact tip `a77b50f` reviewed; carrier `c089070` confirmed ancestor
- [ ] All 10 review questions answered with evidence (file + line or test name)
- [ ] Independent re-run of verification commands at exact tip
- [ ] No product disposition inferred from synthetic `0.3` or happy-path effect
- [ ] Verdict recorded: `PASS` | `FAIL` | `CORRECTIVE REQUIRED`
- [ ] If `PASS`: Ryan may merge; G6 still Ryan-gated (ChatGPT review + explicit grant)
- [ ] If `FAIL` or `CORRECTIVE REQUIRED`: return bounded corrections; Cursor may re-execute grant only

---

## What Kiro must NOT do

- No code, test, script, config, or generated-file edits
- No merge, PR open, or `main` push
- No G6/T0 grant, live parameter selection, or natural evidence access
- No product conclusion from synthetic fixtures
- No re-opening unrelated G1–G4 scope or `fixtures.py` / `contract_validate.py`

---

## Related files

| Purpose | Path |
|---|---|
| Cursor implementation grant | [`CODEX-2026-08-30-naturalistic-g5c-cursor-handoff.md`](CODEX-2026-08-30-naturalistic-g5c-cursor-handoff.md) |
| Accepted design review (prior Kiro PASS) | [`CODEX-2026-08-30-naturalistic-g5-corrective-kiro-review-handoff.md`](CODEX-2026-08-30-naturalistic-g5-corrective-kiro-review-handoff.md) |
| Accepted architecture | [`../plans/ARCHITECTURE-naturalistic-product-value.md`](../plans/ARCHITECTURE-naturalistic-product-value.md) (branch tip includes corrective amendment) |
| Accepted execution contract | [`../plans/EXECUTION-naturalistic-product-value.md`](../plans/EXECUTION-naturalistic-product-value.md) |
| Arc state | [`../plans/STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md) |
| Historical G5 handoff | [`CURSOR-2026-08-30-naturalistic-product-value-g5-handoff.md`](CURSOR-2026-08-30-naturalistic-product-value-g5-handoff.md) |

---

## Picking up (Kiro)

1. Read this file and the Cursor grant handoff before any review edits.
2. `git fetch origin && git checkout a77b50f7721862b119fc045f2eec24f40df74416`
3. Re-run verification commands above; do not trust chat claims alone.
4. Review changed allowlist files at exact tip only.
5. Return verdict + answers in a review note or handoff reply; Ryan owns merge.

**TL;DR:** [Arc Naturalistic ConvMem product-value evaluation] Independent Kiro
review at exact tip `a77b50f` on `fix/2026-08-30-naturalistic-g5c-corrective`.
Verify G5C structural completeness, T0–T10 ledger, bounds/precedence/replay,
and 14 adversarial scenarios. Synthetic only — no product evidence, no G6. Stop
at verdict; Ryan merges after PASS.
