# Crush handoff — Summarizer bake-off pilot + Chroma assessment kickoff

**Lane:** Crush (DeepSeek V4 Flash, investigation/experiment).
**Date:** 2026-08-02.
**Mode:** Read-only experiment + planning. No repo edits, no commits
(C7 code freeze active through 2026-08-07T00:00Z — everything here ran from
`/tmp` configs against the live read path; nothing mutated the repo or corpus).

## Scope (from the technology-replacement list, tasks #3 and #6)

- **#3 Summarizer bake-off:** does a newer 7B–14B instruct model beat
  `llama3.1:8b` for local summary generation?
- **#6 Chroma replacement assessment:** does Chroma actually limit us, or do we stay?

## #3 Pilot bake-off — results (3 golden rows, existing harness)

Harness: `scripts/eval-summaries.py` (deterministic hard gate + advisory
DeepSeek V4 Flash judge, negative control PASS for all runs). No repo edits:
`CONVMEM_CONFIG` pointed at copied configs in `/tmp/summarizer-bakeoff/`.

| Model | Structural pass | Keyword recall | Judge mean (indep) | Note |
|---|---|---|---|---|
| `llama3.1:8b` (current) | 100% | 100% | 4.33 | baseline, unchanged |
| `qwen3.5:latest` (6.6GB) | 100% | 93.3% (run 2) / 86.7% (run 1) | **5.0** | best judge score; recall jitter |
| `ornith:9b` (5.6GB) | 66.7% (run 1: 6 sentences) / 100% (run 2) | 100% / 87.8% | 4.67 | violates 3-sentence contract intermittently |

Read: 3 rows is a smoke test, not a verdict. `qwen3.5:latest` is the only
candidate that beat the baseline on judge faithfulness; it slightly misses
keyword recall vs the incumbent. `ornith:9b` is unstable on the structural
contract. GPU headroom today: RTX 3060 12GB, ~2.8GB used — candidates must fit
~9.5GB; that rules out `mistral-small:22b` (12GB) until quantization or
offload.

**Next for a real bake-off (post-freeze or read-only):**
1. Expand golden set beyond 3 rows (sample real corpus units, follow the
   existing `golden_summaries.jsonl` schema: `source_excerpt`,
   `must_include_keywords`, `must_mention`).
2. Add quantized `mistral-small:22b` / `qwen3.6:35b-nothink` if VRAM allows.
3. Run each model N times to separate structural-contract stability from
   sampling noise (ornith run 1 vs run 2 shows why).
4. Add identifier/temporal-preservation checks (the bake-off spec's remaining
   dimensions beyond field accuracy).

## #6 Chroma evidence inventory (read-only)

- **Pinned:** `chromadb==1.5.9` in `requirements.txt` (`.venv` on py3.13).
- **Collections:** `knowledge_units` (~13.6k active units) and
  `conversation_summaries` (~1.9k), cosine HNSW.
- **API surface used** (`chroma_store.py`, 532 lines): `upsert`, `query`
  (embedding top-k, fetch-3x + in-Python superseded filter), `get(where=…)`
  for source_path/superseded scans, `count`, metadata update, delete-by-source.
- **Chroma-specific couplings:** sqlite write-lock contention handling
  (`is_chroma_contention_error`), hnswlib SegmentAPI compat shim (the
  `dec_test_nonempty_upsert` regression), legacy collection metadata without
  `convmem:embed_model` (doctor WARN), C3/C7 writer-lease path in
  `chroma_write_store.py`, shadow-sink emit on write.
- **Consumers:** `convmem.py`, `propose_decision.py`, `complete_data_restore.py`,
  `shadow_replay.py`, `chroma_readonly.py`, `eval_corpus/shadow_build.py`.

Working read: the store boundary is already abstracted (`ChromaStore`,
read/write split), so a migration surface exists — but the lease, contention,
and restore machinery is Chroma-shaped. There is **no measured deficiency** on
the table; per the recommendation list, correct default is **stay** unless a
benchmark shows one.

## Asks to the other lanes

- **Kiro (design review / sign-off):** review the bake-off methodology
  (golden-set expansion, repetition for contract stability, VRAM constraint)
  and the stay-unless-measured position on Chroma. Read-only; no implementation.
- **Codex (planning, post-freeze execution):** after 2026-08-07T00:00Z, plan
  the full bake-off expansion (larger golden set + stability runs) and, if a
  measured Chroma deficiency appears, a migration assessment doc. Execution
  stays on a `convmem work start` branch — never `main`.

## Expanded golden-set stability runs (30 rows × 5 runs, 2026-08-02)

Real conversation pairs sampled from indexed Cursor/Codex/Kiro transcripts
(`/tmp/summarizer-bakeoff/golden_summaries_expanded.jsonl`, same schema as the
repo fixtures; every `must_mention` validated present in its excerpt).

| Model | Structural mean | Recall mean | Judge mean | Failure rate |
|---|---|---|---|---|
| `llama3.1:8b` (current) | **0.653** | 0.828 | 4.10 | 0.347 |
| `qwen3.5:latest` | **0.813** (+16pts) | **0.866** (+3.8pts) | **4.70** | **0.187** |
| `ornith:9b` | 0.673 | 0.861 | 4.62 | 0.327 |

Per-row structural (30 rows): qwen3.5 wins **14**, ties **16**, loses **0**
vs llama3.1. On the 3-row repo fixture qwen3.5's recall looked worse; on the
30-row real-pair set it is better on every axis. The 3-row golden set was too
small and too easy (llama scored 100% there vs 65% on real pairs).

Caveat: single GPU, 5 runs, judge is DeepSeek V4 Flash (advisory). Enough for
a **recommendation**, not yet a production switch.

**TL;DR for #3:** `qwen3.5:latest` is the first candidate with real,
consistent improvement over the incumbent on the expanded set — recommend
10-run confirmation + identifier/temporal checks before the post-freeze switch.

## 10-run confirmation + identifier/temporal checks (2026-08-02)

30 rows × **10 runs** (300 summaries per model):

| Model | Structural | Recall | Judge | Failure rate |
|---|---|---|---|---|
| `llama3.1:8b` (current) | 0.667 | 0.829 | 4.14 | 0.333 |
| `qwen3.5:latest` | **0.820** | **0.854** | **4.74** | **0.180** |

Identifier/temporal preservation (1 run, 28 rows / 48 id pairs):

| Model | ID preservation | Date-row preservation |
|---|---|---|
| `llama3.1:8b` | 0.563 | 0.421 |
| `qwen3.5:latest` | **0.625** | 0.421 |

**Verdict:** qwen3.5 wins every metric on the 10-run set; ID preservation is
better, date preservation is a tie. Both models drop `dec_prop_…` ids and
line numbers (e.g. `:1668`) — a shared summarizer ceiling worth a prompt
change later, not a switch blocker.

**Recommended action (post-freeze 2026-08-07):** switch
`summarize_model = "qwen3.5:latest"` in `~/.config/convmem/config.toml` on a
`convmem work start` branch, re-run `scripts/eval-summaries.py --update-baseline`,
soak a few real ingests. Do **not** switch during the C7 freeze.

## Codex read-only planning verdict (2026-08-02, `codex exec --sandbox read-only`)

- **#3:** pilot is a smoke test, not a selection result. Post-freeze plan:
  1. 30–50-row golden set, stratified (short/long, decisions, debugging,
     WordPress, inter-model, identifiers, dates/sequences, ambiguous excerpts),
     schema unchanged;
  2. identical copied configs, same golden file, `--judge --baseline`, harness
     unchanged;
  3. 10 repeated runs per model; report mean/min/stddev/failure rate per row,
     not just aggregates;
  4. DeepSeek judge = advisory; decide on reproducible hard-gate + recall.
     A candidate must not replace `llama3.1:8b` without a material quality gain
     and no structural/recall regression.
- **#6:** staying is justified as current default — no measured deficiency;
  migration carries lease/contention/restore/HNSW/shadow-sink risk. Conditional:
  reopen only after measuring query latency, writer contention, rebuild/restore
  time, metadata-filter cost, failure recovery against a concrete replacement.

## Freeze compliance

No tracked files touched, no commits, no config/corpus mutation. Bake-off
configs live in `/tmp/summarizer-bakeoff/`. This doc is an untracked inbox
file like the other pending handoffs.
