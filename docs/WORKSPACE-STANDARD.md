# Workspace standard

**Convention only** — not enforced by tooling. **Confirmed by Ryan, 2026-06-22.**

Signed by models: Codex, Kiro, Cursor.

Machine copy: [`~/Projects/WORKSPACE.md`](file:///home/lauer/Projects/WORKSPACE.md) (keep in sync with this file).

> One root per project, one brief per project, explicit live-state exclusions, tool state isolated; **convmem = cross-project coordination**.

## Active project roots

| Root | Role |
|------|------|
| `~/Projects/convmem` | Memory bus, watch/index tooling, inter-model docs |
| `~/Projects/wp-sec-agent` | Client security work (per-client state inside root) |
| `~/Projects/web-control` | Ops / site checklists |
| `~/Projects/ComfyUIimprov` | Experimental fork — **high churn; do not add to convmem watch** |

| Brief | Path |
|-------|------|
| Machine ops | `~/.local/share/convmem/brief.md` (`convmem brief`) |
| Cross-model | `~/Projects/convmem/docs/inter-model/` (newest first) |
| Per-project | `STATUS.md` or `AGENTS.md` at project root |

## Live paths — never watch-index

Manual `convmem index --file` only. Enforced in `watch.py` (`is_live_watch_db`) and/or `convmem exclude`:

- `~/.local/share/kiro-cli/data.sqlite3`
- `~/.config/cursor/chats/**/store.db`
- `~/.local/share/convmem/imports/webui.db`

## Tool state ≠ source

Not project source: `.crush/`, `.lighthouseci/`, `node_modules/`, ComfyUI caches, `~/.local/share/convmem/chroma/`.

## New project checklist

1. Create `~/Projects/<name>/`.
2. Add `STATUS.md` or `AGENTS.md` with watch exclusions for any live DBs.
3. Register live DBs in `watch.py` or `convmem exclude` **before** watch touches project paths.
4. Coordinate via convmem — don't copy state between trees.

**Rejected for now:** workspace index, per-project manifests, automated enforcer.

## Machine inventory (2026-06-22)

| Path | Class | Watch default |
|------|-------|---------------|
| `~/Projects/convmem` | Active project | Tool paths only (see config); not project source tree |
| `~/Projects/wp-sec-agent` | Active project | **Exclude** — `.crush/`, live client results |
| `~/Projects/web-control` | Active project | **Exclude** until explicit AGENTS.md + exclusions |
| `~/Projects/ComfyUIimprov` | Noisy sandbox | **Never watch** — 9G+ churn, caches, models |
| `~/Projects/.crush` | Tool state at workspace root | **Never watch** |
| `~/Projects/.lighthouseci` | Tool state at workspace root | **Never watch** |
| `~/Projects/*.tar.gz` | Archives | **Never watch** |

See also: `docs/inter-model/KIRO-CURSOR-BEST-PRACTICES-2026-06-22.md`, `docs/CHROMA-ACCESS-PATTERN.md`.
