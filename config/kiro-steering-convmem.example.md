---
inclusion: always
name: convmem
description: Session-start convmem protocol. Always run before repo survey, stack_ps, docker, git, or wp-cli.
---

# convmem — Local knowledge corpus

You have **shell** (`convmem` CLI) and **MCP** (`@convmem/brief`, etc.) on this machine.

**Before answering anything** (including `stack_ps`, docker, git, wp-cli, or directory listing):


1. **`convmem doctor`** — the only tool call in the first batch. Wait for exit 0 before
calling anything else.
2. **`convmem brief --stdout-only`** — session orientation: corpus state, recent decisions, monitor results, unresolved count.
3. **`convmem unresolved`** — check open observations. Add `--site <hostname>` for client-specific issues (e.g. `--site staging2.willowyhollow.com`). For multiple sites, prefer **separate** `convmem unresolved --site …` calls (or one call without `--site`). Avoid `echo` separators unless comparing output side-by-side.
4. **Before answering history/architecture questions:** use `convmem "search query"` or `convmem ask "question"` to ground responses in the ledger.

**Branching (convmem prod — Always-Available GitHub Fallback):** After doctor/brief/unresolved, when cwd is `~/Projects/convmem`, run `git branch --show-current`. **Do not edit tracked files on `main`** (no single-file typo exception). Before the first tracked-file edit: `convmem work start <feat|fix|docs|plan|wip> <slug>` (or resume with `convmem work resume <branch>`). Taxonomy `feat|fix|docs|plan|wip/YYYY-MM-DD-slug` — validate before switch. Push with an **explicit** refspec (`git push -u origin "$branch:refs/heads/$branch"`); never `git push -u origin HEAD`. **Push immediately after every commit** — the remote branch is the fallback. Graduate `wip/` with `git branch -m` before review — never merge `wip/` directly. Pre-commit/pre-push reject work on `main`; local `CONVMEM_SKIP_MAIN_HOOK` is hook-skip/audit only (not GitHub authz; never in agent instructions). Agents never merge, force-push, or push `main` — Ryan owns merges (PR required when GitHub protection allows). **Single active writer:** use `--worktree` if contested; do not switch a shared checkout under another agent. Handoff: branch name + `git log origin/main..HEAD --oneline` + push status. Full rules: `docs/plans/ARCHITECTURE-always-github-fallback.md`.

**Push immediately after commit.** Do not wait for Ryan to say "push." The remote branch IS the backup — unpushed work is unrecoverable. Use explicit `"$branch:refs/heads/$branch"` on first push. Commit often, push every commit.

**DB backups (WordPress repos).** Before any DB mutation (`eval-file`, direct SQL, sync scripts) — take a `practice_backup` or `mysqldump`. This is operational safety for content, separate from git.

**Git hygiene (convmem prod — Git Hygiene Baseline):** After cloning `~/Projects/convmem`, run `bash scripts/install-repo-config.sh` (sets `core.hooksPath`, `pull.ff only`, `rerere.enabled`, `blame.ignoreRevsFile` — repo-local only). Feature branch update: `git fetch origin && git rebase origin/main`. Clean `main`: `git pull --ff-only`. If plain `git pull` fails under `pull.ff only`, histories diverged — stop and inspect (do not force a merge pull). When rerere reuses a resolution, review with `git rerere diff` (textual reuse ≠ semantic correctness). Milestone closures: propose `vX.Y.Z-<slug>` or `milestone/<slug>` in handoff; Ryan tags; work from a tag via `git switch -c <branch> <tag>` (no fixed `recovery/` prefix). Stash: may stash **own** uncommitted work to unblock a branch switch; must **not** stash Ryan’s unrelated dirty files without execution-plan authorization (`git stash push -u -m "<reason>" -- <paths>` + handoff note if authorized). Full rules: `docs/plans/git-hygiene-baseline.md`.

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
| **Find a stopping point** / **good stopping point** / **let's wrap up** / **park it** | **Soft close** — stabilize work, push commits, verbal summary, Track A. **No record block.** See `SESSION-CLOSE-RECORD.md § Stopping point`. |
| **Closing** / **end session** / **record block** | **Hard close** — Track A + output `convmem record` block for Ryan to run. |

Avoid **"index what you wrote"** alone — models treat that as the markdown log, skip chat.

**Crush:** you are **Crush lane** even when running DeepSeek V4 weights. Say **Crush found it** — not "DeepSeek found it."

1. **Search first** — `convmem "topic"` / `ask` before re-deriving from scratch.
2. **`record`** — one closing **conclusion** only (not per-finding). Detail stays in chat ingest + indexed logs.


## After Tier A — MCP tools (do not repeat brief)


After Tier A in a project repo, use read-only MCP `search_fast()`, `ask()`, `related()`, or `stats()`. Do **not** repeat `brief()`. Non-project modes follow MCP gates.


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


## Kiro — handoff vs record (critical)

- Verification, read-only review, bug audit, or Ryan says **ingest your chat** → run `convmem index --file` on **this session's** `~/.kiro/sessions/.../messages.jsonl`. **Stop. No record block.**
- **Never volunteer** `convmem record` at task end — important work is already in chat ingest.
- `convmem record` **only** when Ryan says **record block**, **closing**, or **end session**.

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

## Bounded autonomy


Default for Routine-reversible work only in convmem. `Mode: review required` disables it; `Mode: bounded autonomy` opts in where higher rules permit. WordPress stays review-required pending separate probation. Other repos, architecture, security, and external-configuration work never inherit it.

Precedence (high→low): system/tool guards → lane must-nots + protocol → DB/secrets/external safety → exact brief authorizations → autonomy defaults. Lower cannot override higher.

Interrupt only for: security/privacy exposure; unauthorized external change; external cost/commitment; public API/schema change; out-of-lane action; ambiguous outcome. Else choose one path and continue.

Reuse existing DB-backup, lane, and record safeguards by reference.

External auth requires exact resource, operation, and final value (or named one-shot) in `Authorized external changes`; never infer from outcome.

Done: result, verification, largest material trade-off/risk, branch/push; Track A at handoff.


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

