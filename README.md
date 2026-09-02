# convmem — Personal conversation memory and evidence retrieval for AI coding assistants

A local-first working system I build and use for my own AI-assisted development workflow. It ingests AI chat logs, inter-model documents, and **tool-sourced evidence**; maintains a local searchable corpus plus durable records and recovery metadata; and exposes retrieval, synthesis, evidence traversal, and guarded operational controls through the CLI and MCP.

**Storage is local:** the corpus, durable exports, and Chroma projection live on the workstation; there is no cloud database or web app. If a provider-backed model is configured, retrieved context or source material may be sent to that provider for synthesis or distillation. My current configuration uses local Ollama for embeddings/summaries and `deepseek-v4-flash` for provider-backed generation.

---

## Status: Personal project

`convmem` is a working system I build and use for my own AI-assisted development workflow. It is public because I’m happy for people to inspect it, learn from it, or adapt it, but it is not currently packaged or maintained as a turnkey application for general installation. Expect a working but evolving codebase, personal deployment assumptions, experimental features, and documentation that sometimes describes my own environment. Contributions and cleanup are not expected; I optimize the repository for my own workflow first.

This README serves two purposes: it explains the architecture for curious readers and records the operational commands I use on my own workstation. Paths, hosts, model names, and deployment instructions below may be specific to my setup. If you are an agent helping with this repository, read [`AGENTS.md`](AGENTS.md) for repository workflow and safety rules; this README is project and personal-operations context.

> **Personal-data warning:** My local corpus contains real AI conversations and security findings. The repository does not contain that corpus, but do not publish or share `~/.local/share/convmem/`.

---

## New here? Choose the right entrance

This README explains the project shape. It is not the live status record, and it does not replace the repository's agent protocol.

### Understand the technical/research project

Start with [`docs/RESEARCH.md`](docs/RESEARCH.md). It explains the research
problem, mechanism, evaluation claims, threats to validity, reproducibility
boundary, and the code-reading path without requiring the repository's
agent-governance documents. Then inspect the concrete [evidence-chain
example](examples/chain-demo.md) and the implementation/evaluation locations it
links.

### Work on ConvMem as an agent or developer

For a clean-context agent or someone operating the personal system:

1. Run `convmem doctor` and wait for exit 0.
2. Run `convmem brief --stdout-only`, then `convmem unresolved`. These report current workstation, corpus, and open-observation state; static counts in documents can age.
3. Read [`AGENTS.md`](AGENTS.md) for repository safety, branch/worktree, authorization, and session rules.
4. Follow [`docs/STATUS.md`](docs/STATUS.md), which gives the maintained documentation reading order.
5. Read [`docs/MODEL-WORKFLOW.md`](docs/MODEL-WORKFLOW.md) for operational routing and the prod/lab boundary.
6. If the task belongs to a named arc, read its active [`docs/plans/STATUS-*.md`](docs/plans/) brief before changing anything.
7. Use [`docs/inter-model/STATUS.md`](docs/inter-model/STATUS.md) and dated handoffs for cross-arc context, but verify their date and branch state before treating them as current.

Do not infer current state from an old handoff, a historical milestone label, or a filename alone. Archived documents are historical context; the status pointer explains how to connect them to current work.

## Current capabilities

These are current personal capabilities, not a promise that every path is equally mature or supported as a general-purpose product.

- **Ingests** chat sessions and coordination documents through adapters for Cursor, Kiro, Continue, Aider, Crush, Open WebUI, Codex, Copilot CLI, OpenCode, inter-model documents, and Kiro steering. The adapters recognize several on-disk formats, including JSONL, SQLite, JSON, and Markdown.
- **Records** tool observations, decisions, and verifications with stable ledger IDs and explicit relationships.
- **Retrieves** conversation and evidence units with embeddings, lexical fallback, optional cross-encoder reranking, domain/site scope, recency, and provenance-aware signals.
- **Answers** questions with RAG citations through `convmem ask`; `--evidence` prioritizes unresolved observations and failed verifications.
- **Traverses and triages** evidence with `convmem related`, `convmem unresolved`, and the ledger-backed decision/verification view.
- **Orients and operates** agent sessions with `doctor`, `brief`, `tldr`, `scope`, and `agent-run`; the same core is exposed through the local MCP server and generated agent-protocol surfaces.
- **Experiments under explicit gates** with shadow-ledger, writer-census, provenance, recovery, and evaluation machinery. These are real repository subsystems, but several remain disabled, experimental, blocked, or separately authorized; read the relevant status brief before treating one as live.

Past conversations and security findings become a **queryable evidence layer** — not live agent-to-agent chat. The repository also contains the controls used to test, govern, back up, recover, and evaluate that layer.

**Personal development roadmap:** [docs/ROADMAP.md](docs/ROADMAP.md)

**Current personal deployment:** `staging2.willowyhollow.com`

**Typical query:**

```bash
convmem ask "What CSP fixes did we try on staging?"
```

The answer is synthesized from retrieved excerpts and includes citations. This reflects my current workflow, not a hosted service.

---

## Quick start (existing personal install)

```bash
source ~/.config/convmem/env.local   # DEEPSEEK_API_KEY + convmem alias
convmem stats
```

**After data loss:** see [docs/RECOVER.md](docs/RECOVER.md). MCP wiring examples live in `config/*.example`.

If `convmem` is not defined:

```bash
~/miniforge3/envs/convmem/bin/python ~/Projects/convmem/convmem.py stats
```

---

## Mental model and architecture

```
Chat logs / SQLite / JSONL / Markdown ──► adapters + ingest ──┐
Inter-model docs / agent protocols ─────► normalization/chunking ─┤
Tool observations / decisions / checks ──► ledger + provenance ───┘
                                      │
               Chroma corpus + JSONL exports + approval records
                                      │
                 retrieval, evidence, and recovery controls
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
   search/query                 ask (RAG)                 related/unresolved
   scope + rerank          configured model + citations     ledger relationships
        │                             │                             │
        └────────────── CLI + local MCP + agent protocol ───────────┘
                                      │
                    watch / refine / monitor background services
```

**Persistence and authority:** the default data root contains Chroma collections, `knowledge_units.jsonl`, processed/inventory state, decision queues and approval records, agent-run events, and optional shadow/recovery data. Authority is record- and arc-specific: current Phase 0 documentation preserves Chroma `knowledge_units` as the Tier-1 authority for the existing observation/search path, while `decisions-approved.jsonl` remains authoritative for approved decision intent and newer ledger-first/recovery work defines bounded paths toward more rebuildable projections. The JSONL export is useful for backup/replay but is incomplete and mutable today; do not assume it alone reconstructs every current unit. See [the current authority map](docs/audit-ledger-first/CURRENT-OBSERVATION-AUTHORITY.md) and [recovery guidance](docs/RECOVER.md). There is no separate graph database: `related` and evidence-aware ranking traverse ledger metadata and relationships.

**Deployment:** This is a single-workstation system. By default, persistent data is under `~/.local/share/convmem/`, configuration is under `~/.config/convmem/`, and Ollama runs locally. Optional user systemd units (`watch`, `refine`, `monitor`, and backup/digest jobs) run on the same machine — see [docs/SYSTEMD-DEPLOY.md](docs/SYSTEMD-DEPLOY.md). MCP clients and agent hooks are local adapters to the same core; this repository does not document a turnkey remote corpus service.

The core retrieval path can run without a hosted model. Provider-backed synthesis/distillation is configurable, and the current personal setup uses DeepSeek for those calls; inspect [`config.example.toml`](config.example.toml) before assuming a provider, model, or data-flow boundary.

---

## Historical milestone labels

These labels are internal checkpoints for my own development, not a public release roadmap or a complete description of current state. For current work, use the status path above and [`docs/ROADMAP.md`](docs/ROADMAP.md) only as planning context.

| Milestone | What | Key commands / files |
|-----------|------|---------------------|
| **A** | Evidence ledger storage | `ledger.py`, `convmem add`, `export_report_to_observations.py` |
| **B** | Graph navigability | `build_ledger_index()`, `convmem related` |
| **C** | Scanner auto-ingest + upsert | `export_lighthouse.py`, `add --upsert`, `scripts/ingest-*.sh` |
| **E** | Evidence-aware ask | `evidence.py`, `ask --evidence` |
| **D** | OpenClaw probes | *deferred* |
| **F0/F1/F2b** | Always-on watch + refine + monitor | See [docs/MILESTONE-F.md](docs/MILESTONE-F.md), [docs/SYSTEMD-DEPLOY.md](docs/SYSTEMD-DEPLOY.md) |

---

## CLI reference

The complete command surface is available from `convmem --help`. The commands below highlight the stable personal workflow; several lifecycle, shadow, recovery, and evaluation commands are intentionally guarded or status-dependent.

### Orientation and current operations

```bash
convmem doctor
convmem brief --stdout-only
convmem tldr
convmem unresolved
convmem scope show
convmem agent-run --help
convmem shadow-inventory
convmem writer-census-status
```

`doctor`, `brief`, and `unresolved` are read-only orientation checks. `agent-run` records client-neutral run lifecycle evidence. Shadow-ledger and writer-census commands report or advance separately authorized operational paths; they do not imply that Shadow is enabled.

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

**Ask model:** `config.toml` → `[models] distill_model = "deepseek-v4-flash"` in my current setup. The generation model is configurable; using DeepSeek requires `DEEPSEEK_API_KEY` in `~/.config/convmem/env.local`.

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
convmem refine --once --job backfill_domain --limit 10   # LLM — uses configured model
convmem refine --stats
convmem refine                     # daemon (systemd user units)
convmem monitor --site staging2.willowyhollow.com          # F2b HTTP probes
convmem monitor --site staging2.willowyhollow.com --dry-run
./scripts/monitor-staging2.sh

Always-on deploy: [docs/SYSTEMD-DEPLOY.md](docs/SYSTEMD-DEPLOY.md) (watch + refine + monitor timer).
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
| `convmem.py` | CLI entry, including orientation, retrieval, evidence, run, shadow, and scope commands |
| `config.py` | Load `~/.config/convmem/config.toml` |
| `ingest.py` | Chat ingest pipeline |
| `distill.py` | LLM distillation → knowledge units |
| `observe.py` | Ledger ingest (`add`, `add --upsert`) |
| `ledger.py` | Observation/Decision/Verification contract + `build_ledger_index()` |
| `agent_run_ledger.py` | Durable client-neutral agent-run lifecycle events |
| `ledger_ids.py` | Stable semantic id helpers |
| `evidence.py` | Evidence-aware re-ranking for `ask --evidence` |
| `related.py` | `convmem related` display |
| `verify.py` | Cross-model verification |
| `export_lighthouse.py` | Lighthouse LHR → observations.jsonl |
| `export_report_to_observations.py` | wp-sec results → observations.jsonl |
| `ask.py` | RAG: retrieve → configured model answer + citations |
| `query.py` | Retrieval, rerank, Rich display |
| `chroma_store.py` | `add_unit`, `update_unit` (doc+embed+meta) |
| `llm.py` | Ollama embedding + configured generation |
| `domains.py` | Domain taxonomy + hierarchical filter |
| `mcp_server.py` | Local MCP adapter over the shared read/retrieval surfaces |
| `shadow_*.py`, `recovery_*.py`, `provenance*.py` | Guarded shadow, recovery, and provenance controls; see active status briefs |
| `eval_*/`, `eval_*.py` | Offline corpus, retrieval, synthesis, JudgeBench, and product-value evaluation machinery |
| `scripts/ingest-wp-sec.sh`, `ingest-lighthouse.sh` | Scanner → export → add |
| `tests/` | Unit tests (see below) |

---

## Personal workstation setup

The commands below describe the setup I use on my own workstation. Paths and environment details may need to be adapted elsewhere.

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

## My current QA workflow

This is my current personal QA workflow. It uses the configured generation model (currently `deepseek-v4-flash`) to run `convmem ask`, evaluate answer quality against retrieved citations, and report gaps. Use the checklist below as an operating guide, not as a complete public test contract.

### 1. Unit tests (no API key needed)

```bash
cd ~/Projects/convmem
~/miniforge3/envs/convmem/bin/python -m unittest discover -s tests -v
```

Expect the suite to finish **OK**. Do not trust hard-coded totals in docs — get the current count with `python -m unittest discover -s tests -q` (or `convmem brief --with-tests`). Coverage includes ledger graph, stable ids, upsert, Chroma approve-index regression, evidence rerank, ask dedupe, doctor, and protocol adapters.

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

Rerank: fetch 20 → semantic/lexical fusion and optional CrossEncoder → top 5 (`[query] rerank = true`). Displayed `score` is embedding similarity, not rerank score. `knowledge_units` is the current Tier-1 search surface; exports and approval records support backup/replay but do not form one complete canonical ledger today.

**Domain filter:** `--domain web_stack.security` matches children. Legacy units without `domain` are **excluded** from domain-scoped queries (still appear in unscoped search).

---

## Known limits

| Limit | Notes |
|-------|-------|
| Rerank can't fix recall | Right unit must be in top-20 embedding hits |
| **Cursor `store.db`** | Indexed via `latestRootBlobId` blob walk — Composer chats not covered by JSONL alone |
| Crush `.crush/crush.db` | Indexed via `**/.crush/crush.db` home glob — run `python inventory.py` after new projects |
| Durable JSONL export | Chat indexing appends then compacts repeated unit IDs; ledger upserts replace the matching ledger row. Use [docs/RECOVER.md](docs/RECOVER.md) and the focused tests before treating the export as immutable event history |
| `find_unit_by_ledger_id` | Full metadata scan; fine at ~1.5k units |
| OpenClaw probes | Milestone D deferred |
| Guarded infrastructure | Shadow activation, live capture, recovery publication, and evaluation calls have separate status/authorization boundaries |
| Documentation state | Dated handoffs and cross-arc snapshots can age; run `doctor`/`brief` and follow `docs/STATUS.md` before acting |
| Personal data | The index contains real conversations — don't share `~/.local/share/convmem/` |

---

## License

ConvMem's original code and documentation are available under the [MIT
License](LICENSE). Third-party dependencies and any third-party material
reproduced in this repository remain subject to their respective licenses or
copyright terms and are not relicensed by ConvMem's MIT license.

## Agents in my current workflow

These roles describe how I currently use multiple agents around this repository; they are not a required public contribution model.

| Agent | Role |
|-------|------|
| **DeepSeek** | `convmem ask` synthesis + test/QA per this guide |
| **Kiro** | Review, decisions, verifications, sign-off |
| **Cursor** | Implementation |
| **ChatGPT** | Orchestration (optional) |

Workflow: `examples/AGENTS-FLOW.md`

---

## Personal build history

This records internal implementation steps, not a public release history.

| Step | Shipped |
|------|---------|
| 1–7 | Adapters, ingest, distill, rerank, Rich TUI, ask, open |
| 8 | Domains, observations, verify |
| A | Evidence ledger contract + wp-sec export |
| B | `convmem related`, `build_ledger_index()` |
| C | Stable ids, Lighthouse export, `--upsert`, scanner hooks |
| E | `ask --evidence` |

**Live corpus size** drifts constantly — do not rely on a number in this README. Run `convmem doctor` or `convmem brief --stdout-only` for current knowledge-unit and summary counts. Many older units are legacy chat distillations without `ledger_id`.

---

## Quick sanity check

```bash
convmem stats
python -m unittest discover -s tests -v
convmem ask "summarize what you know about convmem" --top 3
```

If units < 50, primary search works but warns to use `--raw` or finish backfill.
