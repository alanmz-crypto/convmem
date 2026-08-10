# Codex handoff — Summarizer switch decision: qwen3.5 vs llama3.1:8b

**To:** Codex (planning/decision lane)
**From:** Crush (DeepSeek V4 Flash, experiment lane)
**Date:** 2026-08-02
**Mode:** Decision packet + execution plan. Read-only is safe anytime; the
config switch itself is a live-edit decision for Ryan (freeze context below).

## TL;DR

`qwen3.5:latest` beats the incumbent `llama3.1:8b` on every metric at 10
repeated runs over a 30-row real-pair golden set (structural 82.0% vs 66.7%,
recall 85.4% vs 82.9%, judge 4.74 vs 4.14, failure 18% vs 33%). The switch is
a one-line `config.toml` change. The C7 census freeze does **not** bind model
config, so the switch would not corrupt the census — but it bends the freeze's
"no hand edits" spirit. Decide: switch now vs after freeze lift (2026-08-07).

## Evidence (full numbers)

Harness: existing `scripts/eval-summaries.py` + grading contract unchanged.
New golden set: 30 rows sampled from real Cursor/Codex/Kiro transcripts
(`/tmp/summarizer-bakeoff/golden_summaries_expanded.jsonl`, repo-fixture
schema; every `must_mention` validated present in its excerpt).
Config override via `CONVMEM_CONFIG` copies in `/tmp/summarizer-bakeoff/` —
no repo edits, no commits.

### 10-run confirmation (30 rows × 10 runs = 300 summaries/model)

| Metric | `llama3.1:8b` | `qwen3.5:latest` | `ornith:9b` |
|---|---|---|---|
| Structural pass | 66.7% | **82.0%** | 67.3% |
| Keyword recall | 82.9% | **85.4%** | 86.1% |
| Judge mean (DeepSeek V4 Flash, advisory) | 4.14 | **4.74** | 4.62 |
| Failure rate | 33.3% | **18.0%** | 32.7% |

Per-row structural vs llama: qwen3.5 wins 14, ties 16, loses 0 (of 30).
Raw artifacts: `/tmp/summarizer-bakeoff/results-{model}.json`.

### Identifier/temporal preservation (1 run, 28 rows / 48 id pairs)

| Metric | `llama3.1:8b` | `qwen3.5:latest` |
|---|---|---|
| ID preservation | 56.3% | **62.5%** |
| Date-row preservation | 42.1% | 42.1% (tie) |

Both models drop `dec_prop_…` ids and code line numbers (e.g. `:1668`) in
summaries — a shared prompt-level weakness, not a switch blocker. Could be a
follow-up fix (keyword/prompt engineering), not this decision.

## Why the 3-row repo fixture said the opposite

Repo `golden_summaries.jsonl` has 3 easy rows where llama scores 100% — the
pilot on it made qwen look worse on recall. The 30-row real-pair set shows the
incumbent at 65% structural: the 3-row set was too small and too easy. The
30-row set is the trustworthy evidence.

## Freeze analysis (the actual question)

C7 census is **armed** now (window 2026-07-31T00:00Z → 2026-08-07T00:00Z;
`/home/lauer/.local/share/convmem/writer-census/`, state `armed`, actively
recording session events). The census header binds exactly:
`code_revision`, `writer_gate_protocol`, `chroma_root_identity`,
`writer_gate_identity` (validated at every writer open/close in
`writer_census.py`).

- `summarize_model` is **not** a bound identity → the switch cannot corrupt
  census validation or the report.
- The census is payload-free writer-session telemetry; it never reads summary
  content or model names.
- Counter-consideration: the runbook says "no hand edits" during observation,
  and switching mid-window mixes summary provenance in the corpus for the
  remaining ~5 days. Ryan (freeze owner) leans toward "quality of freeze work
  improves now" as the reason to switch immediately.

**Decision for Ryan/Codex:** is a config-only switch during an armed census
acceptable given (a) it cannot invalidate the census, (b) it violates the
"no hand edits" spirit, (c) it improves all summarization quality
immediately? Or wait 5 days?

## Execution plan if Ryan says switch (now or post-freeze)

1. `git branch --show-current` must be a `convmem work start` branch — never
   `main` (tracked-file rule; config.toml is untracked live config, but the
   baseline file is tracked).
2. Edit `~/.config/convmem/config.toml`:
   `summarize_model = "llama3.1:8b"` → `summarize_model = "qwen3.5:latest"`
   (backup exists: `config.toml.bak-2026-08-02-pre-qwen`).
3. Re-run `scripts/eval-summaries.py --update-baseline` on the repo 3-row
   fixture so the regression gate's baseline matches the new model context
   (provenance includes model digest — "NEEDS REBASELINE" otherwise).
4. Smoke: `convmem doctor` (summarization canary), one real ingest with a
   short new session, verify `conversation_summaries` gets qwen-style
   summaries (3 sentences + Keywords line).
5. Optional: expand repo golden set with the 30-row real-pair set (schema
   compatible) so future runs gate on realistic pairs, not just 3 easy ones.
6. VERIFY doc (post-freeze / if switched now, retrospective): per-row
   structural + recall, judge negative control PASS, model digest in
   provenance, no live-store regression (superseded counts, counts).

## Suggested Codex outputs

1. Verdict on switch-now vs wait (with the freeze analysis above as the
   decision frame).
2. Exact diff + commands for the switch (config edit, baseline update,
   doctor smoke).
3. Blast-radius note: does changing `summarize_model` affect anything else
   (embedding consistency, retrieval, `conversation_summaries` queries)?
   Summaries are embedded with `embed_model` (unchanged) and stored in the
   same collection — confirm no dimensional/schema impact.

## Reference docs

- C7 runbook: `docs/inter-model/CODEX-2026-07-30-C7-OPERATIONAL-RUNBOOK.md`
- Prior packet: `docs/inter-model/CRUSH-2026-08-02-summarizer-bakeoff-chroma-assessment.md`
- Harness: `scripts/eval-summaries.py`, `eval_grading.py`, `eval_judge.py`
- Baseline: `tests/fixtures/golden_summaries_baseline.json`
