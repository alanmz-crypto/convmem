# convmem — Conversation Memory for AI Coding Assistants

Local-first system that ingests AI chat logs and **tool-sourced evidence** into ChromaDB, then lets you search, ask (RAG), verify, and traverse evidence chains.

**No cloud database. No web app.** File-based config + Chroma on disk. `convmem ask` uses **DeepSeek v4** (`deepseek-v4-flash`) when `DEEPSEEK_API_KEY` is set.

---

## What this does now

1. **Harvests** chat history (Cursor, Kiro, Continue, Aider, Crush, Open WebUI) → distilled knowledge units
2. **Ingests** scanner observations (wp-sec, Lighthouse) via `convmem add` with stable ledger ids
3. **Searches** via embedding + optional cross-encoder rerank
4. **Answers** with citations via `convmem ask` (DeepSeek synthesizes from retrieved excerpts)
5. **Verifies** cross-model checks via `convmem verify`
6. **Traverses** evidence graphs via `convmem related`
7. **Re-ranks** ask results by resolution status via `convmem ask --evidence`

Past conversations and security findings become a **queryable evidence bus** — not live agent-to-agent chat.

**First webdev target:** `staging2.willowyhollow.com`

---

## Quick start (existing install)

```bash
source ~/.config/convmem/env.local   # DEEPSEEK_API_KEY + convmem alias
convmem stats
```

If `convmem` is not defined:

```bash
~/miniforge3/envs/convmem/bin/python ~/Projects/convmem/convmem.py stats
```

---

## Architecture

```
Chat logs ──► ingest.py + distill.py ──► knowledge_units ──┐
                                                            ├──► ChromaDB
Tools (wp-sec, Lighthouse) ──► observe.py (add/upsert) ──┘
                                        │
                    ledger.py (Observation / Decision / Verification)
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
   query / search                   convmem ask                    convmem related
   (semantic)                  (RAG + DeepSeek v4)              (graph traversal)
                                        │
                              ask --evidence (evidence.py)
                              unresolved > failed > resolved
```

**Persistence:** JSONL exchange format at ingest + Chroma only. No graph DB.

---

## Milestones (signed off)

| Milestone | What | Key commands / files |
|-----------|------|---------------------|
| **A** | Evidence ledger storage | `ledger.py`, `convmem add`, `export_report_to_observations.py` |
| **B** | Graph navigability | `build_ledger_index()`, `convmem related` |
| **C** | Scanner auto-ingest + upsert | `export_lighthouse.py`, `add --upsert`, `scripts/ingest-*.sh` |
| **E** | Evidence-aware ask | `evidence.py`, `ask --evidence` |
| **D** | OpenClaw probes | *deferred* |
| **F0/F1/F2b** | Always-on watch + refine + monitor | See [docs/MILESTONE-F.md](docs/MILESTONE-F.md), [docs/MINIPC-DEPLOY.md](docs/MINIPC-DEPLOY.md) |

---

## CLI reference

### Search & ask

```bash
convmem "csp headers"                          # semantic search (knowledge units)
convmem "topic" --raw                          # fallback: conversation summaries
convmem "topic" --top 10 --domain web_stack.security

convmem ask "What CSP fixes did we try on staging?"
convmem ask "What security issues remain unresolved?" --domain web_stack.security --evidence
convmem ask -i                                 # interactive multi-turn
```

`--evidence` re-ranks by ledger graph: prefers **unresolved** observations and **failed** verifications; deprioritizes resolved/passed. Does not auto-detect intent — flag must be explicit. Skips raw-summary hybrid fallback.

**Ask model:** `config.toml` → `[models] distill_model = "deepseek-v4-flash"`. Requires `DEEPSEEK_API_KEY` in `~/.config/convmem/env.local`.

### Evidence ledger

```bash
convmem add --file observations.jsonl              # append-only (default)
convmem add --file observations.jsonl --upsert     # update by stable ledger id

convmem verify obs_staging2_wpsec_csp-missing --model kiro-review --confidence 0.95
convmem related obs_staging2_wpsec_csp-missing     # graph traversal (not search)
```

### Index & stats

```bash
convmem index
convmem index --file /path/to/transcript.jsonl
convmem watch                    # F0: inotify + debounced incremental index
convmem watch --debounce 15
convmem stats
convmem open PATH
```

**Refine (F1):**

```bash
convmem refine --once --job chroma_dedupe --limit 20
convmem refine --once --job confidence_audit
convmem refine --once --job backfill_domain --limit 10   # LLM — uses DeepSeek
convmem refine --stats
convmem refine                     # daemon (systemd on miniPC)
convmem monitor --site staging2.willowyhollow.com          # F2b HTTP probes
convmem monitor --site staging2.willowyhollow.com --dry-run
./scripts/monitor-staging2.sh

Always-on deploy: [docs/MINIPC-DEPLOY.md](docs/MINIPC-DEPLOY.md) (watch + refine + monitor timer).
```

Tombstoned duplicates are hidden from search/stats (`superseded: true` in metadata). See `systemd/convmem-refine.service.example`.

### Scanner ingest (staging2)

```bash
./scripts/ingest-wp-sec.sh staging2.willowyhollow.com
./scripts/ingest-lighthouse.sh staging2.willowyhollow.com [lhci-dir]
```

`wp-sec-agent/run.sh` auto-exports + ingests if `convmem` is on PATH (`--upsert`).

---

## Stable ledger IDs

Pattern: `obs_<site>_<producer>_<audit_key>` — **no counters**, deterministic across reruns.

| Example | Source |
|---------|--------|
| `obs_staging2_lh_csp-xss` | Lighthouse |
| `obs_staging2_wpsec_csp-missing` | wp-sec / nikto |
| `obs_staging2_wpsec_wp-version` | wpscan |

Producers normalize: `lighthouse-ci` → `lh`, `wp-sec-agent` → `wpsec`.  
Site slug: first hostname label (`staging2.willowyhollow.com` → `staging2`).

Decisions and verifications link via `relates_to`:

```json
{"id":"dec_001","kind":"decision","relates_to":"obs_staging2_wpsec_csp-missing","summary":"Add CSP via nginx","author_model":"kiro-review"}
{"id":"ver_001","kind":"verification","relates_to":"obs_staging2_wpsec_csp-missing","result":"pass","author_model":"kiro-review"}
```

See `examples/chain-demo.md` and `examples/AGENTS-FLOW.md`.

---

## File map

| File | Role |
|------|------|
| `convmem.py` | CLI entry |
| `config.py` | Load `~/.config/convmem/config.toml` |
| `ingest.py` | Chat ingest pipeline |
| `distill.py` | LLM distillation → knowledge units |
| `observe.py` | Ledger ingest (`add`, `add --upsert`) |
| `ledger.py` | Observation/Decision/Verification contract + `build_ledger_index()` |
| `ledger_ids.py` | Stable semantic id helpers |
| `evidence.py` | Evidence-aware re-ranking for `ask --evidence` |
| `related.py` | `convmem related` display |
| `verify.py` | Cross-model verification |
| `export_lighthouse.py` | Lighthouse LHR → observations.jsonl |
| `export_report_to_observations.py` | wp-sec results → observations.jsonl |
| `ask.py` | RAG: retrieve → DeepSeek answer + citations |
| `query.py` | Retrieval, rerank, Rich display |
| `chroma_store.py` | `add_unit`, `update_unit` (doc+embed+meta) |
| `llm.py` | Ollama embed + DeepSeek generate |
| `domains.py` | Domain taxonomy + hierarchical filter |
| `scripts/ingest-wp-sec.sh`, `ingest-lighthouse.sh` | Scanner → export → add |
| `tests/` | Unit tests (see below) |

---

## Setup (fresh machine)

### Dependencies

```bash
mamba create -n convmem python=3.12
mamba activate convmem
pip install -r requirements.txt
```

Requires **Ollama** (`nomic-embed-text`, `llama3.1:8b` or similar).  
Optional: **`DEEPSEEK_API_KEY`** for distillation and `convmem ask`.  
Rerank: `sentence-transformers` + `BAAI/bge-reranker-v2-m3` (see CUDA note below).

#### CUDA torch (reranker)

`rerank.py` loads the cross-encoder with `device="cuda"`. A plain `pip install -r requirements.txt` pulls **CPU-only** torch via `sentence-transformers`, so reranking falls back to CPU (slow, no error).

On a machine with an NVIDIA GPU, install a **CUDA build of torch first**, then the rest:

```bash
# Example: CUDA 12.x wheels — pick the index URL matching your driver/toolkit
# https://pytorch.org/get-started/locally/
pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```

Verify: `python -c "import torch; print(torch.cuda.is_available())"` should print `True` before relying on rerank latency.

### Config

```bash
mkdir -p ~/.config/convmem ~/.local/share/convmem
cp config.example.toml ~/.config/convmem/config.toml
```

```bash
# ~/.config/convmem/env.local
export DEEPSEEK_API_KEY=your-key-here

convmem() {
  ~/miniforge3/envs/convmem/bin/python ~/Projects/convmem/convmem.py "$@"
}
```

### First index

```bash
cd ~/Projects/convmem
python inventory.py
convmem index          # first run: slow
convmem stats
```

---

## Testing guide (for DeepSeek v4 / automated QA)

DeepSeek's role: run `convmem ask`, evaluate answer quality against retrieved citations, and report gaps. Use the checklist below.

### 1. Unit tests (no API key needed)

```bash
cd ~/Projects/convmem
~/miniforge3/envs/convmem/bin/python -m unittest discover -s tests -v
```

Expect **28 tests, all OK** — covers ledger graph, stable ids, upsert, evidence rerank, ask dedupe.

### 2. Seed evidence chain (optional, for graph/ask tests)

```bash
convmem add --file examples/observations.jsonl
convmem add --file examples/decision.jsonl
convmem add --file examples/verification.jsonl
```

### 3. Graph traversal (no LLM)

```bash
convmem related obs001
convmem related dec_001
convmem related obs999          # expect exit 1, clear error
```

### 4. Scanner export (no LLM)

```bash
python export_report_to_observations.py \
  --site staging2.willowyhollow.com \
  --results-dir ~/Projects/wp-sec-agent/clients/staging2.willowyhollow.com/results \
  --print | head -5

# Stable ids should repeat on rerun (same audit → same id)
```

### 5. Upsert idempotency (Ollama embed only)

```bash
convmem stats                     # note unit count N
convmem add --file /tmp/obs.jsonl --upsert
convmem stats                     # count still N, updated≥1
```

### 6. Ask tests (needs DEEPSEEK_API_KEY + Ollama)

```bash
source ~/.config/convmem/env.local

# Baseline semantic ask
convmem ask "What security header issues exist on staging2?" \
  --domain web_stack.security --top 5

# Evidence-aware (should surface unresolved findings higher in citations)
convmem ask "What security issues remain unresolved on staging2?" \
  --domain web_stack.security --evidence --top 5
```

**What to check in ask output:**

- Answer cites `[1]`, `[2]` matching the References section
- References show `ledger: obs_staging2_…` for tool-sourced units
- With `--evidence`, citations may show yellow status labels: `unresolved`, `failed check`, `resolved`
- If excerpts are thin, a yellow Warning panel appears (low retrieval confidence)
- Answer should **not invent** fixes not present in excerpts — should say when index lacks detail

### 7. Compare `--evidence` vs plain ask

Run the same question with and without `--evidence`. Unresolved wp-sec observations should rank higher with the flag. Resolved/verified items should drop in citation order.

### 8. Ingest staging2 corpus (if not already done)

```bash
./scripts/ingest-wp-sec.sh staging2.willowyhollow.com
convmem related obs_staging2_wpsec_csp-missing
```

---

## Search layers

| Layer | Collection | When |
|-------|------------|------|
| **Primary** | `knowledge_units` | Default; needs ≥50 units for full quality |
| **Fallback** | `conversation_summaries` | `--raw` flag |

Rerank: fetch 20 → CrossEncoder → top 5 (`[query] rerank = true`). Displayed `score` is embedding similarity, not rerank score.

**Domain filter:** `--domain web_stack.security` matches children. Legacy units without `domain` are **excluded** from domain-scoped queries (still appear in unscoped search).

---

## Known limits

| Limit | Notes |
|-------|-------|
| Rerank can't fix recall | Right unit must be in top-20 embedding hits |
| **Cursor `store.db`** | Indexed via `latestRootBlobId` blob walk — Composer chats not covered by JSONL alone |
| Crush `.crush/crush.db` | Indexed via `**/.crush/crush.db` home glob — run `python inventory.py` after new projects |
| `units_export` on upsert | `knowledge_units.jsonl` only appends on add, not update |
| `find_unit_by_ledger_id` | Full metadata scan; fine at ~1.5k units |
| OpenClaw probes | Milestone D deferred |
| Privacy | Index contains real conversations — don't share `~/.local/share/convmem/` |

---

## Agent roles

| Agent | Role |
|-------|------|
| **DeepSeek** | `convmem ask` synthesis + test/QA per this guide |
| **Kiro** | Review, decisions, verifications, sign-off |
| **Cursor** | Implementation |
| **ChatGPT** | Orchestration (optional) |

Workflow: `examples/AGENTS-FLOW.md`

---

## Build history

| Step | Shipped |
|------|---------|
| 1–7 | Adapters, ingest, distill, rerank, Rich TUI, ask, open |
| 8 | Domains, observations, verify |
| A | Evidence ledger contract + wp-sec export |
| B | `convmem related`, `build_ledger_index()` |
| C | Stable ids, Lighthouse export, `--upsert`, scanner hooks |
| E | `ask --evidence` |

**Live corpus (approx.):** ~1470+ knowledge units (majority legacy chat distillations without `ledger_id`).

---

## Quick sanity check

```bash
convmem stats
python -m unittest discover -s tests -v
convmem ask "summarize what you know about convmem" --top 3
```

If units < 50, primary search works but warns to use `--raw` or finish backfill.
