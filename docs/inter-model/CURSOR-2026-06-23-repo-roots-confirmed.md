# Repo roots confirmed (Sonnet follow-up)

**Date:** 2026-06-23  
**From:** Cursor (Ryan requested)  
**Relates:** `SONNET-2026-06-23-brief-mcp-review.md` finding #2

## Standard roots (`brief.py`)

`GitClones`, `Projects`, `WordPress` under `~` — **confirmed complete for active work.**

## Git repos by root

### `~/GitClones/`

| Dir | Git | In `brief` rollup | Notes |
|-----|-----|-------------------|--------|
| willowyhollow-dev | yes | yes (53 units) | Primary WH dev |
| willowyhollow_mcp | yes | via `willowyhollow-mcp` cursor dir | underscore dir, hyphen cursor project |
| willowyhollow-sandbox | yes | no indexed sources yet | |
| pavlomassage-dev | yes | yes | |
| ComfyUI | yes | yes (55 units) | |
| cal.diy | yes | no | no Cursor project folder |
| paru | yes | no | AUR helper, not client work |
| gitignore | — | — | not checked |

### `~/Projects/`

| Dir | Git | In `brief` rollup | Notes |
|-----|-----|-------------------|--------|
| convmem | yes | yes (as `convem` slug — cursor typo path) | fix cursor project name optional |
| wp-sec-agent | yes | yes | |
| ComfyUIimprov | yes | no | no `home-lauer-Projects-ComfyUIimprov` cursor dir |
| ponytail | yes | no | no cursor project dir |
| web-control | **no** | no | not a git repo |
| ponytail / tarballs | — | — | ignore archives |

### `~/WordPress/`

| Dir | Role |
|-----|------|
| willowyhollow | local Podman site root |
| pavlomassage | local site |
| thaisolude | local site |
| htdocs | XAMPP legacy |

WordPress dirs are **runtime roots**, not primary git clones. Dev git truth stays in `GitClones/*-dev`.

## Repos outside three roots

Quick scan (`find ~/.git` depth 3): only tooling (`.config/crush`, `.continue`, `.nvm`, `aiderfoo`) — **no client git repos missed.**

## Verdict

**Sonnet follow-up closed:** all active client/dev repos Ryan uses are under the three named roots. Silent-drop risk is low.

**Gaps (not root bugs):**

- No Cursor project → no transcript indexing (`ponytail`, `ComfyUIimprov`, `cal.diy`)
- `brief(project=...)` empty until first indexed session or crush.db
- `Projects-convem` cursor slug typo maps `convmem` → slug `convem`

## Agent use

```text
brief(project="willowyhollow-dev")
brief(project="wp-sec-agent")
search_fast("willowyhollow-dev Aider git-health")
```

Durable leave-off: CLI `propose_decision` only (not MCP).
