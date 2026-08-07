# Crush handoff — qwen3.5 summarizer saturates the GPU; ingest timeouts drop chunks silently

**To:** Claude (cloud, advisory) — request: concrete suggestions, ranked
**From:** Crush (investigation lane)
**Date:** 2026-08-06
**Mode:** Read-only analysis. No fix applied yet. Two one-line candidate fixes
identified; want a sanity check and better options before touching anything.

## TL;DR

Since `summarize_model = "qwen3.5:latest"` went live (2026-08-06, after a
bakeoff vs `llama3.1:8b`), the single GPU is saturated by the 6.6 GB summarizer
at `-np 1`. Every new index run then hits ollama timeouts on the *embed* calls
(hardcoded 120 s, `llm.py:40`) and sometimes on summarize itself; `ingest.py`
catches the exception and `continue`s — **chunks are silently skipped**. The
corpus degrades without any failure flag, and watch re-processes the same old
sessions, so it looks like endless "catching up".

The two obvious fixes are one-liners: (a) raise the embed timeout 120 → 600 s,
or (b) move summarize to DeepSeek cloud (`deepseek-v4-flash`, key present) the
way distill already is. We want Claude's read on those plus anything smarter
(parallelism, chunk sizing, batching, queueing).

## Symptom (live evidence, 2026-08-06 evening)

GPU: RTX 3060 12 GB — 9310/12288 MiB used, 95 % util.

| PID | Process | GPU mem | Note |
|---|---|---|---|
| 3220257 | `llama-server` qwen3.5:latest (ollama runner, port 33459) | 6648 MiB | `-np 1`, `-c 8192`, `--keep 4`, actively generating |
| 2887448 | `convmem mcp_server.py` (Crush-launched) | 2594 MiB | Idle; embedding model/CUDA context |

Watch journal (`journalctl --user -u convmem-watch`), today:

```
21:12:48 [warn] chunk 400 distill failed: Response ended prematurely
21:12:48 [warn] chunk 500 summarize failed: HTTPConnectionPool(host='localhost',
                  port=11434): Read timed out. (read timeout=120)
21:12:48 [warn] chunk 650 distill failed: Response ended prematurely
21:12:48 [warn] chunk 850 distill failed: Response ended prematurely
21:20:42 [warn] unit embed failed: HTTPConnectionPool(host='localhost',
                  port=11434): Read timed out. (read timeout=120)
```

## Root-cause chain

1. `config.toml:30` — `summarize_model = "qwen3.5:latest"` (switched 2026-08-06;
   see `CODEX-2026-08-02-summarizer-switch-decision.md` for why the model won).
   qwen3.5 is a 6.6 GB model; the runner runs at `-np 1`, so one generation at a
   time, minutes per chunk summary.
2. `ingest.py:623-644` — per chunk: `summarize()` → `ollama_embed()` → `distill()`.
   All three go through the same ollama daemon; embed and distill queue behind
   the running summary.
3. `llm.py:40` — `ollama_embed` has a **hardcoded `timeout=120`**. `generate()`
   (`llm.py:250`) defaults to 300 s. The journal's "read timeout=120" on the
   *summarize* path is unexplained given the 300 s default — see Q2.
4. `ingest.py:638` — `except Exception: print(warn); continue` → the chunk is
   skipped, no retry, no metric. Coverage loss is silent.
5. Watch (`watch.py`, systemd daily 24 h unit, `subprocess_index=on`, 90 s
   debounce) re-indexes the same old sessions repeatedly (e.g. the 08/03 and
   08/04 rollouts were indexed 2026-08-05 17:59 **and** 2026-08-06 21:26+),
   amplifying the queue.

## Context that matters

- Corpus: 16.4 k units, 2.3 k summaries; batch of 77 Codex sessions indexed
  around 2026-08-02 ("corpus doubling") is done; current backlog is a handful
  of files, not the issue.
- `embed_model = "nomic-embed-text"` (323 MB) — fast *when served*, but queues
  behind the summarizer.
- `distill_model = "deepseek-v4-flash"` (cloud) already — `DEEPSEEK_API_KEY` is
  present (doctor PASS). The config comment saying "No DeepSeek key is present
  on this machine" is stale and contradicts that.
- Partial synthesis on timeout already exists for the *ask* path (P1c); the
  ingest chunk-skip path has no such affordance.
- Branch `fix/2026-08-06-summarizer-switch-baseline-and-docs` — the summarizer
  switch is deliberately being baselined right now, so a timeout/config fix
  belongs on this branch.

## Questions for Claude

1. **Which is better: raise the embed timeout, or move summarize to
   `deepseek-v4-flash` (cloud)?** Local qwen3.5 won the bakeoff on quality; is
   the quality delta worth GPU saturation, or should summarize follow distill
   to the cloud and keep qwen3.5 for batch jobs only?
2. **Why did summarize report "read timeout=120" when `_ollama_generate`'s
   default is 300 s?** Hardcoded 120 s appears only in `ollama_embed`. Is there
   another path, or a stale worktree checkout in the subprocess index run?
3. **Better throughput levers on the 12 GB card:** raise `num_parallel` (the
   `-np 1` runner + 2.6 GB mcp_server leaves ~3 GB headroom — enough for a
   second slot at reduced ctx?), shrink `_MAX_CHUNK_CHARS` (8000, `llm.py:30`)
   / `num_ctx` 8192, or batch embeddings?
4. **Silent-skip hygiene:** should `ingest.py:638` record failures to
   `synthesis_failures.jsonl` (a file that already exists) and count them, so
   coverage loss is measurable? Any cheap retry-with-backoff scheme?
5. **Re-index churn:** why does watch reprocess unchanged sessions — is the
   processed-log hash comparison (`watch_skip_reason` / `processed.json`)
   failing for these files, and is that a separate bug?
6. Anything else obvious we're missing (OLLAMA_MAX_LOADED_MODELS, keep_alive
   tuning, schedule-aware ingest)?

## Constraints

- Quality bar: qwen3.5 won the bakeoff; don't casually regress it.
- No new dependencies. Prefer config/one-line code changes.
- Reversible changes only; this is an investigation, not a design review.

## Files to read

- `config.toml` (`~/.config/convmem/config.toml`): models section, lines 22-33
- `llm.py`: `ollama_embed` (line 40), `generate` (line 250), `summarize` (line 269)
- `ingest.py`: per-chunk summarize/embed/distill block, lines 595-660
- `watch.py`: debounce + subprocess indexing, lines 180-260, 288-370
- `docs/inter-model/CODEX-2026-08-02-summarizer-switch-decision.md`: why qwen3.5
