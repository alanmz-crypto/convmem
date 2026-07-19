# EXECUTION — Embedding-Model A/B Evaluation (two-gate operator runbook)

**Status:** Gate 1 evaluator harness on `feat/2026-07-19-embed-eval-harness`.
**Authority:** Architecture Rev 1 (binding) + Gate 1 / Gate 2 human gates.

## Two-gate model

| Gate | Meaning |
|------|---------|
| **Gate 1** | Approves the completed evaluator (tracked code, hermetic tests, fixtures). No live capture/builds/evals. |
| **Gate 2** | Reviews the first real comparison’s evidence (external approval sidecar SHA, corpus acceptance, uncertainty report). Never automatic promotion. |

## Gate 1 shipped capabilities

- Canonical capture CLI (**Chroma always required**): post-Chroma recheck; **canonical overlap policy** (40/30/30 — under-quota → `UNRESOLVED`); immutable `historical_spot_check.json`
- Separate adjudication CLI + `corpus_acceptance.json` (spot-check never edited); real path is run-manifest-gated
- Shadow builder: package SHA + fingerprint, write-once manifest, collection vs comparison reuse, `units_per_sec`
- **Operation-specific run-manifest binders** (capture / adjudicate / config_generation / baseline_build / challenger_build / compare / model_execution): reject missing, extra, or mismatched fields; real mode requires external `<manifest>.approved.sha256` sidecar
- Real shadow builds force corpus acceptance from auth context (CLI flag cannot disable)
- Embed adapters: `fake`, `http-fake`, gated `ollama` behind `model_execution`
- Compare modes:
  - `injectable` — hermetic scoring via `--scores-json`; latency labeled `fabricated_clock`
  - `subprocess` — real `query_units` via `CONVMEM_CONFIG` workers; one-shot for isolation; long-lived per-arm workers for warm latency (5 discarded warmups + 20 timed reps, counterbalanced); process startup reported separately
- Subprocess mode **fails closed**: worker exit codes, error results, malformed output, and startup-identity mismatches abort the compare (exit 5) — never recorded as misses or 0.0 latency
- **Per-arm identity binding**: `baseline_/challenger_model_tag` + `_config_sha256` from parsed arm configs; `--embed-host` verified against both configs and worker banners; enrichment (`decisions-approved.jsonl`) hashed and required byte-identical across arms
- Fallback exercise wired into the compare CLI (`--exercise-fallback --fallback-config`): wrong query-vector dimension from a dedicated endpoint while preserving readable `chroma.sqlite3`; `fallback_exercised=true` only on fallback-only sentinel, else the run aborts (exit 4)
- Schema fixtures: `eval_schema_*` and `eval_methodology_schema_*` (category handling only — **not** a real corpus pilot)
- Doctor embed identity via SQLite `mode=ro`

## Real pilot (post Gate 1 merge / pre Gate 2)

The actual 25–40-query pilot must use resolvable real corpus/ledger IDs, receive Claude label/coverage review, and have query/relevance hashes bound into the approved Gate 2 run-manifest. That is run preparation, not another Gate 1 authorization.

## Not authorized under Gate 1

Real corpus capture, external configs under `~/.config/convmem` or `~/.local/share/convmem/eval`, model pull/probe, real shadow builds/evaluations, service changes, promotion, cleanup.

## Uncertainty rule (manifest fields)

`primary_metric`, `primary_view=embedding_influenced`, `tie_epsilon`, `significance_alpha`, `confidence_level`, `bootstrap_seed`, `bootstrap_resamples`, `minimum_non_tied_pairs`.

Challenger **BETTER** only when mean paired delta > 0, CI excludes zero positively, sign-test p ≤ alpha, and effective non-tied n ≥ minimum; else **INCONCLUSIVE** or **WORSE**. Evidence only — not promotion authority.

## Notes

- `pending_decisions.jsonl` is not in `query_units` closure.
- Crash-safe writes via `eval_corpus.io_atomic`.
- Historical review / unadjudicated spot-check blocks Gate 2 corpus acceptance.
