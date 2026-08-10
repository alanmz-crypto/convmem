# Crush session handoff — qwen3.5 GPU contention diagnosis and fix

**From:** Crush (investigation + implementation)
**Date:** 2026-08-06 / 2026-08-07
**PR:** [#140](https://github.com/alanmz-crypto/convmem/pull/140) — squash-merged to `main` as `657336d`
**Corpus at close:** 16.5k+ units, 2.3k summaries, 230 Crush session units indexed

## TL;DR

Diagnosed and fixed qwen3.5 summarizer saturating the RTX 3060 GPU at 95% util, causing ollama embed calls to blow 120s timeouts and silently drop ingested chunks. Four mitigations applied, Kiro-reviewed, pylint clean, zero timeouts confirmed, merged.

## What was wrong

- `summarize_model = "qwen3.5:latest"` (6.6 GB, `-np 1`) sat on the single GPU slot
- Every chunk's embed and distill calls queued behind it → 120s read timeout → `ingest.py:638` `continue`d silently
- `OLLAMA_MAX_LOADED_MODELS=1` forced qwen3.5 and nomic-embed-text to unload/reload per chunk
- Watch journal: 4+ timeout/failure lines per index run, chunks dropped with zero visibility

## What was done

| # | Change | File |
|---|--------|------|
| 1 | `summarize_model = "deepseek-v4-flash"` (cloud, key present) | `~/.config/convmem/config.toml` |
| 2 | `ollama_embed` timeout 120 → 300 s | `llm.py:40` |
| 3 | `OLLAMA_MAX_LOADED_MODELS=2` (was 1) | `/etc/systemd/system/ollama.service.d/override.conf` |
| 4 | Chunk failure logging to `synthesis_failures.jsonl` + 3-attempt retry (5s/30s backoff) | `ingest.py` |
| 5 | Restored dynamic test/corpus count language | `README.md`, `docs/ROADMAP.md` |
| 6 | Updated active handoff | `docs/inter-model/LATEST.md` |

## Review chain

- **Crush** — initial investigation (GPU + journal evidence, root-cause chain)
- **Claude cloud** — advisory review, ranked action list, co-location diagnosis, 6 answered questions
- **Kiro** — design review: initial FAIL (stale doc counts) → fixed → PASS
- **Pylint** — regression gate PASS (499 findings, 0 new/increased)
- **Ryan** — squash-merge approved

## Key docs produced

- `docs/inter-model/CRUSH-2026-08-06-summarizer-gpu-timeout-handoff.md` — Claude's analysis + our evidence
- `docs/inter-model/LATEST.md` — updated active handoff entry

## What remains (not addressed)

- **11 unresolved observations**: 5 staging2 security headers (CSP, HSTS, Referrer-Policy missing), 6 retrieval/tooling gaps
- **5 untracked inter-model docs** in working tree (pre-existing from other sessions)
- **Claude items #7-8** deferred: shrink `num_ctx` to 4096 for batch qwen3.5 runs, test `-np 2`
- **Watch re-index churn** — confirmed hash-based staleness already implemented; re-indexes were from live Codex session appends, not a bug

## Artifacts for synthesis

- Branch: `fix/2026-08-06-summarizer-switch-baseline-and-docs` (merged, deleted locally)
- Commits: 7 → squash-merged as 1 (`657336d`)
- PR: #140
- Session: this Crush chat indexed (230 units)
- GPU verification: `nvidia-smi` clean, `journalctl --user -u convmem-watch` zero timeouts post-fix
