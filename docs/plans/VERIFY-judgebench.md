# VERIFY Plan — JudgeBench Semantic Calibration (v1)

## Planning Status

| Field | Value |
|---|---|
| Verify state | **PARTIAL** — CHK-001..006 and CHK-008..010 PASSED; CHK-007 PARTIAL until Ryan locks G3 and a selected judge runs the corpus |
| Plan reference | `docs/plans/EXECUTION-judgebench.md` (Execute HITL APPROVED `dec_prop_20260808_150112_f49e`; S1–S9 landed) |
| Consequence hold | Human consequence assessment deferred until Execute events occur; updates require Ryan review |

## Human Consequence (placeholder)

Placeholder: If verification is skipped or failed checks are waived, the offline semantic calibration result may be accepted without provenance assurance, which could propagate an unverified judge disposition into downstream E2E work. This consequence is not yet assessed — it is a placeholder for post-Execute review.

## Scope Lock

| # | In scope | Out of scope |
|---|---|---|
| 1 | Mechanical verification of offline-only semantic path | Any live judging or online retrieval checks |
| 2 | No Chroma in semantic calibration path | Chroma dependency verification (separate E2E arc) |
| 3 | Invalid output handling, comparison signature, legacy isolation | J2/J3 jury semantics; live `ask.py` judging |
| 4 | Conformance scenarios for `SemanticJudgmentV1` | Gold mutation or corpus re-annotation |

## V0 Mechanical Checks

| ID | Check | Method | Status |
|---|---|---|---|
| CHK-001 | No Chroma import exists anywhere in the JudgeBench semantic calibration import graph | Static AST import scan of `eval_judgebench/` (S8); must not import `chroma_store`, `chroma_readonly`, or `ask` | **PASSED** — `tests/test_judgebench_no_chroma.py` green; runner (`eval_judgebench/runner.py`) included in scan |
| CHK-002 | Invalid/unknown disposition values from the pinned judge fail closed (never coerce to a valid disposition) | Negative test: feed synthetic invalid judge output; assert fail-closed | **PASSED** — `contract_validate.validate_judgment_dict` returns `invalid_output`/`StructuralContractError` for malformed enums and unknown props; never coerces a verdict (S3/S4 tests). |
| CHK-003 | `SemanticJudgmentV1` validates against the rubric validator; malformed rubric refs are rejected | Inject malformed rubric ref fixture; assert validation error | **PASSED** — `rubric.load_rubric` raises `RubricNotFoundError` on unknown `rubric_id` and refuses id-mismatch; `rubric_validate` checks against rubric data (S5/S6 tests). |
| CHK-004 | Provenance comparison signature detects evidence ID or judge pin changes | Altered-output diff test against frozen evidence; assert mismatch | **PASSED** — `tests/test_judgebench_contracts.py` |
| CHK-005 | Legacy `eval_judge.py` 1–5 path runs only under explicit `--legacy` flag and produces byte-compatible legacy schema | Golden output comparison for legacy run | **PASSED** — `tests/test_judgebench_contracts.py` (`legacy=True` gate + schema keys) |
| CHK-006 | No `SemanticJudgmentV1` provenance bleeds into legacy path output | Schema diff of legacy output; assert zero v1 fields present | **PASSED** — `tests/test_judgebench_contracts.py` |
| CHK-007 | Conformance scenario: each defined conformance fixture returns the exact expected disposition under the pinned judge | Fixture-by-fixture disposition comparison | **PARTIAL** — synthetic conformance in `tests/test_judgebench_contracts.py`; corpus-backed conformance awaits an eligible judge and separately authorized calibration experiment |
| CHK-008 | Corpus gold is unmodified after runner execution; runner is read-only vs gold | Hash-gold before/after; assert equal | **PASSED** — `tests/test_judgebench_contracts.py` gold hash before/after |
| CHK-009 | Locked corpus is structurally complete and canonical validation requires Ryan lock | Validate rows, hashes, rubric refs, split counts, J0 outcomes, origins, and uniform lock state with `--require-locked` | **PASSED** — 30 cases, 20/10 split, both tasks 15/15, all 30 rows locked by Ryan at `2026-08-10T00:50:50Z`; canonical corpus validation accepts the lock |
| CHK-010 | Canonical independence is derived from every frozen model-generated candidate origin, never substituted by caller identity/config | Supply a cross-family caller for a same-family frozen origin; assert canonical refusal. Cover multiple origins, unresolved origin, and forged human-curated config | **PASSED (pre-lock)** — focused contract regressions prove caller substitution refusal, all-origin enforcement, `unknown` fail-closed, and config-forgery resistance |

CHK-001/002/003 are met by the merged S1–S9 slice implementation (#144). CHK-004..006 and CHK-008 met by T2–T5 (Cursor). CHK-009/010 are met by the locked G3 branch. CHK-007 stays PARTIAL until identity resolution and calibration are separately authorized; Ryan's G4 selection follows the calibration evidence.
