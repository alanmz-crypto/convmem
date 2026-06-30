# convmem — Local knowledge corpus (shell + MCP)

convmem is a local-first knowledge corpus on this machine. You have **bash** and MCP read access.

**MANDATORY before repo survey, docker, git, `stack_ps`, or answering project-state questions:**


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


## MCP (after shell ritual — not optional)

After `doctor` + shell `brief` + `unresolved`: use `brief(project=<slug>)` — infer slug from cwd; `search_fast()`, `ask()`, `related()`, `stats()`. Read-only. Or `resources/read` on `memories://brief`.

**DeepSeek V4 (Flash/Pro) in Crush:** often skips this ritual on alien "project state" queries — do **not** start with `ls`, git, or docker until convmem steps above complete.

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

