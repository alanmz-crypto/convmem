# Cursor → Codex / Ryan: Gate 1 correction tip for re-verify

**To:** Codex (targeted Gate 1 re-verify), Ryan  
**From:** Cursor  
**Date:** 2026-07-19  
**Branch:** `feat/2026-07-19-embed-eval-harness`  
**Tip:** `02ae7e8fae7c27cc6219cf3e13bdb504fbdb5fd4`  
**Runbook:** [`docs/plans/EXECUTION-embedding-model-eval.md`](../plans/EXECUTION-embedding-model-eval.md)

**Live ops:** `convmem brief` only. Do not treat this post as corpus truth.

---

## TL;DR

- Gate 1 correction is pushed at `02ae7e8` under Ryan authorization + five Codex binding constraints.
- Evaluator now has operation-specific binders, subprocess compare (isolation ≠ warm latency), SQLite-safe dim-mismatch fallback, and dual-endpoint isolation proof.
- Methodology data is **schema fixtures only**; real 25–40 corpus pilot waits until after Gate 1 merge / before Gate 2.
- No PR, no Gate 2, no live/eval writes in this pass — Codex re-verify next.

---

## What changed since FAIL tip `0ec350e`

| Constraint | Delivery |
|------------|----------|
| C1 SQLite-preserving fallback | Wrong-dim fake embed; `fallback_exercised` only on `FALLBACK_ONLY_SENTINEL_Z9` hit |
| C2 Isolation ≠ latency workers | One-shot `CONVMEM_CONFIG` workers for isolation; long-lived per-arm workers with 5 warmups + 20 timed reps, counterbalanced; startup ms separate |
| C3 Operation-specific binders | `capture` / `adjudicate` / `config_generation` / `baseline_build` / `challenger_build` / `compare` / `model_execution`; nonempty ops; external `.approved.sha256` sidecar; real acceptance forced from auth context |
| C4 Isolation evidence | Shadow fake endpoint vs live-canary (must be zero); unreachable live paths; frozen shadow enrichment; worker startup banner (config/chroma/data/host) |
| C5 Schema ≠ real pilot | Renamed `eval_schema_*`; added `eval_methodology_schema_*`; real pilot deferred |

## Verification (Cursor)

- Focused eval suites: OK  
- Full `pytest tests/`: **617 passed**, 34 subtests  
- `git diff --check origin/main...HEAD`: clean  
- External/live writes: none  

## Ask of Codex

Re-verify Gate 1 against tip `02ae7e8` under the binding constraints. Do **not** authorize Gate 2 or open a PR from this tip unless Ryan says so.

## Out of scope here

- Real corpus capture / shadow / Ollama model ops  
- Preparing the real 25–40-query pilot (post-merge / pre-Gate 2 prep)  
- PR open/merge, promotion, cleanup  

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Gate 1 | Approve completed evaluator harness (code/tests/fixtures); no live capture/eval |
| Gate 2 | Human review of first real comparison evidence; never auto-promotion |
| run-manifest | Mechanical authorization file; real mode needs external approval sidecar SHA |
| binder | Per-operation exact runtime-field check (missing/extra/mismatch → refuse) |
| methodology schema fixture | Synthetic categorized queries for reporting tests — not real corpus evaluation |
| `fallback_exercised` | Report flag set only when fallback-only sentinel is returned after forced vector failure |
