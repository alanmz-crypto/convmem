# VERIFY Plan — JudgeBench Semantic Calibration (v1)

## Planning Status

| Field | Value |
|---|---|
| Verify state | **PENDING until Execute** — this is a stub; no checks have run |
| Plan reference | `docs/plans/EXECUTION-judgebench.md` (Proposed for Ryan HITL; no Execute authority) |
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
| CHK-001 | No Chroma import exists anywhere in the JudgeBench semantic calibration import graph | Static import scan over `eval_corpus/fixtures/judgebench/semantic-v1/` and runner modules | PENDING |
| CHK-002 | Invalid/unknown disposition values from the pinned judge fail closed (never coerce to a valid disposition) | Negative test: feed synthetic invalid judge output; assert fail-closed | PENDING |
| CHK-003 | `SemanticJudgmentV1` validates against the rubric validator; malformed rubric refs are rejected | Inject malformed rubric ref fixture; assert validation error | PENDING |
| CHK-004 | Provenance comparison signature detects evidence ID or judge pin changes | Altered-output diff test against frozen evidence; assert mismatch | PENDING |
| CHK-005 | Legacy `eval_judge.py` 1–5 path runs only under explicit `--legacy` flag and produces byte-compatible legacy schema | Golden output comparison for legacy run | PENDING |
| CHK-006 | No `SemanticJudgmentV1` provenance bleeds into legacy path output | Schema diff of legacy output; assert zero v1 fields present | PENDING |
| CHK-007 | Conformance scenario: each defined conformance fixture returns the exact expected disposition under the pinned judge | Fixture-by-fixture disposition comparison | PENDING |
| CHK-008 | Corpus gold is unmodified after runner execution; runner is read-only vs gold | Hash-gold before/after; assert equal | PENDING |

All checks are PENDING until Execute authority is granted.
