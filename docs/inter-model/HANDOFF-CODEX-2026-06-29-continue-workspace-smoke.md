# Codex handoff — Continue CLI workspace folder-state smokes

**Date:** 2026-06-29  
**From:** Cursor Auto (debug session `939529`)  
**To:** Codex (Tier A: shell + MCP)  
**Surface:** **continue-cli only** (`cn`) — Ryan does **not** use VS Code/Cursor Continue extension for these smokes  
**Goal:** Fix / verify qwen3-coder:30b folder-state ritual on **workspace_local** cwds (`~/Documents`, `/home/linuxbrew`, `~/Pictures`) and keep **PASS** on `~/Projects/*` / `~/WordPress/*` under `cn --auto`

---

## Problem statement

Ryan prompts: *"What is the current state of this folder?"* (or cataloging variant) from alien cwds. **Pass** = turn 1 calls convmem MCP (`folder_state()` or `brief()`) before `List`/`Read`/`Bash`. **Fail** = model runs `pwd && ls -la` or `List` first and gives shallow answers from directory names alone.

Two failure classes observed:

1. **Hallucination** — global `brief()` returned full corpus; model summarized `convmem` instead of the cwd (`~/Documents`, session `c0cb171a`).
2. **Skipped convmem** — model never calls MCP; `List` or generic `Bash` first (`725e9e78`, `46e505d1`).
3. **Partial** — `cn --auto` allows `Bash` turn 1, then `folder_state` turn 2 (`e46bb58d`, `5a5e6f0e`).

---

## Root cause (proven)

| Finding | Evidence |
|---------|----------|
| `cn --auto` **ignores** `--exclude` | [Continue tool permissions docs](https://docs.continue.dev/cli/tool-permissions) — auto mode is `*: allow`; CLI flags and `permissions.yaml` do not apply |
| MCP payload fixes alone insufficient if model never calls MCP | `725e9e78` — zero MCP tools |
| `~/Projects/*` / `~/WordPress/*` infer project slug; model usually brief-first | `62c9a903`, `cbf6e0b3` PASS under `cn --auto` |
| workspace_local cwds need `brief_mode: workspace_local` | Empty `projects[]`, `workspace_hint`, strip global `recent_decisions` |

**Enforceable path:** run **`cn-convmem-smoke.sh`** (no `--auto`) — excludes `List`, `Read`, generic `Bash`; allows MCP + `Bash(convmem*)`.

---

## What shipped (2026-06-29, in repo + live config)

### `mcp_server.py`

- **`workspace_local` brief mode** — alien cwd (not `~/Projects|WordPress|GitClones`, not system runbook): filter `projects[]`, strip global noise, add `workspace_hint`, `workspace_local_note`, scoped `answer_from`.
- **`folder_state()` tool** — prompt-matched alias for `brief()` (“folder state / cataloging”).
- **Ignore `project=<basename>` on workspace_local** — prevents `folder_state(project=linuxbrew)` fake project scope.
- **Cwd-aware MCP `instructions=`** at spawn — `ACTIVE SESSION` block for workspace_local / system_runbook.
- **`search_fast` / `ask` / `stats` blocked until `brief()`** on workspace_local + system runbook (per MCP process).
- **`_search_fast_off_topic()`** — blocks Continue/Compose confabulation queries.
- **Debug instrumentation** — `_debug_log` → `.cursor/debug-939529.log` (NDJSON). **Remove after Codex confirms fix.**

### Scripts

| Script | Purpose |
|--------|---------|
| [`scripts/cn-convmem-smoke.sh`](../../scripts/cn-convmem-smoke.sh) | **Canonical** graded folder-state smokes (any cwd) |
| [`scripts/cn-workspace-convmem.sh`](../../scripts/cn-workspace-convmem.sh) | Implementation (exclude List/Read/Bash) |
| [`scripts/grade-continue-session.sh`](../../scripts/grade-continue-session.sh) | `alien_ritual` PASS / **PARTIAL** / FAIL; accepts `folder_state` |
| [`scripts/verify-continue.sh`](../../scripts/verify-continue.sh) | Wiring check; includes `folder_state` tool |
| [`scripts/restart-convmem-mcp.sh`](../../scripts/restart-convmem-mcp.sh) | Kill stale MCP; **cn spawns fresh** — no IDE reload |

### Live config (Ryan machine)

- **`~/.continue/config.yaml`** — qwen3-coder:30b `provider: openai` + Ollama `/v1` for native tools; rules + `baseAgentSystemMessage` for brief-first / `folder_state`.
- **Do not use VS Code extension** for verification.

### Tests

- [`tests/test_mcp_site.py`](../../tests/test_mcp_site.py) — 15 tests (workspace_local, folder_state, linuxbrew instructions, slug ignore).

### Docs

- [`docs/inter-model/CONTINUE-VERIFY.md`](CONTINUE-VERIFY.md) — smoke table, CORE 8 rows, strict-script instructions.

---

## Session evidence table

| Session | cwd | Command style | Turn 1 | Verdict |
|---------|-----|---------------|--------|---------|
| `c0cb171a` | `~/Documents` | `cn --auto` | `brief` → hallucinated convmem | **FAIL** (pre-fix) |
| `725e9e78` | `/home/linuxbrew` | `cn --auto` | `List` | **FAIL** |
| `77a57494` | `/home/linuxbrew` | `cn-convmem-smoke.sh` | `folder_state` | **PASS** |
| `e46bb58d` | `~/Documents` | `cn --auto` | `Bash` → turn 2 `folder_state` | **PARTIAL** |
| `5a5e6f0e` | `~/WordPress/scripts` | `cn --auto` | `Bash` → turn 2 `folder_state` + deep search | **PARTIAL** |
| `62c9a903` | `~/Projects/convem` | `cn --auto` | `brief` | **PASS** |
| `cbf6e0b3` | `~/Projects/ponytail` | `cn --auto` | `brief` | **PASS** |

Grader:

```bash
~/Projects/convmem/scripts/grade-continue-session.sh ~/.continue/sessions/<uuid>.json
```

---

## What Codex should do first

### 1. Tier A ritual (this repo)

```bash
convmem doctor
convmem brief --stdout-only
```

### 2. Restart MCP if `mcp_server.py` changed

```bash
bash ~/Projects/convmem/scripts/restart-convmem-mcp.sh
```

### 3. Strict smokes (interactive — headless `-p` hangs in automation)

```bash
~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/Documents
# prompt: What is the current state of this folder?

~/Projects/convmem/scripts/cn-convmem-smoke.sh /home/linuxbrew
~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/WordPress/scripts
```

Select **qwen3-coder:30b** via `/model` if needed.

**PASS criteria:** turn 1 = `folder_state()` or `brief()`; for Documents include `search_fast(workspace_hint.suggested_search_fast)` and cite `has_crush_db` / README — not global inventory as “this folder’s files”.

### 4. Regression under `cn --auto` (best-effort, expect PARTIAL on alien cwd)

```bash
cd ~/Projects/ponytail && cn --auto --config ~/.continue/config.yaml
```

Repo paths should stay **PASS** turn 1.

---

## Open problems (for Codex)

1. **`cn --auto` cannot enforce turn-1 convmem** on workspace_local — structural Continue limitation. Options: document only; or investigate Continue config/agents API for non-auto default with tool policy (no fix found yet).

2. **Headless `cn -p` hangs** in agent automation (~2–3 min, no session file). Use **interactive** smokes only; do not rely on `-p` for CI.

3. **XML tool leak** (session `e46bb58d` end) — `<function=folder_state>` as chat text. Tier-A uses `provider: openai` + Ollama `/v1`; if leak recurs, check Continue/Ollama tool-call format.

4. **Read tool param mismatch** — model uses `path=`; Continue expects `filepath=` (`e46bb58d`). Continue-side quirk; model may need rule or tool schema doc.

5. **Answer depth** — even with `folder_state`, model may cite global `inventory.total` as folder stats. `workspace_local_note` added; may need stronger brief trimming (hide global inventory on workspace_local).

6. **Remove debug instrumentation** in `mcp_server.py` after strict smokes PASS interactively for Documents + linuxbrew.

7. **CORE 8 system runbook smokes** still TODO under `cn --auto`: `/etc`, `/boot/loader/entries` — brief-first + `runbook_hint` (see CONTINUE-VERIFY.md).

---

## Key code paths

```
mcp_server.py
  _cwd_is_project_root()      → ~/Projects|WordPress|GitClones, .git, AGENTS.md
  _is_alien_workspace_cwd()   → workspace_local
  _resolve_brief_project()    → slug inference / ignore project= on workspace_local
  _trim_brief_for_workspace_local()
  _build_mcp_instructions()   → ACTIVE SESSION block at MCP spawn
  folder_state()              → wraps brief()
  _blocked_until_brief_json() → gates search_fast/ask/stats
```

Cwd for MCP subprocess = Continue workspace (`cn` sets it). Dynamic instructions use `os.getcwd()` at import.

---

## Protected paths

- **Tier 1:** `~/.local/share/convmem/` — no delete via agent shell  
- **Tier 2:** `~/.config/convmem/`  
- **Tier 3:** `~/Projects/convmem/` — edit freely  
- **`~/.continue/config.yaml`** — Ryan manual merge; agent may edit for Continue fixes (document in handoff)

---

## Record block (when closing)

```bash
convmem record \
  --relates-to dec_prop_20260623_161428_c311 \
  --summary "Continue workspace_local folder-state smokes: cn-convmem-smoke.sh PASS; cn --auto PARTIAL on Documents." \
  --rationale "Codex handoff 2026-06-29; workspace_local brief mode, folder_state tool, strict smoke script; cn --auto ignores exclude." \
  --author codex
convmem record --approve-last
```

(Ryan runs record — agent provides block only.)

---

## Related files

- [`CONTINUE-VERIFY.md`](CONTINUE-VERIFY.md)
- [`SOAK-REPORT-2026-06-25.md`](SOAK-REPORT-2026-06-25.md)
- [`VERIFICATION-MATRIX.md`](VERIFICATION-MATRIX.md)
- [`config/agent-protocol-mcp.txt`](../../config/agent-protocol-mcp.txt)
- Agent transcript: Cursor session `93952925-3831-41d9-9c66-45ce9f843fb0`
