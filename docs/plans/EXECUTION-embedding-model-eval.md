# EXECUTION — Embedding-Model A/B Evaluation (two-gate operator runbook)

**Status:** Gate 1 evaluator harness on `feat/2026-07-19-embed-eval-harness`.  
**Authority:** Architecture Rev 1 (binding) + Gate 1 / Gate 2 human gates.

## Two-gate model

| Gate | Meaning |
|------|---------|
| **Gate 1** | Approves the completed evaluator (tracked code, hermetic tests, fixtures). No live capture/builds/evals. |
| **Gate 2** | Reviews the first real comparison’s evidence (approved run-manifest SHA, corpus acceptance, uncertainty report). Never automatic promotion. |

## Gate 1 shipped capabilities

- Canonical capture CLI (**Chroma always required**): post-Chroma export/processed recheck, overlap validation, immutable `historical_spot_check.json`
- Separate adjudication CLI + `corpus_acceptance.json` binding SHAs of capture report, package, overlap, spot-check, and adjudications file (spot-check never edited)
- Shadow builder: package SHA + fingerprint recompute, `convmem:package_sha256` + `document_recipe_version` in metadata, write-once manifest, collection vs comparison reuse split, `units_per_sec`
- Run-manifest auth (`execution_mode=fixture|real`) replacing R4/R5 flags; fixture manifests cannot authorize external paths
- Embed adapters: `fake`, `http-fake`, gated `ollama` (unimplemented for live Gate 1 runs)
- Dual-view compare CLI with recipe strata, paired sign-test + seeded bootstrap uncertainty, `queries_per_sec` / `units_per_sec`
- Primary inference: pre-registered metric in `embedding_influenced` only; ops-pipeline and recipe strata diagnostic
- 25–40 categorized pilot with `recipe_stratum`; temp-only shadow config generator
- Doctor embed identity via SQLite `mode=ro`

## Not authorized under Gate 1

Real corpus capture, external configs under `~/.config/convmem` or `~/.local/share/convmem/eval`, model pull/probe, real shadow builds/evaluations, service changes, promotion, cleanup.

## Uncertainty rule (manifest fields)

`primary_metric`, `primary_view=embedding_influenced`, `tie_epsilon`, `significance_alpha`, `confidence_level`, `bootstrap_seed`, `bootstrap_resamples`, `minimum_non_tied_pairs`.

Challenger **BETTER** only when mean paired delta > 0, CI excludes zero positively, sign-test p ≤ alpha, and effective non-tied n ≥ minimum; else **INCONCLUSIVE** or **WORSE**. Evidence only — not promotion authority.

## Notes

- `pending_decisions.jsonl` is not in `query_units` closure.
- Crash-safe writes via `eval_corpus.io_atomic`.
- Historical review / unadjudicated spot-check blocks Gate 2 corpus acceptance.
