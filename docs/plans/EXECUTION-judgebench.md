# Execution Plan — JudgeBench Semantic Calibration (v1)

## Planning Status

| Field | Value |
| --- | --- |
| Plan state | **Proposed for Ryan HITL; no Execute authority** |
| Architecture authority | Lock-ready @ 2026-08-08 (`ARCHITECTURE-judgebench.md`) |
| Execution plan author of record | Codex |
| Delegate input | DeepSeek V4 Flash draft — for Ryan/Codex review, not authoritative |
| Lane | Cursor for implementation; Codex owns plan text; Ryan owns HITL |
| Next gate | Ryan Architecture lock → Execution HITL → corpus gold/split lock |

## Scope lock

| In scope | Out of scope |
| --- | --- |
| Offline frozen-evidence JudgeBench semantic calibration (no Chroma) | J2/J3 jury; live `ask.py` judging |
| `SemanticJudgmentV1`, `JudgeInvocationV1`, MechanicalGrade, rubric validators | Corpus gold mutation (Ryan stop) |
| `eval_model_identity.py` before run; `eval_provenance.py` comparison signature | Judge model selection (Ryan stop after calibration) |
| JudgeBench runner + `eval_corpus/fixtures/judgebench/semantic-v1/` scaffold | Full corpus `convmem index` |
| Legacy `eval_judge.py` explicit legacy path | v1 provenance bleed into legacy |
| E2E `convmem-e2e/synthesis-v1/` fixture scaffold (structure only) | T5 gold authoring; Chroma Tier-L reconcile |

Chroma orphan P0-A is a **separate arc** dependency for the E2E track only.

## Task order

```text
T1 → T2 → T3 → T4 → T5 → T6
              ↑ Ryan stop: corpus gold/split lock before populating semantic cases
              ↑ Ryan stop: judge selection after calibration split work (separate from T6 scaffold)
```

T1–T5 may proceed after Execution HITL. T6 scaffold is structure-only until Ryan locks gold.

## Tasks

| ID | Deliverable | Depends on | Start tier | Flash slices | Escalation owner | Gates |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | Shared contracts: `SemanticJudgmentV1`, `JudgeInvocationV1`, MechanicalGrade hooks, rubric validator framework | — | 1–4 | S3–S6, S9 | Luna high+ if rubric semantics contested | pytest contract/validator tests; no unknown JSON properties |
| T2 | `eval_model_identity.py` + versioned registry stub | T1 | 5 | S7 loader only | V4 Pro / Luna max for classify | `cross_family` enforcement; `unknown` fail-closed; no substring guessing |
| T3 | `eval_provenance.py` comparison-signature expansion | T2 | 5 | — | Tier 5–8 | signature changes → `needs_rebaseline`; identity policy version bound |
| T4 | JudgeBench offline runner + `semantic-v1/` corpus scaffold (manifest, rubric refs, empty cases) | T3 | 5–7 | S1, S8 | Tier 5–7 for runner orchestration | runner dry-run; zero Chroma imports in semantic path |
| T5 | Legacy `eval_judge.py` shim (`--legacy` or explicit legacy result type) | T4 | 6–8 | — | Tier 6–8 | legacy output unchanged; cannot emit v1 provenance |
| T6 | E2E `synthesis-v1/` fixture scaffold for T5 disposition (structure only) | T5 | 1 | S2 | Gold population → Ryan stop | manifest parses; no gold values until Ryan lock |

**Flash executor brief:**
[`EXECUTION-judgebench-flash-slices.md`](EXECUTION-judgebench-flash-slices.md) —
Crush + DeepSeek V4 Flash runs S1–S9 only; stops at escalation wall.

## Stop points

1. **Ryan Architecture HITL lock** on `ARCHITECTURE-judgebench.md` — before Execution HITL.
2. **Ryan Execution HITL** on this plan (Codex may revise Flash draft).
3. **Ryan locks corpus gold/split** — before authoring semantic case content or E2E gold.
4. **Ryan selects judge** after calibration-split experiments — not architecture's job to bless a model.

## Evidence requirements

- Contract + validator unit tests green (T1)
- Identity registry resolves known aliases; refuses `unknown` for canonical runs (T2)
- Comparison signature stable across identical re-runs (T3)
- JudgeBench runner completes with empty corpus; Chroma stopped does not change inputs (T4)
- Legacy path explicitly labeled; score baselines cannot update v1 baselines (T5)
- E2E scaffold files present; gold hashes unchanged until Ryan lock (T6)

## Arc VERIFY companion

`docs/plans/VERIFY-judgebench.md` — V0 checks PENDING until Execute.

## Delegate-down wall (not Flash/Cursor without escalation)

- Codex re-authoring execution plan if Ryan requires authoritative plan text
- Python implementation beyond bounded tasks above → Cursor after Execution HITL
- Corpus case authoring, Ryan gold lock, judge calibration runs
- Chroma orphan repair / Tier-L reconcile (parallel arc)
