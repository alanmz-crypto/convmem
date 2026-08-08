# Execution Plan — JudgeBench Semantic Calibration (v1)

## Planning Status

| Field | Value |
|---|---|
| Plan state | **Proposed for Ryan HITL; no Execute authority** |
| Architecture authority | Lock-ready @ 2026-08-08 |
| Execution plan author of record | Codex |
| Delegate input | DeepSeek V4 Flash draft (this file) — for Ryan/Codex review, not authoritative |
| Lane | Cursor for implementation tasks; Codex owns plan text; Ryan owns HITL approval |
| Next gate | Ryan HITL approval; corpus gold/split lock; judge selection |

## Scope Lock

| # | In scope (this arc) | Out of scope (explicit) |
|---|---|---|
| 1 | Offline, frozen-evidence semantic calibration for JudgeBench v1 | Any Chroma usage in the semantic calibration path (Chroma P0-A is a separate arc dependency for E2E track only) |
| 2 | `SemanticJudgmentV1` contract, `JudgeInvocationV1`, MechanicalGrade hooks, rubric validator framework | Jury/J2/J3 semantics; any live `ask.py` judging |
| 3 | `eval_model_identity.py` run before execution; `eval_provenance.py` comparison after | Corpus gold mutation; gold/split lock is a Ryan stop point |
| 4 | `cross_family` only; unknown → fail-closed; exactly one judge pinned per run | Same-family evaluation; multi-judge runs |
| 5 | Legacy `eval_judge.py` 1–5 path remains explicitly legacy during transition | Backporting v1 provenance into legacy path |
| 6 | T5 definitions version as E2E fixtures (semantic disposition only) | Using T5 definitions as gold or mutating gold in this arc |

## Task Order

Sequential execution is required; each task depends on its predecessor. No task in this plan may start early.

```
T1 → T2 → T3 → T4 → T5 → [Ryan stop: corpus gold/split lock] → [Ryan stop: judge selection] → T6
```

Tasks T1–T5 are implementation. T6 is structural scaffold only; execution halts before T6 content work pending Ryan gold lock.

## Tasks

| ID | Deliverable | In scope | Depends on | Gates | Lane |
|---|---|---|---|---|---|
| T1 | Shared contracts landed | `SemanticJudgmentV1`, `JudgeInvocationV1`, MechanicalGrade hooks, rubric validator framework; validation error types; fail-closed defaults for unknown dispositions | None | Contract compiles; validator rejects unsigned/invalid rubric refs; no SemanticJudgmentV1 import outside allowed modules | Cursor |
| T2 | `eval_model_identity.py` + registry stub | Versioned judge/evidence registry stub; strict identity capture (model family, pinned version); cross-family enforcement; unknown family → hard fail | T1 | Registry stub records exactly one judge per run; cross-family-only policy enforced; unknown → fail-closed | Cursor |
| T3 | `eval_provenance.py` signature expansion | Expanded comparison signature for evidence provenance (frozen evidence IDs, judge pin, calibration timestamp); diff output; no write to gold | T2 | Provenance comparison passes for expected runs; fails on altered evidence ID or judge pin change; output is read-only vs gold | Cursor |
| T4 | JudgeBench runner + corpus scaffold | `eval_corpus/fixtures/judgebench/semantic-v1/` manifest, empty case placeholders, rubric refs; offline runner; no Chroma imports in semantic path | T3 | Runner executes end-to-end with zero cases; Chroma absent from import graph; manifest validates | Cursor |
| T5 | Legacy compatibility shim | Explicit `--legacy` flag on `eval_judge.py` 1–5 path; no v1 provenance bleed; shared constants isolated | T4 | Legacy run passes under explicit flag; legacy output schema unchanged; no `SemanticJudgmentV1` leak into legacy output | Cursor |
| T6 | E2E synthesis-v1 fixture scaffold | Structure-only scaffold for T5 disposition fixtures (semantic disposition placeholders, rubric refs, manifest slots); no gold mutation; Ryan locks gold later | T5 + Ryan gold/split lock + Ryan judge selection | Scaffold renders empty fixtures; manifest parses; gold files untouched | Cursor |

## Stop Points

Stop authority is required before proceeding past the following gates:

1. **Ryan locks corpus gold/split** — required before T6 gold content may be authored. T6 scaffold structure may be laid before the lock, but no gold values are written.
2. **Ryan selects judge after calibration** — required before any T6 disposition content or E2E fixture population. Judge selection is based on `eval_model_identity.py` + calibration output, and is a separate decision from corpus lock.

Until both stop points are cleared, the plan remains in execution hold after T5.

## Evidence Requirements

| Evidence | Produced by | Required state |
|---|---|---|
| Contract + validator compile | T1 | Green |
| Identity/registry run output | T2 | Green; one judge pinned; family cross-check visible |
| Provenance comparison report | T3 | Green; diff empty vs frozen evidence |
| Runner dry run (zero cases) | T4 | Green; manifest valid; no Chroma import trace |
| Legacy shim run output | T5 | Green; legacy schema byte-compatible |
| Fixture scaffold listing | T6 | Green; empty fixtures only; gold lock referenced |

## Companion VERIFY Reference

Execute against `docs/plans/VERIFY-judgebench.md`. All V0 mechanical checks must be Green before any conditional calibration judgement call. VERIFY status is PENDING until Execute; no Execute authority exists at this plan state.
