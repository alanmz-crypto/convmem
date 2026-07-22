# Inter-model communication

When you communicate something meant for **other models** (not Ryan), write a file here.

**Historical context (pre-2026-06-24 soak):** [`docs/archive/inter-model/2026-06-22/`](../archive/inter-model/2026-06-22/) — date-bucketed archive; not scanned by brief staleness.

## Closed debate folder

- [debate-2026-07-15-who-fixes-retrieval/](debate-2026-07-15-who-fixes-retrieval/) — **CLOSED** (2026-07-22). Rounds 1–4 shipped; board closed into P1.3. Keep as reference (not an active contribution board).

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

## Done-writing ping

When you finish a note for other models, end it with a direct handoff:

- name the next model or models that should read it
- name the one file they should open first
- say whether they need to reply, assess, or implement

If the handoff changes shared course, also update `docs/inter-model/LATEST.md` so the next session has a single pointer.

## Anti-sprawl

Keep this inbox small and active. Treat planning notes as temporary unless they remain the current decision record.

- **One active inbox rule:** archive or merge planning output once the decision lands.
- **No orphan plans:** every plan or red-flag note should state `Status:`, `Owner:`, and `Sunset:` in its header.
- **Decision-first execution:** freeze the one open choice before bulk moves or folder changes.
- **Record block required:** major cleanup decisions and session closes should end with a `convmem record` block.
- **Archive before taxonomize:** move history out first; do not add new folder hierarchy just because the tree feels messy.
- **No duplicate canonical pointers:** keep one protocol pointer and one synthesis pointer, with names that make the difference obvious.
- **Review stale residue routinely:** use `convmem brief --stdout-only` and `convmem unresolved` to check for drift.

Do not add a separate governance doc for this. Do not create new taxonomy as a cleanup reflex.

## Reading order for any new session

1. `~/.local/share/convmem/brief.md` (auto-generated ops truth)
2. **`docs/inter-model/LATEST.md`** (single pointer — 3 bullets, updated each session)
3. `docs/STATUS.md` (pointer — where to read)
4. **Newest files in `docs/inter-model/`** (sort by mtime — read all unread since your last message)
5. `docs/AGENT-ROLES.md` (static routing)
6. `docs/archive/handoffs/` only for historical context

**Codex — cross-model history policy (2026-06-15):** `CURSOR-2026-06-15-cross-model-history-for-codex.md`

**Current direction:** [`config/agent-protocol.md`](../config/agent-protocol.md) — `brief` → `search_fast` / `ask`; session close via `convmem record` + `convmem record --approve-last` (see [`SESSION-CLOSE-RECORD.md`](SESSION-CLOSE-RECORD.md)). Legacy CLI name: `propose_decision`.

## Cursor implementer rule

On every Ryan trigger for convmem/wp-sec-agent: `ls -lt docs/inter-model/` first, read anything newer than your last `CURSOR-*` file, then act.

## Deprecation

Long-form handoffs in `docs/HANDOFF-*.md` are being superseded by:

- `brief.md` for live state
- `docs/inter-model/` for cross-model messages
- Future: `STATUS.md`, `ARCHITECTURE.md`, `DECISIONS.md`

Do not create new `HANDOFF-*.md` files unless archiving a milestone.
