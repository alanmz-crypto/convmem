---
inclusion: always
name: convmem
description: Session-start convmem protocol. Always run before repo survey, stack_ps, docker, git, or wp-cli.
---

# convmem — Local knowledge corpus

You have **shell** (`convmem` CLI) and **MCP** (`@convmem/brief`, etc.) on this machine.

**Before answering anything** (including `stack_ps`, docker, git, wp-cli, or directory listing):


1. **`convmem doctor`** — run first. Must exit 0 before any ask/search. Confirms Ollama/Chroma health.
2. **`convmem brief --stdout-only`** — session orientation: corpus state, recent decisions, monitor results, unresolved count. When also calling MCP **`brief()`**, pass **project=<slug>** inferred from cwd (see Tier B).
3. **`convmem unresolved`** — check open observations. Add `--site <hostname>` for client-specific issues (e.g. `--site staging2.willowyhollow.com`). For multiple sites, prefer **separate** `convmem unresolved --site …` calls (or one call without `--site`). Avoid `echo` separators unless comparing output side-by-side.
4. **Before answering history/architecture questions:** use `convmem "search query"` or `convmem ask "question"` to ground responses in the ledger.

**Cursor with shell:** run `convmem doctor` before MCP `brief()` — doctor confirms infra; brief does not.

**Codex-specific:** if `convmem ask` fails with a network error (sandbox blocks localhost), retry with:
```
bash -lc 'convmem ask "your question here"'
```
The `-l` flag sources `~/.zshrc`/`~/.bashrc` where Ollama's PATH is set. For permanent access in the convmem repo: `cp .codex/config.toml.example .codex/config.toml` to enable `network_access = true`.


## MCP (after shell ritual, or use MCP first if no shell step yet)


1. **`brief()` first** every session. Pass `project=<repo-slug>` to focus one repo (e.g. `pavlomassage-dev`, `willowyhollow-practice`, `convmem`). **If omitted:** infer from workspace — git repo basename, parent dir name, or tags in README/AGENTS.md; do not substitute a unrelated slug (e.g. do not use `willowyhollow-dev` when cwd is `pavlomassage-practice`).
2. **Check `unresolved_count`** in the brief response. If >0 and working on a client site, surface open issues before proceeding.
3. **Before answering history/architecture questions:** call `search_fast()` then `ask()` with citations.
4. **`related()`** walks the evidence chain for any ledger id (`dec_prop_…` or `obs_…`).
5. **If `ask()` fails with network error** (Codex sandbox): retry via `bash -lc 'convmem ask "..."'`.

**Read-only via MCP.** No propose_decision, add, index, or verify on MCP — durable writes are CLI `convmem record` + `--approve-last` only, run by Ryan.

Prefer **`brief()` tool** for session start. If the client uses `resources/read`, **`memories://brief`** or **`memory://brief`** is available (same payload). Do not invent other memory URIs.


## Session close


**Do not record session-start orientation alone** (`doctor` / `brief` / `unresolved` with no substantive work). That ritual is read-only context — not ledger-worthy unless Ryan says **closing**, **record block**, or you finished a decision/fix worth preserving.

**Never ask Ryan** what `convmem record` should capture — you already know the format. Look up `--relates-to` via `search_fast` / `convmem search` if needed; fallback for unrelated new work: `dec_prop_20260623_161428_c311`.

When Ryan closes or asks for a record block:

- Read `docs/inter-model/SESSION-CLOSE-RECORD.md`.
- `--relates-to` must be a real ledger id (`dec_prop_…` or `obs_…` from search_fast/ask/related).
- **Never** use topic slugs (`system-maintenance`), omit `--relates-to`, or use fake ids.
- Fallback for unrelated new work: `dec_prop_20260623_161428_c311`.
- Output a copy-paste shell block:

```bash
convmem record \
--relates-to <ledger_id> \
--summary "<one sentence>" \
--rationale "<why this decision>" \
--author <model-name>
convmem record --approve-last
```

Do not run convmem record -i directly — Ryan runs CLI commands. **Kiro:** add `--signer kiro-review` on `--approve-last` when signing durable facts.

