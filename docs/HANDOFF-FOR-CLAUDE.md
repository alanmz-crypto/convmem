# Handoff for Claude — convmem & the evidence bus

**Purpose of this doc:** Give you enough context to brainstorm with the human about where this system could go next — especially evolving from *what happened* toward *how it works* and *why we chose it*.

**Date:** 2026-06-18  
**Status:** All milestones through **F2c** signed off. System running on dev machine (watch + refine + monitor). ~1,710 knowledge units in corpus.

---

## What this is (one paragraph)

**convmem** is a local-first **memory and evidence bus** for AI-assisted development. It ingests two very different streams into one searchable store (ChromaDB on disk):

1. **Chat history** from coding agents (Cursor, Kiro, Continue, Aider, Crush, Open WebUI) — distilled by LLM into reusable “knowledge units.”
2. **Tool observations** from security scanners (wp-sec-agent, Lighthouse, hourly HTTP monitor) — structured facts with stable IDs, no distillation.

You query it semicolon semantic search (`convmem "topic"`), RAG Q&A (`convmem ask`), or graph traversal (`convmem related obs_…`). It is **not** live agent-to-agent chat; it is **durable, citeable memory** that survives sessions and boots.

**Companion repo:** `wp-sec-agent` — WordPress security scanner that exports findings into convmem’s ledger format. First real site: `staging2.willowyhollow.com`.

**No cloud DB. No web app.** Config in `~/.config/convmem/config.toml`, data in `~/.local/share/convmem/`.

---

## Architecture (mental model)

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOURCES                                   │
├──────────────────────────┬──────────────────────────────────────┤
│  Chat logs (many tools)  │  Tools (wp-sec, Lighthouse, monitor) │
│  → parse → chunk         │  → Observation / Decision / Verif  │
│  → distill (LLM)         │  → stable ledger_id, relates_to    │
└────────────┬─────────────┴──────────────────┬───────────────────┘
             │                                 │
             ▼                                 ▼
      knowledge_units (Chroma)          same collection + graph edges
             │                                 │
             └─────────────┬───────────────────┘
                           ▼
              query / ask / related / verify
                           │
              refine daemon (dedupe, domain backfill, …)
              watch daemon (new files → index)
              monitor timer (HTTP probes → verifications)
```

**Persistence:** Chroma vectors + metadata; JSONL sidecars (`processed.json`, `knowledge_units.jsonl`, exchange records at ingest). **No graph database** — `relates_to` links are resolved in memory via `build_ledger_index()`.

---

## Two ingestion paths (important distinction)

### Path A — Chat distillation (fuzzy, rich, lossy)

- **Input:** Conversation chunks (60 messages, 10 overlap).
- **Process:** LLM extracts `{type, title, summary, keywords, confidence, domain}`.
- **Types:** `solution | decision | explanation | pattern` (plus `observation` when from ledger export).
- **Metadata kept:** `source_path`, `tool`, `timestamp`, `session_id`, `author_model`, chunk offsets.
- **Strength:** Captures tribal knowledge, workarounds, narrative.
- **Weakness:** No guaranteed structure for causality; “why” is implicit in summary prose; duplicates possible.

### Path B — Evidence ledger (structured, deterministic)

- **Input:** JSONL with `kind: observation | decision | verification`.
- **Stable IDs:** e.g. `obs_staging2_wpsec_csp-missing` (site + producer + audit key).
- **Graph:** `decision.relates_to → observation`, `verification.relates_to → observation`.
- **Fields:** `summary`, `domain`, `site`, `severity`, `evidence` dict, `author_model`, `confidence`, `result` (verifications).
- **Strength:** What / where / when for security findings; repeatable upsert; monitor can attach low-confidence verifications.
- **Weakness:** Only as good as producers; “why we chose fix X” is optional human/agent decision records, not automatic.

---

## What we track today vs the W5H ladder

The human wants to explore turning this into something that tracks:

| Dimension | Today (honest assessment) | Gap |
|-----------|---------------------------|-----|
| **What** | Strong for ledger obs (CSP missing, plugin vuln). Moderate for chat units (distilled summary). | Chat path conflates fact and opinion. |
| **Where** | `site`, `source_path`, `workspace_directory`, paths in summaries/keywords. | No normalized “resource URI” layer (host, path, file, env). |
| **When** | ISO timestamps on units; monitor runs hourly; `processed.json` for file versions. | No event timeline / “state as of T” model. |
| **How** | Partially in `summary`, `evidence` dict, chat `solution`/`pattern` types. | Not first-class: no procedure steps, command logs, or reproducible runbooks linked to obs. |
| **Why** | Rarely explicit. `decision` kind exists but underused. Distill prompt asks for reusable facts, not rationale chains. | **Hardest layer** — requires capturing intent, alternatives rejected, constraints. |

### Hypothesis for brainstorming

- **What / where / when** → extend **ledger + monitor + scanner** producers (structured, cheap, automatable).
- **How** → link procedures to observations (`evidence.commands`, runbook units, or `decision` + `relates_to` to step lists); possibly ingest shell history / Crush sessions as “how” evidence.
- **Why** → needs explicit **`decision` records with rationale**, or a new kind (e.g. `rationale` / `assumption`) and discipline from agents (Kiro writes these at sign-off). LLM distillation alone will hallucinate or omit why.

---

## Corpus snapshot (2026-06-18)

| Source | ~Units | Notes |
|--------|--------|-------|
| Cursor JSONL | ~1,215 | Primary agent history |
| Kiro | ~590 | SQLite conversations |
| Crush | ~228 | Just indexed (24 `.crush/crush.db` files) |
| Continue | ~221 | Session JSON |
| Open WebUI | ~181 | Large sqlite |
| wp-sec / monitor / Lighthouse | ~20+ | Ledger-linked security |

**Domains:** dotted taxonomy (`web_stack.security`, `coding.ml.*`, etc.) — filter with `--domain`.

**Always-on (dev machine):**

- `convmem watch` — new chat files → index
- `convmem refine` — dedupe, domain backfill, semantic dedupe queue
- `convmem monitor` — hourly HTTP probes on staging2 → verifications

**MiniPC:** cold standby (was canonical briefly; reverted).

---

## Agent roles (how humans use multiple AIs)

| Agent | Role |
|-------|------|
| **Cursor** | Read/plan; does not write ledger |
| **Builder** | Implements code |
| **Kiro** | Review, sign-off, writes verifications/decisions |
| **Claude (you)** | Brainstorm, architecture, greenfield ideas |
| **DeepSeek** | Distillation + `convmem ask` synthesis |

Exchange format is designed so **observers** (tools, monitor) append facts and **reviewers** (Kiro) append verifications without overwriting each other’s authority.

---

## Signed-off milestones (don’t re-litigate)

| Milestone | Capability |
|-----------|------------|
| A | Ledger contract (`Observation`, `Decision`, `Verification`) |
| B | `convmem related` graph |
| C | Scanner upsert + stable ids |
| E | `ask --evidence` (prefers unresolved/failed) |
| F0 | `watch` |
| F1 | `refine` job queue |
| F2a | Store API + citation dedupe |
| F2b | HTTP monitor on staging2 |
| F2c | Crush adapter |

---

## Deferred / not started (fair game for ideas)

| Item | Notes |
|------|-------|
| **Milestone D — OpenClaw probes** | More security observers |
| **Cursor `store.db` adapter** | 6 Composer DBs; needs tree-walk POC |
| **`recency_weight` in query** | Config stub exists |
| **Semantic dedupe LLM verdict** | Pairs queued; no auto-merge |
| **`domain_drift_detect` (v1.1)** | Monthly mis-tag spot-check |
| **Physical `--prune` of tombstones** | Needs explicit policy |

---

## Key files (if you need to reason about implementation)

| Path | Role |
|------|------|
| `~/Projects/convmem/README.md` | Operator docs |
| `ledger.py` | Observation / Decision / Verification schema |
| `distill.py` | Chat → knowledge unit prompt |
| `evidence.py` | Unresolved-first reranking |
| `monitor.py` | HTTP probe → verification |
| `docs/MILESTONE-F.md` | Refine/watch policy |
| `docs/F2b-MONITOR-POLICY.md` | Monitor authority rules |
| `~/Projects/wp-sec-agent/` | Scanner that feeds ledger |

---

## Example ledger chain (what / where / partial how)

```json
{"id":"obs_staging2_wpsec_csp-missing","kind":"observation","site":"staging2.willowyhollow.com","summary":"Content-Security-Policy header absent","severity":"high","domain":"web_stack.security"}
{"id":"dec_staging2_csp_nginx","kind":"decision","relates_to":"obs_staging2_wpsec_csp-missing","summary":"Add CSP via nginx config snippet X","author_model":"kiro-review"}
{"id":"ver_staging2_csp_monitor","kind":"verification","relates_to":"obs_staging2_wpsec_csp-missing","result":"fail","confidence":0.4,"author_model":"convmem-monitor","summary":"CSP header still absent"}
```

What’s missing for full W5H: **why nginx over plugin**, **how to apply snippet**, **what changed between scans**.

---

## Questions for Claude to explore with the human

1. **Schema:** Should `why` be a new ledger kind, extra fields on `decision` (`rationale`, `alternatives_rejected`, `constraints`), or a separate “argument graph”?
2. **How vs chat:** Should procedures be first-class units (type `procedure` with steps) or always anchored to an `observation` via `relates_to`?
3. **Automation boundary:** What can monitors/scanners prove vs what must stay human/Kiro-signed?
4. **Timeline:** Do we need an event log (state transitions) or is upsert + verification history enough?
5. **Query UX:** How should `convmem ask` behave when user asks “why did we…?” — retrieve decisions only, or synthesize (risky)?
6. **Crush / terminal sessions:** 228 new units — are these “how” gold mines if parsed for commands and outcomes?
7. **Minimal next build:** One thin slice that proves W→H→Y (e.g. wp-sec finding → decision with rationale → linked runbook)?

---

## Constraints to respect

- Local-first; no mandatory cloud DB.
- **Single writer** to Chroma (one host owns corpus).
- Kiro verifications are **authoritative** — monitor never supersedes.
- Distillation is **lossy** — don’t rely on it alone for audit trail.
- Privacy: corpus contains real conversations; treat `~/.local/share/convmem/` as sensitive.

---

## Starter prompt for the human → Claude

> We built convmem (see HANDOFF-FOR-CLAUDE.md). It tracks AI chat knowledge and security observations in one searchable corpus. I want to evolve it so it reliably captures **what / where / when** (mostly there for tools), **how** (procedures, commands — partial), and **why** (decisions and rationale — weak). What architectures, schemas, or workflows have you seen that bridge operational facts to explicit reasoning without becoming a maintenance burden? What would you prototype first?

---

*Generated for cross-model brainstorming. Not a spec — ideas welcome.*
