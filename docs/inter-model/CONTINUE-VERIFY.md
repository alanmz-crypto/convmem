# Continue + convmem verification checklist

**Updated:** 2026-06-23

## What “pass” means

**CLI verify** (`verify-continue.sh`) only checks wiring — config, MCP imports, corpus hits.

**UI verify** requires the model to **call the named MCP tool** and answer from tool output. A correct answer obtained via `Read`, `Bash`, or codebase search is a **FAIL** (common with DeepSeek Reasoner after weak `ask`).

Grade a session after testing:

```bash
~/Projects/convmem/scripts/grade-continue-session.sh ~/.continue/sessions/<latest>.json
```

## CLI (automated)

```bash
~/Projects/convmem/scripts/verify-continue.sh
```

## Continue UI (manual — required for “integrated”)

Use a **new Agent chat**. **Recommended model:** DeepSeek V4 Flash or DeepSeek V4 Flash (Think) for convmem MCP verify.

**Agent mode required** — MCP tools do not load in plain chat mode ([Continue MCP docs](https://docs.continue.dev/customize/deep-dives/mcp)).

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

### 3. Search practice facts

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
