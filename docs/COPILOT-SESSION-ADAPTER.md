# GitHub Copilot CLI session transcripts (jsonl_copilot_session)

GitHub Copilot CLI stores **full agent chat transcripts** at:

```
~/.copilot/
  session-state/
    <uuid>/
      events.jsonl      ← indexed
      workspace.yaml    ← metadata (title, cwd)
      session.db        ← live SQLite — do not watch
  session-store.db      ← global index DB — do not watch
  mcp-config.json       ← MCP servers (see config/copilot-mcp-config.json.example)
  agents/               ← user-level custom agents (protocol deploy target)
```

Index **`events.jsonl` only**. Tool/system noise is skipped; user + assistant text is kept.

## Config

Add to `~/.config/convmem/config.toml` (see [config.example.toml](../config.example.toml)):

```toml
"~/.copilot/session-state",
```

Prefer `session-state` over `~/.copilot` so watch does not churn on logs, locks, or `session-store.db`.

## MCP

Copilot CLI loads `~/.copilot/mcp-config.json`. Example:

```bash
# Prefer the deploy script (merges without wiping other servers):
bash scripts/deploy-agent-protocol.sh

# Or one-shot:
copilot mcp add convmem --env CONVMEM_MCP_PROFILE=shell -- \
  /home/lauer/miniforge3/envs/convmem/bin/python \
  /home/lauer/Projects/convmem/mcp_server.py
```

Template: [config/copilot-mcp-config.json.example](../config/copilot-mcp-config.json.example)

Do **not** put `DEEPSEEK_API_KEY` in `mcp-config.json` — `mcp_server.py` loads it
from `~/.config/convmem/env.local` (or `env.systemd`) when missing from the process env.

## Protocol

**Always-on (required):** `~/.copilot/copilot-instructions.md` — loaded by plain
`copilot` (same role as Codex `~/.codex/AGENTS.md`). Deployed from
`config/copilot-instructions-convmem.example.md` via `deploy-agent-protocol.sh`.

Repo `AGENTS.md` in convmem is a **pointer only** (no Tier A body). Without the
always-on file, Copilot skips `doctor`/`brief`/`unresolved` and starts with
`ls`/`git`/`README` — that was the soak failure mode.

**Optional agent:** `~/.copilot/agents/convmem.md` via `copilot --agent convmem`
(not required once always-on instructions are deployed).

```bash
bash scripts/deploy-agent-protocol.sh
test -f ~/.copilot/copilot-instructions.md && rg -n 'convmem doctor' ~/.copilot/copilot-instructions.md
```

## Track A (handoff)

```bash
convmem index --file ~/.copilot/session-state/<uuid>/events.jsonl
# or:
bash ~/Projects/convmem/scripts/convmem-index-prod.sh \
  ~/.copilot/session-state/<uuid>/events.jsonl --force
```

Newest session:

```bash
ls -t ~/.copilot/session-state/*/events.jsonl | head -1
```

## Backfill (Ryan — count before bulk)

```bash
find ~/.copilot/session-state -name events.jsonl | wc -l
```

After approving the count:

```bash
find ~/.copilot/session-state -name events.jsonl \
  -exec convmem index --file {} \;
```

## Verify

```bash
convmem search "What's the current state of this repo"
```

A hit with `source_path` under `~/.copilot/session-state/` confirms the pipeline.

## Detection

`adapters/detect.py` matches:

```python
path.name == "events.jsonl"
and path is under ~/.copilot/session-state/<uuid>/
```

Tool metadata tag: `copilot`.
