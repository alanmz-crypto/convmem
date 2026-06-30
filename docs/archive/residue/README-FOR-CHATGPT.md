# convmem — ChatGPT onboarding (inter-agent product layer)

You are joining an existing project. **Read this first**, then `examples/AGENTS-FLOW.md`.

This archive is **source + product guidance only** — no Chroma index, no API keys, no private chat logs.

---

## One-sentence pitch

**convmem** is a local memory bus: ingest AI chats + tool observations → searchable **knowledge units** → agents query, ask, and verify — without talking to each other directly.

---

## Repo location (live machine)

```
~/Projects/convmem/          # this codebase
~/Projects/wp-sec-agent/     # security scanner (feeds observations)
~/.local/share/convmem/      # runtime data (chroma, processed.json) — NOT in tarball
~/.config/convmem/           # config.toml + env.local (secrets)
```

---

## Build history (what exists today)

| Step | Shipped |
|------|---------|
| 1–3 | Adapters: Cursor jsonl, Kiro sqlite, Continue JSON, Aider markdown, Open WebUI sqlite |
| 4 | Ingest → `conversation_summaries` + `convmem index` + `--raw` search |
| 5 | Distillation → `knowledge_units` (solution/pattern/explanation/decision) |
| 6 | Cross-encoder rerank (`rerank.py`, top-20 → top-5) |
| 7 | Rich TUI, `convmem ask`, `convmem open`, Continue `cn --fork` |
| **8** | **Domains, observations, verify** — see below |

**Live corpus (approx.):** ~86 files indexed, ~193 chunks, **~1470 knowledge units** (mostly **untagged** — no `domain`/`author_model` until Step 8 ingests).

---

## Step 8 — what Sonnet built, what Cursor merged

**No separate Sonnet repo.** Step 8 was built from the earlier Claude tarball in a sandbox, then merged by Cursor into `~/Projects/convmem/`. All six live smoke tests passed.

### New modules

| File | Role |
|------|------|
| `domains.py` | Dotted taxonomy (`web_stack.security`, `coding.backend`, …), hierarchical match |
| `observe.py` | Direct JSON/JSONL ingestion → `knowledge_units` (no LLM) |
| `verify.py` | `verify_unit(id, verifier_model, confidence)` — chains confidence forward |

### New CLI

```bash
convmem add --title "…" --summary "…" --keyword a --keyword b --keyword c \
  --domain web_stack.security --author wp-sec-agent

convmem add --file observations.jsonl

convmem verify UNIT_ID --model kiro-review --confidence 0.9

convmem "query" --domain web_stack.security
convmem ask "what CSP fixes did we find?" --domain web_stack.security
```

### Critical integration fix (Cursor)

`--domain general` was matching **all** legacy units (missing domain → normalized to `general`). **Fixed:** untagged units are excluded from `--domain` filters; they still appear in plain search/ask.

### DISTILL_PROMPT change

Sonnet added optional `domain` field to distillation. Original prompt was "locked" — flagged exception; new chat ingests get domains automatically.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Chat logs   │────▶│ ingest.py    │────▶│ knowledge_units │
│ (Cursor,    │     │ + distill    │     │ (+ summaries)   │
│  Kiro, …)   │     └──────────────┘     └────────┬────────┘
└─────────────┘                                    │
┌─────────────┐     ┌──────────────┐               │
│ Tools       │────▶│ observe.py   │───────────────┤
│ (wp-sec,    │     │ add / JSONL  │               ▼
│  Lighthouse,│     └──────────────┘     ┌─────────────────┐
│  OpenClaw)  │                          │ ChromaDB + query  │
└─────────────┘                          │ ask / verify      │
                                         └─────────────────┘
```

---

## Your mission: inter-agent **product layer** (beyond memory)

Memory (Steps 1–8) works. The gap is **workflow**: who emits what, when, and how the next agent consumes it.

### Workflow #1 (recommended first)

```
Kiro reviews Lighthouse CI / security report
        │
        ▼
Writes observations.jsonl  (or reviews wp-sec-agent output)
        │
        ▼
convmem add --file observations.jsonl
        │
        ▼
Cursor: convmem ask "CSP fixes for staging" --domain web_stack.security
        │
        ▼
Cursor implements in repo (willowyhollow-dev, theme, mu-plugins)
        │
        ▼
Cursor session → convmem index (chat distillation, automatic)
        │
        ▼
Kiro: convmem verify <unit_id> --model kiro-review --confidence 0.95
```

**Loop closes:** tool findings → memory → implementation → chat → memory → verification.

### Who writes observations?

| Writer | When | `author_model` example | Typical `domain` |
|--------|------|------------------------|------------------|
| **wp-sec-agent** | After nikto/nuclei scan | `wp-sec-agent` | `web_stack.security` |
| **Lighthouse CI** | CI job parses report JSON | `lighthouse-ci` | `web_stack.performance` |
| **OpenClaw / browser probes** | Runtime checks (checkout, forms) | `openclaw` | `web_stack.wordpress` |
| **Kiro** | Review pass, human-readable synthesis | `kiro-review` | any |
| **Any agent** | Explicit structured finding | agent name | match taxonomy |
| **Chat distillation** | Automatic on `convmem index` | `distill_model` from config | model-assigned |

**Rule:** Observations require explicit `author_model`. Chat distillation sets it from `distill_model`. Kiro should **verify**, not duplicate — use `convmem verify` after Cursor ships a fix.

### Who does NOT write observations?

- Raw chat (use `convmem index` — distillation path)
- Unstructured paste into Kiro (distill manually or structure first)

---

## First webdev targets (user's stack)

| Site | Role | Repo / path |
|------|------|-------------|
| **willowyhollow.com** | Production WordPress | `~/GitClones/willowyhollow-dev` |
| **staging2.willowyhollow.com** | Staging | same repo, deploy target |
| **pavlomassage.com** | Client site | wp-sec-agent `clients/pavlomassage.com/` |
| **wordpress.org** | Scan test target only | not owned |

**Default first target for observer wiring:** `staging2.willowyhollow.com` + `willowyhollow-dev` repo.

Lighthouse CI already mentioned in corpus (Open WebUI chat) — connect CI output → `observations.jsonl` → `convmem add --file`.

---

## Observation schema (canonical)

See `observe.py` docstring and `examples/observations-lighthouse-security.jsonl`.

Required: `title`, `summary`, `keywords` (≥3), `author_model`  
Recommended: `domain`, `type`, `confidence`, `source_path`, `timestamp`

```json
{
  "title": "Missing Content-Security-Policy header",
  "summary": "Lighthouse and Nikto both report no CSP on staging2.willowyhollow.com. Add via SG Optimizer or server headers before production deploy.",
  "keywords": ["csp", "lighthouse", "nikto", "security-headers", "staging"],
  "type": "observation",
  "domain": "web_stack.security",
  "author_model": "wp-sec-agent",
  "confidence": 0.85,
  "tool": "observation",
  "source_path": "clients/staging2.willowyhollow.com/results/report.md",
  "timestamp": "2026-06-17T12:00:00"
}
```

---

## Domain taxonomy (bootstrap)

```
general
coding.frontend | coding.backend | coding.devops | coding.ml | coding.tooling
web_stack.wordpress | .plugins | .themes
web_stack.hosting | .dns | .ssl | .security | .js_runtime | .api | .performance | .seo
```

Hierarchical: `--domain web_stack.wordpress` matches `web_stack.wordpress.plugins` too.

---

## Setup (fresh machine)

```bash
mamba create -n convmem python=3.12
mamba activate convmem
pip install -r requirements.txt

mkdir -p ~/.config/convmem ~/.local/share/convmem
cp config.example.toml ~/.config/convmem/config.toml
# Optional: ~/.config/convmem/env.local with DEEPSEEK_API_KEY

python inventory.py
python convmem.py index          # first run: long
python convmem.py stats
```

Requires: Ollama (`nomic-embed-text`), CUDA for rerank, optional DeepSeek for distill.

---

## What ChatGPT should help design (not re-build)

1. **Observation emitters** — Lighthouse CI → JSONL, wp-sec-agent hook, OpenClaw probe format
2. **Agent conventions** — when Kiro writes JSONL vs when Cursor queries `ask --domain`
3. **Verification policy** — which units get `convmem verify` after deploy
4. **Cron / watch** — `convmem index` every 15–30 min + post-scan `add --file`
5. **Do not duplicate** — adapters, Chroma wrapper, distill prompt internals unless bugfix

---

## Related project: wp-sec-agent

```
~/Projects/wp-sec-agent/
  run.sh <site> [lite|standard|deep] [--force]
  clients/<site>/results/report.md
  clients/<site>/observations.jsonl   # ← wire this (see examples/)
```

After scan: `convmem add --file clients/<site>/observations.jsonl`

---

## Files in this archive

```
convmem/
  README-FOR-CHATGPT.md     ← you are here
  README.md                 ← technical reference (Steps 1–8)
  examples/
    AGENTS-FLOW.md          ← one-page workflow
    observations-lighthouse-security.jsonl
    export_report_to_observations.py
  *.py, adapters/, config.example.toml, requirements.txt
```

---

## Quick validation

```bash
python convmem.py stats
python -m unittest discover -s tests -v

# Evidence ledger
python convmem.py add --file examples/observations.jsonl
python convmem.py related obs001

# Ask (DeepSeek v4)
source ~/.config/convmem/env.local
python convmem.py ask "CSP staging fixes" --domain web_stack.security
python convmem.py ask "What remains unresolved?" --domain web_stack.security --evidence
```

See **README.md** → *Testing guide (for DeepSeek v4)* for the full QA checklist.

---

## Milestones status (2026-06)

| Milestone | Status |
|-----------|--------|
| A — Evidence ledger | ✅ signed off |
| B — `convmem related` | ✅ signed off |
| C — Scanner ingest + `--upsert` | ✅ signed off |
| E — `ask --evidence` | ✅ implemented |
| D — OpenClaw probes | deferred |

Stable ledger ids: `obs_<site>_<producer>_<key>` via `ledger_ids.py`.  
Full CLI + test guide: **README.md**.
