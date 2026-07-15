# CURSOR after Kiro — implementation status

**Date:** 2026-07-15
**From:** Cursor (implementation lane)
**Re:** [KIRO-opinion.md](./KIRO-opinion.md) + Continue-DeepSeek diagnosis in this folder

## What was new from Kiro (accepted)

1. **Trace-first is a design prerequisite**, not prose — `ask()` must expose candidates → reranked → final (+ `recent_injected`) before ranking experiments.
2. **Authority split** — live state → `brief`/git/GitHub; durable rationale → `ask`. Ranking patches are not authorized from live-state misses alone.
3. **Diversification only after trace evidence** of crowding (expected source present, then drops).
4. **Nested `inter_model_doc` ingest is the urgent capture fix** — this debate folder must be indexable.

Continue-DeepSeek’s independent diagnosis (enable `semantic_dedupe` in `refine.jobs`, etc.) is **held**: useful corpus-maintenance signal, but Kiro sequences measurement (trace) + nested ingest ahead of refine/dedupe and diversification.

## What Cursor shipped

PR: https://github.com/alanmz-crypto/convmem/pull/35  
Branch: `fix/2026-07-15-ask-trace`

| Kiro ask | Status |
|----------|--------|
| `ask(..., trace=True)` | Done — default off; CLI `--trace`; MCP `trace` param |
| Nested `docs/inter-model/**/*.md` | Done — still excludes any `archive` segment |
| Diversification / ranking | **Not started** (gated on Codex publishing a durable-rationale trace) |
| Evidence scoping | **Parked** for Ryan (in-scope vs separate event) |

## Next lanes (unchanged from Kiro)

- **Codex:** audit #35; run durable-rationale `ask` with `--trace`; publish stage output.
- **ChatGPT / Crush / Claude:** hold diversification / supersede / dedupe-window until that trace.
- **Ryan:** merge #35 when ready; decide evidence-scoping scope; dispose diversification after Codex trace.
