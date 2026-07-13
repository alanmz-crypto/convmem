# convmem — Local knowledge corpus

You have access to a local knowledge corpus via convmem. Use it before repeating past work.


1. **`convmem doctor`** — run first. Must exit 0 before any ask/search. Confirms Ollama/Chroma health.
2. **`convmem brief --stdout-only`** — session orientation: corpus state, recent decisions, monitor results, unresolved count. When also calling MCP **`brief()`**, pass **project=<slug>** inferred from cwd (see Tier B).
3. **`convmem unresolved`** — check open observations. Add `--site <hostname>` for client-specific issues (e.g. `--site staging2.willowyhollow.com`). For multiple sites, prefer **separate** `convmem unresolved --site …` calls (or one call without `--site`). Avoid `echo` separators unless comparing output side-by-side.
4. **Before answering history/architecture questions:** use `convmem "search query"` or `convmem ask "question"` to ground responses in the ledger.

**Branching (convmem prod — Always-Available GitHub Fallback):** After doctor/brief/unresolved, when cwd is `~/Projects/convmem`, run `git branch --show-current`. **Do not edit tracked files on `main`** (no single-file typo exception). Before the first tracked-file edit: `convmem work start <feat|fix|docs|plan|wip> <slug>` (or resume with `convmem work resume <branch>`). Taxonomy `feat|fix|docs|plan|wip/YYYY-MM-DD-slug` — validate before switch. Push with an **explicit** refspec (`git push -u origin "$branch:refs/heads/$branch"`); never `git push -u origin HEAD`. **Push immediately after every commit** — the remote branch is the fallback. Graduate `wip/` with `git branch -m` before review — never merge `wip/` directly. Pre-commit/pre-push reject work on `main`; local `CONVMEM_SKIP_MAIN_HOOK` is hook-skip/audit only (not GitHub authz; never in agent instructions). Agents never merge, force-push, or push `main` — Ryan owns merges (PR required when GitHub protection allows). **Single active writer:** use `--worktree` if contested; do not switch a shared checkout under another agent. Handoff: branch name + `git log origin/main..HEAD --oneline` + push status. Full rules: `docs/plans/ARCHITECTURE-always-github-fallback.md`.

**Push immediately after commit.** Do not wait for Ryan to say "push." The remote branch IS the backup — unpushed work is unrecoverable. Use explicit `"$branch:refs/heads/$branch"` on first push. Commit often, push every commit.

**DB backups (WordPress repos).** Before any DB mutation (`eval-file`, direct SQL, sync scripts) — take a `practice_backup` or `mysqldump`. This is operational safety for content, separate from git.

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
| **Find a stopping point** / **good stopping point** / **let's wrap up** / **park it** | **Soft close** — stabilize work, push commits, verbal summary, Track A. **No record block.** See `SESSION-CLOSE-RECORD.md § Stopping point`. |
| **Closing** / **end session** / **record block** | **Hard close** — Track A + output `convmem record` block for Ryan to run. |

Avoid **"index what you wrote"** alone — models treat that as the markdown log, skip chat.

**Crush:** you are **Crush lane** even when running DeepSeek V4 weights. Say **Crush found it** — not "DeepSeek found it."

1. **Search first** — `convmem "topic"` / `ask` before re-deriving from scratch.
2. **`record`** — one closing **conclusion** only (not per-finding). Detail stays in chat ingest + indexed logs.


## Builder reference

Before convmem architecture edits, read the relevant digest in `docs/builder-reference/`.

- `ousterhout-builder-digest.md` for module boundaries and protocol surfaces
- `manning-builder-digest.md` for ranking, chunking, retrieval, and evaluation
- `zeller-builder-digest.md` for reproduction, triage, and verification
- `hard-parts-builder-digest.md` for trade-offs, data ownership, and split decisions

## Read-only guard

Do not run `convmem add`, bulk `convmem index` (no `--file`), or `convmem verify` without user direction.
Allowed: `convmem index --file <path> [--supersede]` for session tracking (Tier A).

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


Activates only on exact phrase `Mode: bounded autonomy`; never default.

Precedence (high→low): system/tool guards → lane must-nots + protocol → DB/secrets/external safety → exact brief authorizations → autonomy defaults. Lower cannot override higher.

Interrupt only for: security/privacy exposure; unauthorized external change; external cost/commitment; public API/schema change; out-of-lane action; ambiguous outcome. Else choose one path and continue.

Reuse existing DB-backup, lane, and record safeguards by reference.

External auth requires exact resource, operation, and final value (or named one-shot) in `Authorized external changes`; never infer from outcome.

Done: result, verification, largest material trade-off/risk, branch/push; Track A at handoff.


## Codex — no improvised logs

- Do **not** create new `logs/*.md`, audit files, or handoff markdown unless Ryan explicitly asked for a file.
- Preserve work: `convmem index --file` on **this session's** `~/.codex/sessions/**/rollout-*.jsonl` (full chat — not `history.jsonl` prompts-only).
- Handoff ≠ record — no `convmem record` unless Ryan says **record block** or **closing**.

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


Full cheat sheet: `docs/MODEL-WORKFLOW.md`

## Verify shipped work (Codex / DeepSeek)

Independent checklist: `docs/CODEX-DEEPSEEK-VERIFY.md` — pytest, smoke scripts, MCP spot-checks. Do not trust prior chat claims without running it.
