# convmem — Local knowledge corpus protocol

convmem is a local-first knowledge corpus on this machine (1457+ units). It indexes AI chat transcripts, security observations, and decision records into ChromaDB (Ollama nomic-embed-text embeddings). CLI and MCP access. Read-only to agents by default.

**Do not ask "what is convmem" or suggest alternatives.** It exists on this machine. Use it.

---

## Tier A — shell-capable (Cursor, Codex, Kiro, Continue-with-Bash, Crush)

<!-- TIER_A_START -->

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

<!-- TIER_A_END -->

---

## Tier B — MCP-only (no shell, MCP connected)

<!-- TIER_B_START -->

1. **`brief()` first** every session. Pass `project=<repo-slug>` to focus one repo (e.g. `pavlomassage-dev`, `willowyhollow-practice`, `convmem`). **If omitted:** infer from workspace — git repo basename, parent dir name, or tags in README/AGENTS.md; do not substitute a unrelated slug (e.g. do not use `willowyhollow-dev` when cwd is `pavlomassage-practice`).
2. **Check `unresolved_count`** in the brief response. If >0 and working on a client site, surface open issues before proceeding.
3. **Before answering history/architecture questions:** call `search_fast()` then `ask()` with citations.
4. **`related()`** walks the evidence chain for any ledger id (`dec_prop_…` or `obs_…`).
5. **If `ask()` fails with network error** (Codex sandbox): retry via `bash -lc 'convmem ask "..."'`.

**Read-only via MCP.** No propose_decision, add, index, or verify on MCP — durable writes are CLI `convmem record` + `--approve-last` only, run by Ryan.

Prefer **`brief()` tool** for session start. If the client uses `resources/read`, **`memories://brief`** or **`memory://brief`** is available (same payload). Do not invent other memory URIs.

<!-- TIER_B_END -->

---

## Tier C — paste-only (ChatGPT webUI)

<!-- TIER_C_START -->

1. **Ask Ryan to run:** `convmem brief --stdout-only`
2. **Interpret the pasted output.** Cannot run CLI — do not pretend to call convmem.
3. **At session close:** suggest `convmem record` blocks using the format in SESSION-CLOSE-RECORD.md. Ryan will run them.

<!-- TIER_C_END -->

---

## Session close

<!-- SESSION_CLOSE_START -->

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

<!-- SESSION_CLOSE_END -->

---

## Read-only guard

Agents may search, ask, brief, and related freely. Do not run `convmem add`, `convmem index`, `convmem verify`, or any MCP write tool without explicit user direction. The evidence ledger is human-signed.

---

## Workflow routing (when unsure what to run)

<!-- WORKFLOW_ROUTING_START -->

**Cheat sheet:** `docs/MODEL-WORKFLOW.md` — read when lost.

| If cwd / task is… | Read first | Run |
|-------------------|------------|-----|
| Any session | — | `convmem doctor` → `brief` → `unresolved` |
| `~/Projects/convmem` + cross-project digest | `docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md` | `scripts/cross-project-digest.sh --skip-ask`; smoke: `scripts/smoke-cross-project-digest.sh` |
| `~/Projects/convmem` + architecture | `docs/builder-reference/README.md` | matching digest, then code |
| `~/Projects/convmem-lab` | `docs/lab-reference/NOTES.md` | `scripts/convmem-lab.sh doctor`; `lab/scripts/compile-synthesis-brief.sh`; `lab/scripts/smoke-synthesis.sh` |
| Session close / record | `docs/inter-model/SESSION-CLOSE-RECORD.md` | output `convmem record` block; Ryan approves |

**Split:** `lab-reference/` = lab gates & synthesis smoke (lab repo). `builder-reference/` = prod architecture. Never mix prod/lab data paths. Lab: no MCP registration. `--propose` on prod digest: Ryan-gated.

**Codex / DeepSeek:** verify shipped work via `docs/CODEX-DEEPSEEK-VERIFY.md` (independent checklist — do not trust chat claims alone).

<!-- WORKFLOW_ROUTING_END -->

---

## Tool lanes by model

See `docs/AGENT-ROLES.md` for per-model capability details (which tier each model operates under, Crush vs Cursor vs Codex distinctions).

---

## Recovery

See `docs/RECOVER.md`. The runtime corpus (ChromaDB, vector index) is outside Git. Project backup restores source code + MCP templates. To redeploy surfaces: `scripts/deploy-agent-protocol.sh`.
