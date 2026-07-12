# convmem — Local knowledge corpus (shell + MCP)

convmem is a local-first knowledge corpus on this machine. You have **bash** and MCP read access.

**MANDATORY before repo survey, docker, git, `stack_ps`, or answering project-state questions:**


1. **`convmem doctor`** — run first. Must exit 0 before any ask/search. Confirms Ollama/Chroma health.
2. **`convmem brief --stdout-only`** — session orientation: corpus state, recent decisions, monitor results, unresolved count. When also calling MCP **`brief()`**, pass **project=<slug>** inferred from cwd (see Tier B).
3. **`convmem unresolved`** — check open observations. Add `--site <hostname>` for client-specific issues (e.g. `--site staging2.willowyhollow.com`). For multiple sites, prefer **separate** `convmem unresolved --site …` calls (or one call without `--site`). Avoid `echo` separators unless comparing output side-by-side.
4. **Before answering history/architecture questions:** use `convmem "search query"` or `convmem ask "question"` to ground responses in the ledger.

**Branching (convmem prod only — Branching Safety Foundation):** After doctor/brief/unresolved, when cwd is `~/Projects/convmem`, run `git branch --show-current`. If on `main` and the task is multi-commit `feat`/`fix`/`docs`/`plan` work → create a branch **before the first commit** (`feat|fix|docs|plan|wip/<YYYY-MM-DD>-<slug>`). Single-file doc typos may stay on `main` (non-WIP subjects). Graduate `wip/` with `git branch -m wip/old feat/YYYY-MM-DD-slug` — never merge `wip/` directly. Push the branch; **do not merge or force-push `main`**. Pre-push rejects WIP-pattern subjects on `main` — if rejected, create/switch to a branch and push that. **Single active writer:** do not switch branches under another agent in the same checkout. Handoff: run `git branch --show-current`, then notify Ryan in session chat with branch name + `git log main..HEAD --oneline`. Full rules: `docs/plans/branching-strategy.md`.

**Git hygiene (convmem prod — Git Hygiene Baseline):** After cloning `~/Projects/convmem`, run `bash scripts/install-repo-config.sh` (sets `core.hooksPath`, `pull.ff only`, `rerere.enabled`, `blame.ignoreRevsFile` — repo-local only). Feature branch update: `git fetch origin && git rebase origin/main`. Clean `main`: `git pull --ff-only`. If plain `git pull` fails under `pull.ff only`, histories diverged — stop and inspect (do not force a merge pull). When rerere reuses a resolution, review with `git rerere diff` (textual reuse ≠ semantic correctness). Milestone closures: propose `vX.Y.Z-<slug>` or `milestone/<slug>` in handoff; Ryan tags; work from a tag via `git switch -c <branch> <tag>` (no fixed `recovery/` prefix). Stash: may stash **own** uncommitted work to unblock a branch switch; must **not** stash Ryan’s unrelated dirty files without execution-plan authorization (`git stash push -u -m "<reason>" -- <paths>` + handoff note if authorized). Full rules: `docs/plans/git-hygiene-baseline.md`.

**Cursor with shell:** run `convmem doctor` before MCP `brief()` — doctor confirms infra; brief does not.

**Codex-specific:** if `convmem ask` fails with a network error (sandbox blocks localhost), retry with:
```
bash -lc 'convmem ask "your question here"'
```
The `-l` flag sources `~/.zshrc`/`~/.bashrc` where Ollama's PATH is set. For permanent access in the convmem repo: `cp .codex/config.toml.example .codex/config.toml` to enable `network_access = true`.

**Session tracking (default — no hindsight test):** Assume **this conversation is worth tracking**. Two **separate** ingest targets — do **not** confuse them:

| Track | What it captures | When |
|-------|------------------|------|
| **A — Session chat** | What the model *said and did* in chat | **Every** substantive handoff |
| **B — Log artifact** | A `logs/*.md` file the model wrote | Only if such a file was created/updated |

Watch auto-indexes session files after debounce (~90s). Agents still **nudge both** before handoff so the next model is not waiting.

**A — Index your session chat (required at handoff):**

```bash
# Crush (willowyhollow-practice):
convmem index --file ~/WordPress/willowyhollow-practice/.crush/crush.db

# Kiro — this session's transcript (use latest sess_* under cwd or $HOME/.kiro/sessions):
convmem index --file ~/.kiro/sessions/<session-dir>/sess_<id>/messages.jsonl

# Cursor — agent transcript for this chat:
convmem index --file ~/.cursor/projects/<project>/agent-transcripts/<uuid>/<uuid>.jsonl

# Codex — full session (not history.jsonl prompts-only):
convmem index --file ~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-<timestamp>-<id>.jsonl
```

Indexing **only** a `logs/*.md` file does **not** ingest your chat. If you wrote a log, run **A and B**.

**B — Index log artifacts (if you wrote `logs/*.md`):**

```bash
bash ~/Projects/convmem/scripts/sync-willowyhollow-findings-index.sh   # findings log
bash ~/Projects/convmem/scripts/sync-willowyhollow-audit-index.sh      # Codex audit log
# one command for A+B (Crush + Kiro + Codex rollout + findings + audit):
bash ~/Projects/convmem/scripts/sync-willowyhollow-handoff.sh
```

**Ryan phrasebook:**

| Ryan says | Means |
|-----------|--------|
| **Ingest your chat** / **index your session** | Track **A** only |
| **Index the log** | Track **B** only |
| **Ingest everything** / **full handoff** | **A then B** (both if a log exists) |

Avoid **"index what you wrote"** alone — models treat that as the markdown log, skip chat.

**Crush:** you are **Crush lane** even when running DeepSeek V4 weights. Say **Crush found it** — not "DeepSeek found it."

1. **Search first** — `convmem "topic"` / `ask` before re-deriving from scratch.
2. **`record`** — one closing **conclusion** only (not per-finding). Detail stays in chat ingest + indexed logs.


## MCP (after shell ritual — not optional)

After `doctor` + shell `brief` + `unresolved`: use `brief(project=<slug>)` — infer slug from cwd; `search_fast()`, `ask()`, `related()`, `stats()`. Read-only. Or `resources/read` on `memories://brief`.

**DeepSeek V4 (Flash/Pro) in Crush:** often skips this ritual on alien "project state" queries — do **not** start with `ls`, git, or docker until convmem steps above complete.

## Session close


**Handoff is not a record.** Finishing a task, verifying bugs, switching models, or Ryan saying **ingest your chat** / **full handoff** → run **Track A** (`convmem index --file` session transcript). **Do not** output a `convmem record` block.

**Output `convmem record` only when Ryan literally says:** `record block`, `closing`, `end session`, or `record this`.

**Do not create markdown files** (`logs/*.md`, audit summaries, handoff docs) unless Ryan explicitly asked for a file or told you to append to an existing agreed log (e.g. findings log). To preserve work without a new file → **Track A** session index.

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


## Crush — handoff vs record

- You are **Crush lane**; never call yourself DeepSeek in handoff text (DeepSeek V4 is runtime weights only).
- Handoff / **ingest your chat** → `convmem index --file <project>/.crush/crush.db` (Track A). **No record block** unless Ryan asks.
- Do **not** create new markdown logs unless Ryan requested a file.

## HITL team charter (lane names — not model weights)

**Name agents by lane, never by runtime model.** Crush may run DeepSeek V4 weights — that is still **Crush lane** (Tier A shell). The **DeepSeek row** is the Tier B synthesis API behind `convmem ask` only — not a bug-hunter.

| Phase | Owner (lane) | Must not |
|-------|--------------|----------|
| Bug discovery | Crush | self-approve fixes; write `record`; merge to `main` |
| Independent audit | Codex | new `logs/*.md` unless Ryan asks; merge to `main` |
| Design / sign-off | Kiro | volunteer `record` at task end; merge to `main`; create `feat/`/`fix/` branches |
| Implementation (convmem) | Cursor | client WP in same session; merge to `main` |
| Implementation (client WP) | Cursor / Ryan | convmem ledger writes |
| Memory ingest | Whoever closes session | Track A **and** B — never one alone |
| Durable conclusions | Ryan only | per-finding records; agents never `--approve-last` |
| Merge to `main` | Ryan only | agents never merge or force-push `main` |
| Strategy review | ChatGPT / Claude Cloud | code edits; prod writes |
| Synthesis | DeepSeek API (`ask`) | primary bug author |

**Phrasebook:** ingest your chat = Track A · index the log = Track B · ingest everything = both · record block = Ryan runs approve-last.

**Handoff ≠ record.** Index session chat at handoff; `record --approve-last` only when Ryan says record block / closing.

**Tier 1 = shared memory bus** (not orchestration). Orchestration reserved for Tier 3 notify. Sprint checks: `docs/inter-model/BUG-SPRINT-SUCCESS-2026-07-06.md`.

Full charter + review rationale: `docs/inter-model/TEAM-CHARTER-2026-07-06.md`

## Workflow routing (when unsure)


**Cheat sheet:** `docs/MODEL-WORKFLOW.md` — read when lost.

| If cwd / task is… | Read first | Run |
|-------------------|------------|-----|
| Any session | — | `convmem doctor` → `brief` → `unresolved` |
| `~/Projects/convmem` + cross-project digest | `docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md` | `scripts/cross-project-digest.sh --skip-ask`; smoke: `scripts/smoke-cross-project-digest.sh` |
| `~/Projects/convmem` + architecture | `docs/builder-reference/README.md` | matching digest, then code |
| `~/Projects/convmem-lab` | `docs/lab-reference/NOTES.md` | `scripts/convmem-lab.sh doctor`; `lab/scripts/compile-synthesis-brief.sh`; `lab/scripts/smoke-synthesis.sh` |
| Session close / record | `docs/inter-model/SESSION-CLOSE-RECORD.md` | **Only if Ryan asks** — output `convmem record` block; else Track A index only |

**Split:** `lab-reference/` = lab gates & synthesis smoke (lab repo). `builder-reference/` = prod architecture. Never mix prod/lab data paths. Lab: no MCP registration. `--propose` on prod digest: Ryan-gated.

**Codex / DeepSeek:** verify shipped work via `docs/CODEX-DEEPSEEK-VERIFY.md` (independent checklist — do not trust chat claims alone).

