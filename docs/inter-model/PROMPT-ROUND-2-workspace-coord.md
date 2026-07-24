# Workspace coordination — Round 2 (REVIEW + CONSOLIDATE)

Paste this only **after all Round 1 sections** are present in:

```text
/tmp/convmem-coord-2026-07-24-workspaces/BOARD.md
```

## Goal

Read every Round 1 filing. Recommend whether to consolidate to **one** live
workspace and archive the others. Do not implement Architecture, Execution,
or hooks.

## Hard rules

1. Read the full `BOARD.md` first.
2. Append **only your** Round 2 review section. Do not edit Round 1 blocks
   or other Round 2 blocks.
3. No commits, no branch switches on shared checkouts, no PR #115 edits,
   no audit-doc commits.
4. If Round 1 is incomplete (missing a known participant), say so and stop
   with `BLOCKED — missing Round 1 from <slug>` instead of guessing.

## Round 2 — what to do

1. Summarize what each workspace uniquely owns (one line each).
2. Detect conflicts: same dirty paths claimed by two workspaces, cwd drift
   into another worktree, duplicate “primary” claims.
3. Cast a consolidation vote using the options below.
4. List exact archive actions (commands/paths) **for Ryan**, not executed.
5. List what must move/copy before any archive (local-only artifacts).
6. Append your Round 2 section; reply to Ryan with your vote + one risk.

## Vote options (pick exactly one)

| Vote | Meaning |
|---|---|
| `ONE_PRIMARY` | Keep one live workspace; archive the rest after salvage |
| `TWO_LOCKED` | Keep exactly two with hard role locks (name them) |
| `HOLD` | Do not archive yet; missing info or active writer risk |
| `ALL_ARCHIVE_EXCEPT_GITHUB` | No local workspace needed; GitHub PR/docs are enough for now |

## Round 2 section template (append under `## Round 2 — Reviews`)

```markdown
### Review by WS-<slug>

**Read:** <list WS slugs you saw in Round 1>

| Other WS | Unique value | Conflict with me? | Archive? |
|---|---|---|---|
| WS-... | ... | yes/no — why | yes/no/after-salvage |

**Consolidation vote:** <ONE_PRIMARY|TWO_LOCKED|HOLD|ALL_ARCHIVE_EXCEPT_GITHUB>

**If ONE_PRIMARY / TWO_LOCKED — survivors:**
- Primary: <slug + root + role>
- Secondary (only if TWO_LOCKED): <slug + role lock>

**Salvage before archive (if any):**
- <path> → <destination or “commit on dedicated branch after Ryan auth”>

**Proposed archive actions (Ryan runs):**
- <e.g. close chat X; leave worktree; `git worktree remove …` only if clean>

**Largest disagreement with another Round 1 vote:**
- <none or specific>

**TL;DR:** <one sentence vote + why>
```

## After all Round 2 reviews

Ryan (human) chooses. Agents do **not** delete worktrees or close chats
unless Ryan explicitly authorizes the archive step in a later prompt.
