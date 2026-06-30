# Recover convmem + MCP after data loss

Ryan backs up **`~/Projects/convmem`** (source, docs, examples). This guide assumes that
backup exists. It separates what the **hook hard-protects**, what is **easy to recreate
from the repo**, and what needs a **separate data backup**.

---

## Three tiers

| Tier | Location | If wiped | Agent hook |
|------|----------|----------|------------|
| **1 — Corpus** | `~/.local/share/convmem/` | Restore from your **data backup** or full reindex (slow) | **Blocks** shell delete/move/truncate |
| **2 — Runtime config** | `~/.config/convmem/` | Copy examples below; re-enter API key | **Blocks** shell delete/move/truncate |
| **3 — Wiring + source** | `~/Projects/convmem`, `~/.cursor/mcp.json`, `~/.kiro/settings/mcp.json`, `~/.kiro/settings/permissions.yaml`, `~/.config/crush/crush.json`, Continue YAML | Restore project backup or git; copy MCP/permissions examples | **Not blocked** — edits encouraged |

**Not in the Git repo:** Tier 1 (`chroma/`, `processed.json`, `knowledge_units.jsonl`,
`decisions-approved.jsonl`, etc.). Include `~/.local/share/convmem/` in backups if you want
fast recovery without reindexing.

---

## Fast path (project backup only)

Use when Tier 1 corpus still exists or you accept reindexing later.

```bash
# 1. Restore source tree (your normal backup restore)
cd ~/Projects
# … restore convmem directory …

# 2. Runtime config
mkdir -p ~/.config/convmem
cp ~/Projects/convmem/config.example.toml ~/.config/convmem/config.toml
cp ~/Projects/convmem/config/env.local.shell.example ~/.config/convmem/env.local
cp ~/Projects/convmem/config/env.systemd.example ~/.config/convmem/env.systemd
# Edit env.local + env.systemd: set DEEPSEEK_API_KEY

# 3. Shell alias
source ~/.config/convmem/env.local

# 4. Cursor MCP
cp ~/Projects/convmem/config/cursor-mcp.json.example ~/.cursor/mcp.json
# Edit API key in mcp.json or rely on env.local

# 5. Continue MCP
mkdir -p ~/.continue/mcpServers
cp ~/Projects/convmem/config/continue-mcp.json.example ~/.continue/mcpServers/convmem.json
# Add mcpServers block from config/continue-mcp-servers.yaml.example to ~/.continue/config.yaml
# Tier-A agent models: merge config/continue-models-tier-a.example.yaml under models:

# 6. Systemd (optional always-on)
cp ~/Projects/convmem/systemd/convmem-watch.service.example ~/.config/systemd/user/convmem-watch.service
cp ~/Projects/convmem/systemd/convmem-refine.service.example ~/.config/systemd/user/convmem-refine.service
systemctl --user daemon-reload
systemctl --user enable --now convmem-watch.service convmem-refine.service

# 7. Deploy agent protocol surfaces (Cursor .mdc, Codex AGENTS.md, Kiro steering + MCP + permissions.yaml, Crush)
bash ~/Projects/convmem/scripts/deploy-agent-protocol.sh
# Kiro: enable MCP in Settings after deploy (see script manual steps)

# 8. Verify
convmem stats
~/Projects/convmem/scripts/verify-continue.sh
# Restart Cursor / Continue / Kiro after MCP config changes
# After mcp_server.py updates: bash scripts/restart-convmem-mcp.sh (kills stale stdio subprocesses)
```

---

## Corpus lost (Tier 1)

If `~/.local/share/convmem/chroma/` is gone:

1. Complete **Fast path** above.
2. Restore `~/.local/share/convmem/` from a **data backup** if you have one, **or**
3. Rebuild corpus (hours, GPU/LLM cost):

```bash
mkdir -p ~/.local/share/convmem
convmem inventory          # refresh inventory.jsonl
convmem index              # full index from inventory
convmem refine --once      # optional cleanup pass
convmem stats
```

Approved decisions in `decisions-approved.jsonl` can be re-ingested with
`convmem add` if you still have that file from backup.

---

## What agents may change freely

- Any file under `~/Projects/convmem/` (code, tests, docs)
- `mcp_server.py`, `watch.py`, `brief.py`, etc.
- `~/.cursor/mcp.json`, `~/.kiro/settings/mcp.json`, and Continue `mcpServers` (MCP wiring)
- `~/.config/convmem/config.toml` (paths, models)

## What needs Ryan (hook blocks shell destruction)

- `rm` / `mv` / `truncate` on `~/.local/share/convmem/` or `~/.config/convmem/`
- Bulk wipe of Chroma or `processed.json` (use deliberate terminal, not agent)

---

## Related

- `config.example.toml` — index paths and models
- `scripts/verify-continue.sh` — CLI MCP smoke test
- `docs/MINIPC-DEPLOY.md` — systemd + env details
- `docs/inter-model/CONTINUE-VERIFY.md` — Continue UI checklist
