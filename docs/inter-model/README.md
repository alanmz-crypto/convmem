# Inter-model communication

When you communicate something meant for **other models** (not Ryan), write a file here.

## Convention

- **Path:** `docs/inter-model/<MODEL>-<YYYY-MM-DD>-<topic>.md`
- **Examples:**
  - `CURSOR-2026-06-22-brief-build.md`
  - `KIRO-2026-06-22-brief-review.md`
  - `CHATGPT-2026-06-22-orchestration.md`
  - `SONNET-2026-06-22-crush-mcp-live.md`

## Each file should include

1. **To:** which models should read it
2. **From:** your role name
3. **Date / trigger:** what prompted this message
4. **Facts** — verified state only
5. **Asks** — specific requests to named models
6. **Do not** duplicate `brief.md` — point to `~/.local/share/convmem/brief.md` for live ops state

## Reading order for any new session

1. `~/.local/share/convmem/brief.md` (auto-generated ops truth)
2. `docs/STATUS.md` (pointer — where to read)
3. **Newest files in `docs/inter-model/`** (sort by mtime — read all unread since your last message)
4. `docs/AGENT-ROLES.md` (static routing)
5. `docs/archive/handoffs/` only for historical context

## Cursor implementer rule

On every Ryan trigger for convmem/wp-sec-agent: `ls -lt docs/inter-model/` first, read anything newer than your last `CURSOR-*` file, then act.

## Deprecation

Long-form handoffs in `docs/HANDOFF-*.md` are being superseded by:

- `brief.md` for live state
- `docs/inter-model/` for cross-model messages
- Future: `STATUS.md`, `ARCHITECTURE.md`, `DECISIONS.md`

Do not create new `HANDOFF-*.md` files unless archiving a milestone.
