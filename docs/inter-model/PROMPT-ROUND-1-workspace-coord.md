# Workspace coordination — Round 1 (STATUS WRITE)

Paste this whole prompt into **each** Cursor/Codex workspace working on
Shadow Ledger / research-pack / related 2026-07-24 work.

## Goal

Figure out where every open workspace is, what it uniquely owns, and whether
we should **keep one**, **archive the others**, or **keep two with hard
role locks**. No implementation. No commits. No PR edits unless this prompt
says so.

## Shared board (single write target)

```text
/tmp/convmem-coord-2026-07-24-workspaces/BOARD.md
```

All participants append to **that file only**. Do not put Round 1 status into
git branches, `LATEST.md`, or PR #115.

If `BOARD.md` is missing, create it by copying the template at the bottom of
this prompt (or create an empty board with the same headings).

## Hard rules

1. Run `convmem doctor` first if this is a project session start; then continue.
2. **Do not** switch the shared `~/Projects/convmem` branch under another agent.
3. **Do not** edit PR #115 / Architecture branch unless you are the workspace
   that already owns that tip and Round 1 proves you own it.
4. **Do not** stage/commit `docs/audit-ledger-first/` or change runtime code.
5. Append **only your** Round 1 section. Never rewrite another workspace’s
   Round 1 block.
6. If your shell `cwd` drifted into another worktree, `cd` back to your
   declared root before filing. State both declared root and actual `pwd`.
7. Stop after Round 1. Do **not** start Round 2 until Ryan pastes the Round 2
   prompt (after all Round 1 filings exist).

## Round 1 — what to do

1. Identify yourself (lane + chat/session id if any).
2. Inspect: `pwd`, `git branch --show-current`, `git rev-parse --short HEAD`,
   `git status --porcelain`, `git worktree list` (filter to convmem paths).
3. Check whether these exist / match:
   - Draft PR #115 (`gh pr view 115`)
   - `/tmp/convmem-shadow-ledger-phase0-architecture`
   - Untracked `docs/audit-ledger-first/` in `~/Projects/convmem`
   - `docs/inter-model/CURSOR-2026-07-24-shadow-ledger-phase0-chatgpt-handoff.md`
4. Append one Round 1 section to `BOARD.md` using the template below.
5. Reply to Ryan with: your workspace slug, one-line role, and
   “Round 1 filed — waiting for siblings + Round 2 prompt.”

## Round 1 section template (append under `## Round 1 — Status filings`)

```markdown
### WS-<slug> — <one-line role>

| Field | Value |
|---|---|
| Filed at (local) | <ISO or wall clock> |
| Lane / actor | Cursor / Codex / other |
| Chat or session id | <uuid or rollout id, or unknown> |
| Declared workspace root | <absolute path Cursor/Codex opened> |
| Shell pwd when filing | <absolute path> |
| Git branch | <branch or detached> |
| HEAD | <short sha> |
| Dirty summary | clean / list key dirty paths |
| Unique local-only artifacts | <paths not on GitHub, or none> |
| Work completed here | <bullets> |
| Currently waiting on | <Ryan HITL / other WS / nothing> |
| Must not touch from here | <paths/PRs/branches> |
| Preliminary keep/archive vote | KEEP as primary / KEEP as archive-read / ARCHIVE candidate |
| Risk if archived now | <what would be lost> |
| Notes | <toe-stepping / cwd drift / ambiguity> |

**TL;DR:** <one sentence>
```

## Known candidates (do not invent ownership — verify)

These are the likely participants; use them only if they match your root:

| Candidate | Typical root | Likely role |
|---|---|---|
| Main Cursor checkout | `/home/lauer/Projects/convmem` | Research-pack branch + untracked audit/handoff leftovers |
| Codex Architecture worktree | `/tmp/convmem-shadow-ledger-phase0-architecture` | Draft PR #115 tip `c9a5c70` |
| Earlier Cursor chat on same root | same as main checkout, different transcript | Audit → ChatGPT handoff authoring |

If you are a fourth workspace, still file Round 1 with a new slug.

## Done condition for Round 1

Your section appears in `BOARD.md`, you did not edit others’ sections, and
you stopped.
