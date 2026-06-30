# Continue + convmem verification checklist

**Updated:** 2026-06-29 (Phase 1 **CLOSED**; Phase 2 = `cn --auto` policy doc)

## Phase gates vs grader `GRADE:`

The grader runs **all** checks in one pass. Use the right line for each phase:

| Phase | Gate criterion | Grader line to read |
|-------|----------------|---------------------|
| **1** — workspace_local strict smokes | `alien_ritual PASS` | Ignore top-level `GRADE: FAIL` if only `brief_answer` failed |
| **2** — `cn --auto` policy | `alien_ritual` + answer quality (v5 no corpus bleed) | PARTIAL acceptable if documented |
| **4** — named-tool matrix | `brief` / `search_fast` / `ask` rows + `brief_answer` | Full `GRADE:` applies |

Phase 1 **does not** require `brief_answer`, `search_fast`, or `ask` rows in the same session.

## Bounded transcript path (strict smokes with timeout)

The `CONVMEM_CONTINUE_TIMEOUT` env var adds a timeout + full transcript log:

```bash
CONVMEM_CONTINUE_TIMEOUT=180 \
  ~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/Documents
```

- Prints transcript path to stderr (e.g. `/tmp/convmem-continue.*.log`)
- Use **120–180s** minimum (8s too short — captures only startup rules, no tool calls)
- After session, grep transcript for tool order:
  ```bash
  rg -n 'folder_state|search_fast|brief|List|Read|Bash|Search|CheckBackground' \
    /tmp/convmem-continue.*.log | head -40
  ```
- **PASS** = `folder_state` or `brief` appears **before** any `List`/`Read`/generic `Bash`/`Search`

### Environment requirement (real terminal)

**Environment requirement:** smokes must run from a real user terminal, not a Cursor agent shell. Cursor injects `CheckBackgroundJob` before model turns; the grader now scores these as **SKIP**, but the session tool order is unreliable. Use iTerm/Alacritty/foot or a tmux pane — not Cursor's integrated terminal when running under agent mode.

**Do not** run `cn-convmem-smoke.sh` from Cursor/Codex agent subprocess shells for graded Phase 1 smokes.

- **Valid:** interactive terminal on the miniPC (Ryan)
- **Invalid for Phase 1 grading:** Cursor Auto / Codex agent shell invocation of the smoke script
- Harness is fine (`--exclude Search` confirmed in transcript command line); execution environment is not

Set model before smokes (or `/model` inside `cn`):

```bash
jq '.cliSelectedModel = "qwen3-coder:30b"' \
  ~/.continue/index/globalContext.json > /tmp/gc.json && \
  mv /tmp/gc.json ~/.continue/index/globalContext.json
```

## v5 fixes (2026-06-29, qwen3-coder:30b)

The following qwen3-coder:30b open issues were addressed:

| Issue | Fix |
|-------|-----|
| `_debug_log` instrumentation left in `mcp_server.py` | **Removed** — debug-939529.log deleted, all call sites cleaned |
| Global `inventory.total`/`units`/`summaries` cited as folder-local stats | **Zeroed-out** on workspace_local — `units`/`summaries` popped, `inventory` set to 0, `services` stripped, `coordination` emptied |
| MCP instructions lack `filepath=` Read param quirk guidance | **Added** — workspace_local `ACTIVE SESSION` block now warns about `filepath=` not `path=` |
| MCP instructions lack XML tool text warning | **Added** — workspace_local block bans `<function=...>` as chat text |
| `cn-convmem-smoke.sh` timeout too short for qwen3-coder:30b | **Documented** — 120-180s minimum; `CONVMEM_CONTINUE_TIMEOUT=180` is the default recommendation |
| Continue `Search` turn-1 before convmem on strict smokes | **Fixed** — `--exclude Search` in `cn-workspace-convmem.sh` |

## What “pass” means

**CLI verify** (`verify-continue.sh`) only checks wiring — config, MCP imports, corpus hits.

**Alien-workspace soak** (global protocol): unprompted *"What's the current state of this project?"* in a repo without convmem hints — agent calls convmem (`brief` and/or shell `doctor`) before repo survey. See `SOAK-REPORT-2026-06-25.md` sessions #7, #10.

**Named-tool verify** requires the model to **call the named MCP tool** and answer from tool output. A correct answer obtained via `Read`, `Bash`, or codebase search is a **FAIL** (common with DeepSeek Reasoner after weak `ask`).

Grade a session after testing:

```bash
~/Projects/convmem/scripts/grade-continue-session.sh ~/.continue/sessions/<latest>.json
~/Projects/convmem/scripts/grade-continue-session.sh --at '2026-06-25_14-30'
```

The grader checks named-tool discipline (`brief`, `search_fast`, `ask`) and **alien-workspace** ritual (first tool call should be MCP `brief` or terminal `convmem doctor`/`brief`).

## Trim `rules:` to session-close only (Ryan manual)

Session-start lives in MCP `instructions=` (`config/agent-protocol-mcp.txt`). Remove the named-tool rule from `~/.continue/config.yaml` — keep session-close only.

**Template:** [config/continue-rules-session-close.example.yaml](../../config/continue-rules-session-close.example.yaml)

After trim, re-run `cn --auto` smoke with **qwen2.5-coder:14b** (daily) or **qwen3-coder:30b** (heavy) in an alien WP dir.

**Model blocks:** merge from [config/continue-models-tier-a.example.yaml](../../config/continue-models-tier-a.example.yaml) into `~/.continue/config.yaml`.

## CLI (automated)

```bash
~/Projects/convmem/scripts/verify-continue.sh
```

## continue-cli (primary soak path)

Ryan uses **`cn` (continue-cli)**, not the VS Code extension. There is no Chat/Plan/Agent mode dropdown.

**Agent mode in CLI:**

```bash
cd ~/WordPress/pavlomassage-practice   # or any alien dir
cn --auto --config ~/.continue/config.yaml
```

**Model selection:** `/model` in the CLI session, or set `cliSelectedModel` in `~/.continue/index/globalContext.json`. Headless soak: single-model temp config + `cn --auto -p` (see soak rows #19–22).

### Tier-A local models (2026-06-29)

| Tier | Model | VRAM | Roles | Alien soak | Notes |
|------|-------|------|-------|------------|-------|
| **Daily** | **qwen2.5-coder:14b** | ~9 GB | chat, edit, apply | **FAIL** (#19) | Config added; emitted tool JSON as text — not native tool call |
| **Heavy coding** | **qwen3-coder:30b** | ~18 GB | chat, edit, apply | **PASS** (#10, #15, #17, #20) | Proven for convmem; use when 14b fails or task is hard |
| **Planning** | **qwen3.6-27b-iq3-32k** | ~11 GB | chat | **FAIL** (#21) | First tool `List` — repo survey before brief |
| **Planning** | **qwen3.6-27b-iq3-crush** | ~11 GB | chat | **FAIL** (#22) | Same as iq3-32k |
| Legacy | qwen3.6:35b, qwen3.6:27b, unsloth-32k | 14–23 GB | chat | unsloth-32k **PASS** (headless 2026-06-29) | Kept in picker; prefer iq3 on 12GB for size |
| Cloud | DeepSeek V4 Flash | — | chat, edit | FAIL (#5) / PARTIAL (#7) | `cn` warns: limited tool calling |
| Cloud | DeepSeek V4 Pro | — | chat, edit | untested | likely better than V4 Flash |

**Recommendation:** Default `cn --auto` to **qwen3-coder:30b** until **qwen2.5-coder:14b** passes alien soak. iq3 variants are lighter but skip convmem ritual in headless soak — retry interactively before demoting 30b.

**Alien soak prompt** (no convmem hints):

> What's the current state of this project?

**Pass:** MCP `brief()` or shell `convmem doctor` before `stack_ps` / docker / repo reads.

**Session file:** `~/.continue/sessions/<uuid>.json` — newest:

```bash
ls -t ~/.continue/sessions/*.json | head -1
```

**Config:** `~/.continue/config.yaml` — `schema: v1`, `mcpServers` block, session-close rules. Session-start protocol lives in MCP `instructions=` (no duplicate stanza in `rules:`).

## Continue IDE extension (optional)

**Quick start:** `~/Projects/convmem/scripts/continue-extension-soak.sh` (prompts + `grade-latest`).

Use a **new Agent chat** if testing the extension. **Models:** daily **qwen2.5-coder:14b**; heavy **qwen3-coder:30b**; override with `CONTINUE_MODEL=…` in [`continue-extension-soak.sh`](../../scripts/continue-extension-soak.sh).

### Open the right panel (not Cursor Agent)

Continue is a **separate sidebar** from Cursor’s built-in Agent/Composer chat.

1. Activity bar: click the **Continue** icon (hexagon), **or** `Ctrl+L` / `Ctrl+Shift+L` to focus Continue.
2. You should see Continue branding and your `config.yaml` models — not Cursor’s model picker.

If you only see Cursor’s chat, you’re in the wrong panel.

### Mode selector (Chat / Plan / Agent)

MCP loads only when tools are enabled — **Plan** or **Agent** mode ([Continue MCP docs](https://docs.continue.dev/customize/deep-dives/mcp)). **Plan is enough** for read-only convmem (`brief`, `search_fast`, `ask`).

**Where to look:** bottom-left of the **Continue** input box — a small clickable label (often shows `Chat`, `Plan`, or `Agent`). It is easy to miss; the panel may need to be wide enough to show it.

**Keyboard:** `Ctrl+.` cycles Chat → Plan → Agent (Linux/Windows).

**No dropdown at all?**

- Confirm you’re in **Continue**, not Cursor Agent and not terminal `cn`.
- Select **qwen2.5-coder:14b** (daily) or **qwen3-coder:30b** (heavy) as the chat model (⋯ → Models / cube icon above input).
- If Plan/Agent show **Not Supported**, add to that model in `config.yaml`:
  ```yaml
  capabilities:
    - tool_use
  ```
  Reload window after edits.
- Update Continue extension (you have **1.2.22** in `~/.vscode-oss/extensions/`).

**Sanity check:** In Plan or Agent mode, prompt: *Call MCP tool `brief` with `project="willowyhollow-dev"`* — you should see a tool call named `brief` in the transcript (not Bash `convmem brief`).

**Config:** `~/.continue/config.yaml` must include `schema: v1` and an `mcpServers` block (not JSON-only). Reload Continue after edits (`Developer: Reload Window` or restart the extension).

### 1. MCP connected

- Switch to **Agent** mode (not Chat)
- Confirm tool calls appear in the transcript (`brief`, `search_fast`, …) — there is often **no** Settings → MCP list
- **Fail:** model says it has no MCP tools, or only runs `convmem` in Bash

### 2. Brief

Prompt:

> Call MCP tool `brief` with `project="willowyhollow-dev"`. Reply with **only one sentence** that quotes `coordination.durable_writes` from the JSON. No other sections.

**Pass:** one sentence containing `record -i` and `record --approve-last`.

**Fail (seen):** called `brief` but dumped unrelated staging2/handoff sections (qwen3-coder:30b).

**Hallucination (seen, fixed 2026-06-29):** qwen3-coder:30b called `brief(project=…)` then invented Arch Linux / hardware facts from unrelated `recent_decisions`. Fixes: (1) `brief()` filters `recent_decisions`/`recent_monitor` when `project=` is set; (2) `chatOptions.baseAgentSystemMessage` on qwen3-coder:30b; (3) global evidence-grounding rule in `config.yaml`. Restart `cn` / reload Continue after MCP or config edits (`bash scripts/restart-convmem-mcp.sh` if IDE holds stale MCP).

**XML tool leak (seen, fixed 2026-06-29):** Model prints `<function=brief>…</function></tool_call>` as chat text — tool never runs. Cause: `provider: ollama` + Continue system-message-tool fallback. Fix: Tier-A models use `provider: openai` + `apiBase: http://localhost:11434/v1` + `apiKey: ollama` for native Ollama tool API. Also: `brief(project=)` must be cwd basename (not `convmem` when cwd is another repo).

**MCP `Not connected` (IDE extension only):** After `bash scripts/restart-convmem-mcp.sh`, the VS Code Continue sidebar may keep a dead MCP handle. **Fix:** reload window before smoke tests. **`cn --auto` spawns MCP fresh** — start a new CLI session after code updates; no IDE reload.

### CORE 8 system runbook smokes (Arch Linux)

`cd` to workspace, `cn --auto --config ~/.continue/config.yaml`, select **qwen3-coder:30b** (`/model`), ask state question. **Pass:** turn 1 is MCP `brief()` (JSON includes `brief_mode: system_runbook` on `/boot`, `/etc`, `/var`, systemd paths); then `search_fast` with subject terms. **Fail:** List/Read only with no brief.

| # | Workspace | Prompt |
|---|-----------|--------|
| 1 | `~/Projects/ComfyUIimprov` | What's the current state of this project? |
| 2 | `/boot/loader/entries` | What is the state of boot entries? |
| 3 | `/etc` | What is the state of my pacman configuration? |
| 4 | `~/Documents` | How's the cataloging of this directory? | brief → search_fast → README/corpus cites |
| 5 | `/home/linuxbrew` | What's the current state of this folder? | brief (workspace_local) before List |

**Recent smokes (2026-06-29, qwen3-coder:30b):**

| Session | cwd | Mode | Ritual | Notes |
|---------|-----|------|--------|-------|
| `13bf8547` | `~/Documents` | strict + 180s timeout | **PASS** | **Phase 1 gate closed** — turn 1 `folder_state`, v5 stats-zeroing, Search excluded (real run; agent rerun contaminated other cwds) |
| `77a57494` | `/home/linuxbrew` | strict script | **PASS** | turn 1 `folder_state()` (interactive baseline) |
| `62c9a903` | `~/Projects/convem` | `cn --auto` | **PASS** | `brief(project=convem)` turn 1 |
| `cbf6e0b3` | `~/Projects/ponytail` | `cn --auto` | **PASS** | `brief()` → search_fast → ask |
| `725e9e78` | `/home/linuxbrew` | `cn --auto` | **FAIL** | List-first; no MCP |
| `5a5e6f0e` | `~/WordPress/scripts` | `cn --auto` | **PARTIAL** | Bash turn 1; turn 2 `folder_state()` |
| `e46bb58d` | `~/Documents` | `cn --auto` | **FAIL** | Bash turn 1; pre-v5 |

**Phase 1 gate — CLOSED (2026-06-29):**

| cwd | Verdict | Session | Basis |
|-----|---------|---------|-------|
| `~/Documents` | **PASS** | `13bf8547` | Turn 1 `folder_state`, v5 stats-zeroing, Search excluded |
| `/home/linuxbrew` | **PASS** | `77a57494` | Interactive strict baseline, grader-confirmed |
| `~/WordPress/scripts` | **Optional** | — | No strict-script session; not blocking |

**Policy:**

- **Graded workspace_local:** use **`cn-convmem-smoke.sh`** / `cn-workspace-convmem.sh` (no `--auto`; `--exclude Search`). qwen3-coder:30b proven at this bar.
- **`cn --auto` on alien cwds:** **PARTIAL-acceptable** (documented structural limit — `--auto` ignores `--exclude`). Real failure mode: Bash-first, convmem turn 2+ (`e46bb58d`). v5 stats-zeroing improves turn-2+ answers (no global corpus bleed). Known limitation, not a blocker.

**Phase 2 (optional):** document `cn --auto` PARTIAL behavior with answer-quality notes; not blocking.

**v3 fix (2026-06-29):** cwd-aware MCP `instructions=` + `folder_state()` tool (prompt-matched alias for `brief()` on workspace_local paths). Retry `/home/linuxbrew` after MCP restart.

**v4 enforceable soak:** `cn --auto` ignores `--exclude`. Use **`cn-convmem-smoke.sh`** (all folder-state smokes):

```bash
~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/Documents
~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/WordPress/scripts
~/Projects/convmem/scripts/cn-convmem-smoke.sh /home/linuxbrew
```

(no `--auto`; List/Read/Bash/**Search** blocked except `Bash(convmem*)`; run from **real terminal** — see bounded transcript section)

**Pattern:** `cn --auto` → Bash-first PARTIAL on workspace paths; strict script → PASS when turn 1 is `folder_state()`.


Prompt:

> Call MCP tool `search_fast` only (no Read, no Bash) for `practice-local willowyhollow-practice 8081`. Cite top `ledger_id`.

**Pass:** tool call `search_fast` → cites `dec_prop_20260623_203527_c4dd`.

### 4. Ask (or search_fast fallback)

**Prerequisite:** ledger fact for reset exists (`dec_prop_*` “re-run restore-from-backup.sh” chained to `c4dd`).

Prompt:

> Call MCP tool `ask` only: "How do I reset the willowyhollow practice stack?" with `site=practice-local`. If `ask` is weak, say so — do **not** Read files under ~/WordPress.

**Pass:** `ask` tool called; answer mentions `restore-from-backup.sh` from citations.

**Fail (seen):** `ask` returned weak answer → model used `Read` on `willowyhollow-practice/README.md` (correct answer, wrong channel).

### 5. Continue history → convmem

In the same chat, say something unique, e.g.:

> Continue verify marker: purple-elephant-8081

Wait 2 minutes (watch debounce), then in terminal:

```bash
convmem search "purple-elephant-8081"
```

**Pass:** hit points at `~/.continue/sessions/*.json`.

## Not in scope (by design)

- MCP `record` / writes — terminal only (`convmem record --approve-last`)
- CLI session recording — use `record -i` for curated facts

## After pass

```bash
convmem record -i   # summary: Continue MCP verified YYYY-MM-DD
convmem record --approve-last
```
