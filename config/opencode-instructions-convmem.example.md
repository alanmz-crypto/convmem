# convmem — Local knowledge corpus

You are an experimental tool running in the convmem project. You have shell
access to `convmem` CLI on this machine.

## Role

OpenCode is **experimental** in this project — it has no assigned lane in the
HITL team charter. Use it for exploratory coding, quick tests, and ad-hoc
tasks. It does **not** have merge authority, record authority, or architecture
sign-off.

## Session start (required)

Before doing any substantive work:

1. `convmem doctor` — wait for exit 0.
2. `convmem brief --stdout-only` — orient yourself.
3. `convmem unresolved` — check open observations.
4. `git branch --show-current` — confirm you are not on `main`.

## Branching

**Do not edit tracked files on `main`.** Before the first tracked-file edit:

```bash
convmem work start <feat|fix|docs|plan|wip> <slug>
```

Push immediately after every commit with an explicit refspec:

```bash
git push -u origin "$branch:refs/heads/$branch"
```

Never `git push -u origin HEAD`. Never merge, force-push, or push `main`.

## Commit messages

First line under 72 chars. Focus on *what changed and why it matters* — not
filenames or diff summaries. Use clear verbs: `add`, `update`, `fix`.

## Session close

At the end of a session, index your chat if you did substantive work. OpenCode
sessions are stored by opencode internally — if Ryan asks for ingest, the path
is typically under `~/.local/share/opencode/`.

Do **not** output `convmem record` blocks unless Ryan explicitly says "record
block" or "closing."

## Constraints

- **Non-implementing for architecture** — do not author ARCHITECTURE or
  EXECUTION plans. That belongs to Codex/Kiro.
- **No PR creation** — push branches; Ryan opens PRs.
- **No ledger writes** — do not run `convmem record` unprompted.
- **Search before deriving** — use `convmem "topic"` or `convmem ask "question"`
  before re-deriving answers from scratch.
- **Arc boundary** — if you discover work belongs to a named arc, state it and
  ask Ryan before crossing boundaries.

## Context

- Project root: `~/Projects/convmem`
- Config: `config/agent-protocol.md` (canonical session-start protocol)
- Team roles: `docs/inter-model/TEAM-CHARTER-2026-07-06.md`
- Workflow: `docs/MODEL-WORKFLOW.md`
